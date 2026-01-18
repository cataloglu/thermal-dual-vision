"""Health, readiness, and minimal UI server."""

from __future__ import annotations

import base64
import os
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Protocol

import cv2
from aiohttp import web

from src.camera_store import CameraStore
from src.config import Config
from src.config_store import ConfigStore, merge_config, redacted_effective_config
from src.events import EventType, new_event
from src.logger import get_log_tail, get_logger
from src.mqtt_client import MQTTClient
from src.telegram_bot import TELEGRAM_AVAILABLE, TelegramBot

logger = get_logger("health")
UI_PATH = Path(__file__).with_name("web_ui.html")


@dataclass
class ComponentStatus:
    """Component status details."""

    status: str
    detail: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"status": self.status}
        if self.detail:
            payload["detail"] = self.detail
        return payload


@dataclass
class PipelineStatus:
    """Pipeline runtime status."""

    status: str
    detail: Optional[str]
    updated_at: float

    def as_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"status": self.status, "updated_at": self.updated_at}
        if self.detail:
            payload["detail"] = self.detail
        return payload


class EventStore:
    """In-memory ring buffer of recent events."""

    def __init__(self, max_events: int = 50) -> None:
        self._events: Deque[Dict[str, Any]] = deque(maxlen=max_events)

    def add_event(
        self,
        event_type: EventType,
        source: str,
        payload: Optional[Dict[str, Any]] = None,
        camera_id: Optional[str] = None,
    ) -> None:
        event = new_event(
            event_type=event_type,
            source=source,
            camera_id=camera_id,
            payload=payload,
        )
        self._events.appendleft(event.as_dict())

    def snapshot(self) -> List[Dict[str, Any]]:
        return list(self._events)


class PipelineStatusTracker:
    """Track pipeline status for UI and health reporting."""

    def __init__(self, event_store: Optional[EventStore] = None) -> None:
        self._event_store = event_store
        self._status = PipelineStatus(status="idle", detail="Not started", updated_at=time.time())

    def set_status(self, status: str, detail: Optional[str] = None) -> None:
        if status == self._status.status and detail == self._status.detail:
            return
        self._status = PipelineStatus(status=status, detail=detail, updated_at=time.time())
        if self._event_store:
            self._event_store.add_event(
                event_type=EventType.HEALTH,
                source="pipeline",
                payload={"status": status, "detail": detail},
            )

    def as_dict(self) -> Dict[str, Any]:
        return self._status.as_dict()


class PipelineController(Protocol):
    """Protocol for controlling pipeline lifecycle."""

    def start(self) -> bool:
        ...

    def stop(self) -> bool:
        ...

    def restart(self) -> None:
        ...


class CameraStatusChecker:
    """Probe camera availability with a short-lived capture."""

    def __init__(self, config: Config, cache_seconds: float = 2.0) -> None:
        self.config = config
        self.cache_seconds = cache_seconds
        self._last_check = 0.0
        self._last_status = ComponentStatus(status="unknown", detail="Not checked")

    def check(self) -> ComponentStatus:
        if not self.config.camera.url and not self.config.camera.color_url and not self.config.camera.thermal_url:
            return ComponentStatus(status="missing", detail="Camera URL not set")

        now = time.time()
        if now - self._last_check < self.cache_seconds:
            return self._last_status

        self._last_check = now
        camera_url = self.config.camera.url or self.config.camera.color_url or self.config.camera.thermal_url
        if camera_url.startswith("dummy://"):
            self._last_status = ComponentStatus(status="ok", detail="Dummy camera")
            return self._last_status

        capture = cv2.VideoCapture(camera_url)
        try:
            if capture.isOpened():
                self._last_status = ComponentStatus(status="ok")
            else:
                self._last_status = ComponentStatus(
                    status="down", detail="Unable to open camera stream"
                )
        finally:
            capture.release()

        return self._last_status


