"""
Smart Motion Detector v2 - Main Entry Point
"""
import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.models import Camera, CameraStatus
from app.db.session import get_session, session_scope, get_migration_status
from app.version import __version__
from app.workers.detector_mp import get_mp_detector_worker
from app.workers.detector import get_detector_worker
from app.dependencies import (
    settings_service,
    camera_crud_service,
    detector_worker,
    websocket_manager,
    telegram_service,
    go2rtc_service,
    mqtt_service,
    metrics_service,
    continuous_recorder,
    retention_worker,
    live_stream_semaphore,
)
from app.utils.stream_helpers import get_recording_rtsp_url
from app.routers import cameras, events, live, settings as settings_router, system, websocket_router


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _resolve_log_level(raw: str) -> int:
    value = (raw or "").strip().lower()
    if not value:
        return logging.INFO
    if value == "trace":
        return logging.DEBUG
    if value == "notice":
        return logging.INFO
    if value == "fatal":
        return logging.CRITICAL
    return getattr(logging, value.upper(), logging.INFO)


def _resolve_access_log_enabled(raw: str) -> bool:
    return (raw or "").strip().lower() in {"trace", "debug"}


def _resolve_uvicorn_log_level(raw: str) -> str:
    value = (raw or "").strip().lower()
    if value in {"trace", "debug", "info", "warning", "error", "critical"}:
        return value
    if value == "fatal":
        return "critical"
    if value == "notice":
        return "info"
    return "info"


log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "app.log"
_IS_TEST = "pytest" in sys.modules
_handlers = [logging.StreamHandler()]
if not _IS_TEST:
    _handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