class HealthReporter:
    """Build health and readiness payloads."""

    def __init__(
        self,
        config: Config,
        mqtt_client: Optional[MQTTClient] = None,
        telegram_bot: Optional[TelegramBot] = None,
        camera_checker: Optional[CameraStatusChecker] = None,
        event_store: Optional[EventStore] = None,
        pipeline_status: Optional[PipelineStatusTracker] = None,
    ) -> None:
        self.config = config
        self.mqtt_client = mqtt_client
        self.telegram_bot = telegram_bot
        self.camera_checker = camera_checker or CameraStatusChecker(config)
        self.event_store = event_store
        self.pipeline_status = pipeline_status
        self._last_health_status: Optional[str] = None
        self._last_ready_status: Optional[bool] = None

    def _mqtt_status(self) -> ComponentStatus:
        if self.mqtt_client is None:
            if not self.config.mqtt.discovery:
                return ComponentStatus(status="disabled", detail="MQTT discovery disabled")
            return ComponentStatus(status="unknown", detail="MQTT client not wired")
        return ComponentStatus(status="ok" if self.mqtt_client.is_connected else "down")

    def _telegram_status(self) -> ComponentStatus:
        if not self.config.telegram.enabled:
            return ComponentStatus(status="disabled")
        if not TELEGRAM_AVAILABLE:
            return ComponentStatus(status="missing", detail="python-telegram-bot not installed")
        if self.telegram_bot is None:
            return ComponentStatus(status="unknown", detail="Telegram bot not wired")
        return ComponentStatus(status="ok" if self.telegram_bot.is_running else "down")

    def _camera_status(self) -> ComponentStatus:
        return self.camera_checker.check()

    def _record_health_event(self, status: str) -> None:
        if not self.event_store or status == self._last_health_status:
            return
        self._last_health_status = status
        self.event_store.add_event(event_type=EventType.HEALTH, source="health")

    def _record_ready_event(self, ready: bool) -> None:
        if not self.event_store or ready == self._last_ready_status:
            return
        self._last_ready_status = ready
        self.event_store.add_event(event_type=EventType.READY, source="health", payload={"ready": ready})

    def build_report(self) -> Dict[str, Any]:
        ai_enabled = bool(self.config.llm.api_key)
        components = {
            "camera": self._camera_status(),
            "mqtt": self._mqtt_status(),
            "telegram": self._telegram_status(),
        }

        overall = "ok"
        for status in components.values():
            if status.status in {"down", "missing"}:
                overall = "down"
                break
            if status.status == "unknown" and overall != "down":
                overall = "degraded"

        self._record_health_event(overall)

        return {
            "status": overall,
            "timestamp": time.time(),
            "ai_enabled": ai_enabled,
            "components": {key: value.as_dict() for key, value in components.items()},
            "pipeline": self.pipeline_status.as_dict() if self.pipeline_status else {"status": "unknown"},
            "events": self.event_store.snapshot() if self.event_store else [],
        }

    def is_ready(self, report: Optional[Dict[str, Any]] = None) -> bool:
        payload = report or self.build_report()
        components = payload["components"]

        camera_ok = components["camera"]["status"] == "ok"
        telegram_ok = components["telegram"]["status"] in {"ok", "disabled"}
        mqtt_ok = components["mqtt"]["status"] in {"ok", "disabled"}

        return camera_ok and telegram_ok and mqtt_ok


def create_app(
    config: Config,
    mqtt_client: Optional[MQTTClient] = None,
    telegram_bot: Optional[TelegramBot] = None,
    event_store: Optional[EventStore] = None,
    pipeline_status: Optional[PipelineStatusTracker] = None,
    pipeline_controller: Optional[PipelineController] = None,
) -> web.Application:
    """Create aiohttp app with health endpoints and UI."""
    reporter = HealthReporter(
        config,
        mqtt_client=mqtt_client,
        telegram_bot=telegram_bot,
        event_store=event_store,
        pipeline_status=pipeline_status,
    )

    camera_store = CameraStore()
    start_time = time.time()

    async def health_handler(_: web.Request) -> web.Response:
        return web.json_response(reporter.build_report())

    async def config_get_handler(_: web.Request) -> web.Response:
        store = ConfigStore()
        payload = redacted_effective_config(os.environ, store=store)
        return web.json_response(payload)

    async def config_post_handler(request: web.Request) -> web.Response:
        store = ConfigStore()
        try:
            updates = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        if not isinstance(updates, dict):
            return web.json_response({"error": "Invalid config payload"}, status=400)

        saved = store.load()
        merged = merge_config(saved, updates)
        config_candidate = Config.from_sources(os.environ, saved=merged)
        errors = config_candidate.validate(allow_incomplete=True)
        if errors:
            return web.json_response({"errors": errors}, status=400)

        store.save(merged)
        return web.json_response(config_candidate.to_dict(redact=True))

    async def ready_handler(_: web.Request) -> web.Response:
        payload = reporter.build_report()
        payload["ready"] = reporter.is_ready(payload)
        reporter._record_ready_event(payload["ready"])
        return web.json_response(payload, status=200)

    async def events_handler(request: web.Request) -> web.Response:
        events = event_store.snapshot() if event_store else []
        event_type = request.query.get("type")
        if event_type:
            events = [event for event in events if event.get("event_type") == event_type]
        limit = request.query.get("limit")
        if limit:
            try:
                count = int(limit)
                events = events[:count]
            except ValueError:
                return web.json_response({"error": "Invalid limit"}, status=400)
        return web.json_response({"events": events})

    async def logs_tail_handler(request: web.Request) -> web.Response:
        lines_param = request.query.get("lines", "200")
        try:
            lines = int(lines_param)
        except ValueError:
            return web.json_response({"error": "Invalid lines"}, status=400)
        return web.json_response({"lines": get_log_tail(lines)})

    async def metrics_handler(_: web.Request) -> web.Response:
        uptime = time.time() - start_time
        pipeline_payload = pipeline_status.as_dict() if pipeline_status else {"status": "unknown"}
        return web.json_response(
            {
                "uptime_seconds": uptime,
                "pipeline": pipeline_payload,
                "events_count": len(event_store.snapshot()) if event_store else 0,
            }
        )

    async def status_handler(_: web.Request) -> web.Response:
        report = reporter.build_report()
        uptime = time.time() - start_time
        return web.json_response(
            {
                "status": report["status"],
                "uptime_seconds": uptime,
                "components": {
                    "camera": report["components"]["camera"]["status"],
                    "detector": report["pipeline"]["status"],
                    "mqtt": report["components"]["mqtt"]["status"],
                },
            }
        )

    async def stats_handler(_: web.Request) -> web.Response:
        return web.json_response(
            {
                "total_detections": 0,
                "real_detections": 0,
                "false_positives": 0,
            }
        )

    async def cameras_list_handler(_: web.Request) -> web.Response:
        return web.json_response({"cameras": camera_store.list_cameras()})

    async def cameras_create_handler(request: web.Request) -> web.Response:
        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)
        if not isinstance(payload, dict):
            return web.json_response({"error": "Invalid camera payload"}, status=400)
        try:
            camera = camera_store.create_camera(payload)
        except ValueError as exc:
            return web.json_response({"error": str(exc)}, status=400)
        return web.json_response(camera, status=201)

    async def camera_detail_handler(request: web.Request) -> web.Response:
        camera_id = request.match_info.get("camera_id", "")
        camera = camera_store.get_camera(camera_id)
        if not camera:
            return web.json_response({"error": "Camera not found"}, status=404)
        return web.json_response(camera)

    async def camera_update_handler(request: web.Request) -> web.Response:
        camera_id = request.match_info.get("camera_id", "")
        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)
        if not isinstance(payload, dict):
            return web.json_response({"error": "Invalid camera payload"}, status=400)
        try:
            camera = camera_store.update_camera(camera_id, payload)
        except KeyError:
            return web.json_response({"error": "Camera not found"}, status=404)
        except ValueError as exc:
            return web.json_response({"error": str(exc)}, status=400)
        return web.json_response(camera)

    async def camera_delete_handler(request: web.Request) -> web.Response:
        camera_id = request.match_info.get("camera_id", "")
        camera = camera_store.get_camera(camera_id)
        if not camera:
            return web.json_response({"error": "Camera not found"}, status=404)
        camera_store.delete_camera(camera_id)
        return web.json_response({"deleted": True})

    async def camera_test_handler(request: web.Request) -> web.Response:
        camera_id = request.match_info.get("camera_id", "")
        try:
            result = camera_store.test_camera(camera_id)
        except KeyError:
            return web.json_response({"error": "Camera not found"}, status=404)
        status = 200 if result.get("ok") else 400
        return web.json_response(result, status=status)

    async def camera_test_payload_handler(request: web.Request) -> web.Response:
        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)
        if not isinstance(payload, dict):
            return web.json_response({"error": "Invalid camera payload"}, status=400)
        result = camera_store.test_camera_payload(payload)
        status = 200 if result.get("ok") else 400
        return web.json_response(result, status=status)

    async def pipeline_status_handler(_: web.Request) -> web.Response:
        payload = pipeline_status.as_dict() if pipeline_status else {"status": "unknown"}
        return web.json_response({"pipeline": payload})

    async def pipeline_start_handler(_: web.Request) -> web.Response:
        if not pipeline_controller:
            return web.json_response({"error": "Pipeline controller not available"}, status=400)
        started = pipeline_controller.start()
        return web.json_response({"started": started})

    async def pipeline_stop_handler(_: web.Request) -> web.Response:
        if not pipeline_controller:
            return web.json_response({"error": "Pipeline controller not available"}, status=400)
        stopped = pipeline_controller.stop()
        return web.json_response({"stopped": stopped})

    async def pipeline_restart_handler(_: web.Request) -> web.Response:
        if not pipeline_controller:
            return web.json_response({"error": "Pipeline controller not available"}, status=400)
        pipeline_controller.restart()
        return web.json_response({"restarted": True})

    async def telegram_get_handler(_: web.Request) -> web.Response:
        store = ConfigStore()
        config_payload = Config.from_sources(os.environ, store.load()).to_dict(redact=True)
        return web.json_response(config_payload.get("telegram", {}))

    async def telegram_post_handler(request: web.Request) -> web.Response:
        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)
        if not isinstance(payload, dict):
            return web.json_response({"error": "Invalid telegram payload"}, status=400)

        saved = ConfigStore().load()
        merged = merge_config(saved, {"telegram": payload})
        config_candidate = Config.from_sources(os.environ, saved=merged)
        errors = config_candidate.validate(allow_incomplete=True)
        if errors:
            return web.json_response({"errors": errors}, status=400)
        ConfigStore().save(merged)
        return web.json_response(config_candidate.to_dict(redact=True).get("telegram", {}))

    async def telegram_test_message_handler(_: web.Request) -> web.Response:
        if not TELEGRAM_AVAILABLE:
            return web.json_response({"error": "Telegram library not installed"}, status=400)

        config_payload = Config.from_sources(os.environ, ConfigStore().load())
        if not config_payload.telegram.enabled:
            return web.json_response({"error": "Telegram is disabled"}, status=400)
        if not config_payload.telegram.bot_token or not config_payload.telegram.chat_ids:
            return web.json_response({"error": "Telegram is misconfigured"}, status=400)

        bot = TelegramBot(config_payload.telegram)
        await bot.start()
        await bot.send_message("Test message from Smart Motion Detector.")
        await bot.stop()
        return web.json_response({"sent": True})

    async def telegram_test_snapshot_handler(request: web.Request) -> web.Response:
        if not TELEGRAM_AVAILABLE:
            return web.json_response({"error": "Telegram library not installed"}, status=400)
        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)
        camera_id = payload.get("camera_id") if isinstance(payload, dict) else None
        if not camera_id:
            return web.json_response({"error": "camera_id is required"}, status=400)

        config_payload = Config.from_sources(os.environ, ConfigStore().load())
        if not config_payload.telegram.enabled:
            return web.json_response({"error": "Telegram is disabled"}, status=400)
        if not config_payload.telegram.bot_token or not config_payload.telegram.chat_ids:
            return web.json_response({"error": "Telegram is misconfigured"}, status=400)

        try:
            snapshot_result = camera_store.snapshot_camera(camera_id)
        except KeyError:
            return web.json_response({"error": "Camera not found"}, status=404)

        if not snapshot_result.get("ok"):
            return web.json_response({"error": snapshot_result.get("error")}, status=400)

        image_bytes = base64.b64decode(snapshot_result["snapshot"])
        bot = TelegramBot(config_payload.telegram)
        await bot.start()
        await bot.send_photo_bytes(image_bytes, caption="Test snapshot from Smart Motion Detector.")
        await bot.stop()
        return web.json_response({"sent": True})

    async def ui_handler(_: web.Request) -> web.Response:
        html = UI_PATH.read_text(encoding="utf-8")
        return web.Response(text=html, content_type="text/html")

    app = web.Application()
    app.router.add_get("/", ui_handler)
    app.router.add_get("/index.html", ui_handler)
    app.router.add_get("/api/health", health_handler)
    app.router.add_get("/api/config", config_get_handler)
    app.router.add_post("/api/config", config_post_handler)
    app.router.add_get("/api/events", events_handler)
    app.router.add_get("/api/logs/tail", logs_tail_handler)
    app.router.add_get("/api/metrics", metrics_handler)
    app.router.add_get("/api/status", status_handler)
    app.router.add_get("/api/stats", stats_handler)
    app.router.add_get("/api/cameras", cameras_list_handler)
    app.router.add_post("/api/cameras", cameras_create_handler)
    app.router.add_post("/api/cameras/test", camera_test_payload_handler)
    app.router.add_get("/api/cameras/{camera_id}", camera_detail_handler)
    app.router.add_put("/api/cameras/{camera_id}", camera_update_handler)
    app.router.add_delete("/api/cameras/{camera_id}", camera_delete_handler)
    app.router.add_post("/api/cameras/{camera_id}/test", camera_test_handler)
    app.router.add_get("/api/pipeline/status", pipeline_status_handler)
    app.router.add_post("/api/pipeline/start", pipeline_start_handler)
    app.router.add_post("/api/pipeline/stop", pipeline_stop_handler)
    app.router.add_post("/api/pipeline/restart", pipeline_restart_handler)
    app.router.add_get("/api/notifications/telegram", telegram_get_handler)
    app.router.add_post("/api/notifications/telegram", telegram_post_handler)
    app.router.add_post("/api/notifications/telegram/test-message", telegram_test_message_handler)
    app.router.add_post("/api/notifications/telegram/test-snapshot", telegram_test_snapshot_handler)
    app.router.add_get("/ready", ready_handler)
    return app


def run_health_server(
    config: Config,
    mqtt_client: Optional[MQTTClient] = None,
    telegram_bot: Optional[TelegramBot] = None,
    event_store: Optional[EventStore] = None,
    pipeline_status: Optional[PipelineStatusTracker] = None,
    pipeline_controller: Optional[PipelineController] = None,
    host: str = "0.0.0.0",
    port: int = 8000,
) -> None:
    """Run the health server."""
    app = create_app(
        config,
        mqtt_client=mqtt_client,
        telegram_bot=telegram_bot,
        event_store=event_store,
        pipeline_status=pipeline_status,
        pipeline_controller=pipeline_controller,
    )
    logger.info("Starting health server on %s:%s", host, port)
    web.run_app(app, host=host, port=port)