logging.basicConfig(
    level=_resolve_log_level(os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=_handlers,
)
logger = logging.getLogger(__name__)

for _noisy in ("httpcore", "httpx", "openai", "telegram", "hpack"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

APP_START_TS = time.time()


def _load_cors_origins() -> List[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


def _debug_headers_enabled() -> bool:
    return os.getenv("DEBUG_HEADERS", "").strip().lower() in {"1", "true", "yes", "on"}


async def _wait_for_startup_readiness(timeout_seconds: float = 15.0) -> None:
    """Wait until critical startup dependencies are reachable."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        db_ok = False
        go2rtc_ok = False
        mqtt_ready = False
        try:
            with session_scope() as db:
                db.query(Camera).count()
                db_ok = True
        except Exception:
            db_ok = False

        try:
            go2rtc_ok = bool(go2rtc_service and go2rtc_service.ensure_enabled())
        except Exception:
            go2rtc_ok = False

        try:
            mqtt_cfg = settings_service.load_config().mqtt
            mqtt_ready = (not mqtt_cfg.enabled) or bool(mqtt_service.client) or bool(mqtt_service.connected)
        except Exception:
            mqtt_ready = True

        if db_ok and go2rtc_ok and mqtt_ready:
            logger.info("Startup readiness checks passed")
            return
        await asyncio.sleep(0.5)
    logger.warning("Startup readiness timeout reached; continuing with best effort")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan for startup/shutdown tasks."""
    logger.info("Starting Smart Motion Detector v2")

    retention_worker.start()
    logger.info("Retention worker started")

    await _wait_for_startup_readiness()

    try:
        with session_scope() as db:
            cameras = camera_crud_service.get_cameras(db)
            go2rtc_service.sync_all_cameras(cameras)
            logger.info("Cameras synced to go2rtc")
    except Exception as e:
        logger.error(f"Failed to sync cameras to go2rtc: {e}")

    try:
        config = settings_service.load_config()
        if hasattr(config, "performance") and config.performance.enable_metrics:
            metrics_service.start_server(config.performance.metrics_port)
            logger.info(f"Metrics server started on port {config.performance.metrics_port}")

        worker_mode = getattr(getattr(config, "performance", None), "worker_mode", "threading") or "threading"
        global detector_worker
        if worker_mode == "multiprocessing":
            detector_worker = get_mp_detector_worker()
            logger.info("Using multiprocessing detector worker (experimental)")
        else:
            detector_worker = get_detector_worker()
            logger.info("Using threading detector worker")
    except Exception as e:
        logger.warning(f"Failed to load config / start metrics: {e}")
        detector_worker = get_detector_worker()
        logger.info("Using threading detector worker (fallback)")

    detector_worker.start()
    logger.info("Detector worker started")

    continuous_recorder.start()
    try:
        with session_scope() as db:
            cameras = camera_crud_service.get_cameras(db)
            started = 0
            for camera in cameras:
                if camera.enabled:
                    rtsp_url = get_recording_rtsp_url(camera)
                    if rtsp_url:
                        if continuous_recorder.start_recording(camera.id, rtsp_url):
                            started += 1
            logger.info(f"Started continuous recording for {started} cameras")
    except Exception as e:
        logger.error(f"Failed to start continuous recording: {e}")

    mqtt_service.start()
    logger.info("MQTT service started")

    logger.info("Services initialized, application ready")
    try:
        yield
    finally:
        logger.info("Shutting down Smart Motion Detector v2")
        mqtt_service.stop()
        logger.info("MQTT service stopped")
        detector_worker.stop()
        logger.info("Detector worker stopped")
        continuous_recorder.stop()
        logger.info("Continuous recording stopped")
        retention_worker.stop()
        logger.info("Retention worker stopped")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Smart Motion Detector API",
    version=__version__,
    description="Person detection with thermal/color camera support",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_load_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cameras.router)
app.include_router(events.router)
app.include_router(live.router)
app.include_router(settings_router.router)
app.include_router(system.router)
app.include_router(websocket_router.router)


# ---------------------------------------------------------------------------
# Root / health endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "Smart Motion Detector v2", "status": "ok"}


@app.get("/ready")
async def ready():
    return {"ready": True, "status": "ok"}


if _debug_headers_enabled():
    @app.get("/api/debug/headers")
    async def debug_headers(request: Request):
        return {
            "all_headers": dict(request.headers),
            "x_ingress_path": request.headers.get("X-Ingress-Path", "NOT_FOUND"),
            "x_ingress_path_lower": request.headers.get("x-ingress-path", "NOT_FOUND"),
        }


@app.get("/api/health")
async def health():
    from app.routers.system import get_worker_info
    uptime_s = max(0, int(time.time() - APP_START_TS))
    try:
        with session_scope() as db:
            online = db.query(Camera).filter(Camera.status == CameraStatus.CONNECTED).count()
            retrying = db.query(Camera).filter(Camera.status == CameraStatus.RETRYING).count()
            down = db.query(Camera).filter(Camera.status == CameraStatus.DOWN).count()
    except Exception:
        online = retrying = down = 0

    try:
        config = settings_service.load_config()
        has_key = bool(config.ai.api_key) and config.ai.api_key != "***REDACTED***"
        ai_enabled = bool(config.ai.enabled and has_key)
        ai_reason = "" if ai_enabled else ("no_api_key" if config.ai.enabled else "not_configured")
    except Exception:
        ai_enabled = False
        ai_reason = "not_configured"

    pipeline_status = "ok" if detector_worker.running else "down"
    telegram_status = "ok" if telegram_service.is_enabled() else "disabled"
    try:
        mqtt_cfg = settings_service.load_config().mqtt
        mqtt_status = "ok" if mqtt_service.connected else ("disabled" if not mqtt_cfg.enabled else "disconnected")
    except Exception:
        mqtt_status = "unknown"

    migrations = get_migration_status()
    migrations_ok = all(item.get("ok", False) for item in migrations.values()) if migrations else True

    return {
        "status": "ok" if pipeline_status == "ok" and migrations_ok else "degraded",
        "version": __version__,
        "uptime_s": uptime_s,
        "ai": {"enabled": ai_enabled, "reason": ai_reason},
        "cameras": {"online": online, "retrying": retrying, "down": down},
        "components": {"pipeline": pipeline_status, "telegram": telegram_status, "mqtt": mqtt_status},
        "migrations": migrations,
        "worker": get_worker_info(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=_resolve_uvicorn_log_level(os.getenv("LOG_LEVEL", "info")),
        access_log=_resolve_access_log_enabled(os.getenv("LOG_LEVEL", "info")),
    )
