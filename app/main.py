"""
Smart Motion Detector v2 - Main Entry Point
"""
import logging
from pathlib import Path
from datetime import date
from typing import Any, Dict, Optional, List

import os
from fastapi import FastAPI, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import ValidationError, BaseModel
from sqlalchemy.orm import Session
import cv2
import time
import base64

from app.db.session import get_session, init_db
from app.db.models import Zone, ZoneMode, Camera, CameraStatus, Event
from app.models.camera import CameraTestRequest, CameraTestResponse
from app.models.config import AppConfig
from app.services.camera import get_camera_service
from app.services.camera_crud import get_camera_crud_service
from app.services.events import get_event_service
from app.services.media import get_media_service
from app.services.settings import get_settings_service
from app.services.websocket import get_websocket_manager
from app.services.telegram import get_telegram_service
from app.services.logs import get_logs_service
from app.services.ai_test import test_openai_connection
from app.services.ai import get_ai_service
from app.services.time_utils import get_detection_source
from app.services.go2rtc import get_go2rtc_service
from app.services.mqtt import get_mqtt_service
from telegram import Bot
from app.workers.retention import get_retention_worker
from app.workers.detector import get_detector_worker


# Configure logging
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)
APP_START_TS = time.time()

# TODO: Move to Redis/DB for multi-worker support
recording_state: Dict[str, bool] = {}

app = FastAPI(
    title="Smart Motion Detector API",
    version="2.0.0",
    description="Person detection with thermal/color camera support"
)

def _load_cors_origins() -> List[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_load_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Initialize services
settings_service = get_settings_service()
camera_service = get_camera_service()
camera_crud_service = get_camera_crud_service()
event_service = get_event_service()
ai_service = get_ai_service()
media_service = get_media_service()
retention_worker = get_retention_worker()
detector_worker = get_detector_worker()
websocket_manager = get_websocket_manager()
telegram_service = get_telegram_service()
logs_service = get_logs_service()
go2rtc_service = get_go2rtc_service()
mqtt_service = get_mqtt_service()


def _resolve_camera_rtsp_url(camera) -> Optional[str]:
    if camera.type.value == "thermal":
        return camera.rtsp_url_thermal
    if camera.type.value == "color":
        return camera.rtsp_url_color or camera.rtsp_url
    if camera.detection_source.value == "thermal" and camera.rtsp_url_thermal:
        return camera.rtsp_url_thermal
    return camera.rtsp_url_color or camera.rtsp_url_thermal


def _resolve_media_urls(event, ingress_path: str = "") -> Dict[str, Optional[str]]:
    """Resolve media URLs with Ingress path support."""
    collage_path = media_service.get_media_path(event.id, "collage")
    gif_path = media_service.get_media_path(event.id, "gif")
    mp4_path = media_service.get_media_path(event.id, "mp4")

    # Build URLs with Ingress prefix
    prefix = ingress_path.rstrip('/') if ingress_path else ""
    
    # Use DB URLs if present, otherwise generate
    base_collage = event.collage_url or f"/api/events/{event.id}/collage"
    base_gif = event.gif_url or f"/api/events/{event.id}/preview.gif"
    base_mp4 = event.mp4_url or f"/api/events/{event.id}/timelapse.mp4"
    
    # Add prefix if in Ingress mode
    collage_url = f"{prefix}{base_collage}" if prefix else base_collage
    gif_url = f"{prefix}{base_gif}" if prefix else base_gif
    mp4_url = f"{prefix}{base_mp4}" if prefix else base_mp4

    return {
        "collage_url": collage_url if collage_path and collage_path.exists() else None,
        "gif_url": gif_url if gif_path and gif_path.exists() else None,
        "mp4_url": mp4_url if mp4_path and mp4_path.exists() else None,
    }


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    import asyncio
    
    logger.info("Starting Smart Motion Detector v2")
    
    # Start retention worker
    retention_worker.start()
    logger.info("Retention worker started")
    
    # TASK 21: Wait for services to initialize
    logger.info("Waiting 10 seconds for services to initialize...")
    await asyncio.sleep(10)
    logger.info("Services initialized, application ready")

    # Start detector worker
    detector_worker.start()
    logger.info("Detector worker started")

    # Start MQTT service
    mqtt_service.start()
    logger.info("MQTT service started")

    # Sync cameras to go2rtc
    db = next(get_session())
    try:
        cameras = camera_crud_service.get_cameras(db)
        go2rtc_service.sync_all_cameras(cameras)
        logger.info("Cameras synced to go2rtc")
    except Exception as e:
        logger.error(f"Failed to sync cameras to go2rtc: {e}")
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Smart Motion Detector v2")
    
    # Stop retention worker
    retention_worker.stop()
    logger.info("Retention worker stopped")

    # Stop detector worker
    detector_worker.stop()
    logger.info("Detector worker stopped")

    # Stop MQTT service
    mqtt_service.stop()
    logger.info("MQTT service stopped")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Smart Motion Detector v2", "status": "ok"}


@app.get("/ready")
async def ready():
    """Readiness probe endpoint."""
    return {"ready": True, "status": "ok"}


@app.get("/api/debug/headers")
async def debug_headers(request: Request):
    """Debug endpoint to see all headers."""
    return {
        "all_headers": dict(request.headers),
        "x_ingress_path": request.headers.get("X-Ingress-Path", "NOT_FOUND"),
        "x_ingress_path_lower": request.headers.get("x-ingress-path", "NOT_FOUND"),
    }

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    uptime_s = max(0, int(time.time() - APP_START_TS))
    db = next(get_session())
    try:
        online = db.query(Camera).filter(Camera.status == CameraStatus.CONNECTED).count()
        retrying = db.query(Camera).filter(Camera.status == CameraStatus.RETRYING).count()
        down = db.query(Camera).filter(Camera.status == CameraStatus.DOWN).count()
    except Exception:
        online = retrying = down = 0
    finally:
        db.close()

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
    mqtt_status = "ok" if mqtt_service.connected else ("disabled" if not settings_service.load_config().mqtt.enabled else "disconnected")

    return {
        "status": "ok" if pipeline_status == "ok" else "degraded",
        "version": "2.0.0",
        "uptime_s": uptime_s,
        "ai": {"enabled": ai_enabled, "reason": ai_reason},
        "cameras": {"online": online, "retrying": retrying, "down": down},
        "components": {"pipeline": pipeline_status, "telegram": telegram_status, "mqtt": mqtt_status},
    }


@app.get("/api/settings")
async def get_settings() -> Dict[str, Any]:
    """
    Get current application settings.
    
    Returns settings with masked secrets (api_key, bot_token).
    
    Returns:
        Dict containing current settings
        
    Raises:
        HTTPException: 500 if settings cannot be loaded
    """
    try:
        settings = settings_service.get_settings()
        logger.info("Settings retrieved successfully")
        return settings
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to load settings: {str(e)}"
            }
        )


@app.get("/api/settings/defaults")
async def get_default_settings() -> Dict[str, Any]:
    try:
        defaults = settings_service.get_default_config()
        return settings_service._mask_secrets(defaults)
    except Exception as e:
        logger.error(f"Failed to load default settings: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to load defaults: {str(e)}",
            },
        )


@app.post("/api/settings/reset")
async def reset_settings() -> Dict[str, Any]:
    try:
        defaults = settings_service.get_default_config()
        settings_service.save_config(AppConfig(**defaults))
        logger.info("Settings reset to defaults")
        return settings_service.get_settings()
    except Exception as e:
        logger.error(f"Failed to reset settings: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to reset settings: {str(e)}",
            },
        )

@app.post("/api/settings/reset")
async def reset_settings() -> Dict[str, Any]:
    """
    Reset settings to defaults.
    
    Returns:
        Dict with default settings
        
    Raises:
        HTTPException: 500 if reset fails
    """
    try:
        # Delete config file to force reload of defaults
        import os
        config_path = "data/config.json"
        if os.path.exists(config_path):
            os.remove(config_path)
        
        # Get fresh default config
        default_settings = settings_service.get_settings()
        logger.info("Settings reset to defaults")
        return default_settings
        
    except Exception as e:
        logger.error(f"Failed to reset settings: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to reset settings: {str(e)}"
            }
        )


@app.put("/api/settings")
async def update_settings(partial_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update application settings.
    
    Supports partial updates - only provided fields are updated.
    Nested updates are supported (e.g., {"detection": {"model": "yolov8s-person"}}).
    
    Args:
        partial_data: Partial configuration data
        
    Returns:
        Dict containing updated settings with masked secrets
        
    Raises:
        HTTPException: 400 if validation fails, 500 if save fails
    """
    try:
        updated_settings = settings_service.update_settings(partial_data)
        
        # Check if MQTT settings changed and restart service if needed
        if "mqtt" in partial_data:
            logger.info("MQTT settings changed, restarting service...")
            mqtt_service.restart()

        logger.info("Settings updated successfully")
        return updated_settings
    except ValidationError as e:
        logger.error(f"Settings validation failed: {e}")
        # Extract validation errors
        errors = []
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        
        raise HTTPException(
            status_code=400,
            detail={
                "error": True,
                "code": "VALIDATION_ERROR",
                "message": "Settings validation failed",
                "errors": errors
            }
        )
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to update settings: {str(e)}"
            }
        )


@app.post("/api/cameras/test", response_model=CameraTestResponse)
async def test_camera(request: CameraTestRequest) -> CameraTestResponse:
    """
    Test RTSP camera connection and capture snapshot.
    
    Tests camera connectivity, measures latency, and returns a snapshot.
    Supports thermal, color, and dual camera configurations.
    
    Args:
        request: Camera test request with RTSP URLs
        
    Returns:
        CameraTestResponse with snapshot and latency info
        
    Raises:
        HTTPException: 400 if validation fails, 500 if connection fails
    """
    try:
        logger.info(f"Testing camera connection: type={request.type}")
        
        # Test based on camera type
        if request.type == "thermal":
            result = camera_service.test_rtsp_connection(request.rtsp_url_thermal)
        elif request.type == "color":
            result = camera_service.test_rtsp_connection(request.rtsp_url_color)
        elif request.type == "dual":
            result = camera_service.test_dual_camera(
                request.rtsp_url_thermal,
                request.rtsp_url_color
            )
        else:
            raise ValueError(f"Invalid camera type: {request.type}")
        
        # Check if test was successful
        if not result["success"]:
            logger.warning(f"Camera test failed: {result['error_reason']}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": True,
                    "code": "RTSP_CONNECTION_FAILED",
                    "message": result["error_reason"]
                }
            )
        
        logger.info(f"Camera test successful: latency={result['latency_ms']}ms")
        
        return CameraTestResponse(
            success=True,
            snapshot_base64=result["snapshot_base64"],
            latency_ms=result["latency_ms"],
            error_reason=None
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValidationError as e:
        logger.error(f"Camera test validation failed: {e}")
        errors = []
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        
        raise HTTPException(
            status_code=400,
            detail={
                "error": True,
                "code": "VALIDATION_ERROR",
                "message": "Camera test validation failed",
                "errors": errors
            }
        )
    except Exception as e:
        logger.error(f"Camera test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "SNAPSHOT_FAILED",
                "message": f"Failed to test camera: {str(e)}"
            }
        )


@app.get("/api/events")
async def get_events(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Events per page"),
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    date: Optional[date] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence"),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    Get events with pagination and filtering.
    
    Supports filtering by camera_id, date, and minimum confidence.
    Results are ordered by timestamp (newest first).
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of events per page (max 100)
        camera_id: Filter by camera ID (optional)
        date: Filter by date (optional)
        confidence: Minimum confidence threshold (optional)
        db: Database session
        
    Returns:
        Dict containing page, page_size, total, and events list
        
    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        result = event_service.get_events(
            db=db,
            page=page,
            page_size=page_size,
            camera_id=camera_id,
            date_filter=date,
            min_confidence=confidence,
        )
        
        # Get Ingress path from header
        ingress_path = request.headers.get("X-Ingress-Path", "")
        logger.info(f"GET /api/events - X-Ingress-Path: '{ingress_path}'")
        
        # Convert events to dict
        events_list = []
        for event in result["events"]:
            media_urls = _resolve_media_urls(event, ingress_path)
            logger.info(f"Event {event.id} - collage_url: {media_urls['collage_url']}")
            events_list.append({
                "id": event.id,
                "camera_id": event.camera_id,
                "timestamp": event.timestamp.isoformat() + "Z",
                "confidence": event.confidence,
                "event_type": event.event_type,
                "summary": event.summary,
                "collage_url": media_urls["collage_url"],
                "gif_url": media_urls["gif_url"],
                "mp4_url": media_urls["mp4_url"],
            })
        
        return {
            "page": result["page"],
            "page_size": result["page_size"],
            "total": result["total"],
            "events": events_list,
        }
        
    except Exception as e:
        logger.error(f"Failed to get events: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to retrieve events: {str(e)}"
            }
        )


@app.get("/api/events/{event_id}")
async def get_event(
    request: Request,
    event_id: str,
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    Get event by ID.
    
    Returns detailed event information including AI summary and media URLs.
    
    Args:
        event_id: Event ID
        db: Database session
        
    Returns:
        Dict containing event details
        
    Raises:
        HTTPException: 404 if event not found, 500 if database error
    """
    try:
        event = event_service.get_event_by_id(db=db, event_id=event_id)
        
        if not event:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": True,
                    "code": "EVENT_NOT_FOUND",
                    "message": f"Event with id {event_id} not found"
                }
            )
        
        # Get Ingress path from header
        ingress_path = request.headers.get("X-Ingress-Path", "")
        media_urls = _resolve_media_urls(event, ingress_path)
        return {
            "id": event.id,
            "camera_id": event.camera_id,
            "timestamp": event.timestamp.isoformat() + "Z",
            "confidence": event.confidence,
            "event_type": event.event_type,
            "summary": event.summary,
            "ai": {
                "enabled": event.ai_enabled,
                "reason": event.ai_reason,
                "text": event.summary,
            },
            "media": {
                "collage_url": media_urls["collage_url"],
                "gif_url": media_urls["gif_url"],
                "mp4_url": media_urls["mp4_url"],
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get event {event_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to retrieve event: {str(e)}"
            }
        )


@app.delete("/api/events/{event_id}")
async def delete_event(
    event_id: str,
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    Delete event by ID.
    
    Args:
        event_id: Event ID
        db: Database session
        
    Returns:
        Dict with deleted status and event ID
        
    Raises:
        HTTPException: 404 if event not found, 500 if database error
    """
    try:
        deleted = event_service.delete_event(db=db, event_id=event_id)
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": True,
                    "code": "EVENT_NOT_FOUND",
                    "message": f"Event with id {event_id} not found"
                }
            )
        
        return {
            "deleted": True,
            "id": event_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete event {event_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to delete event: {str(e)}"
            }
        )


@app.post("/api/events/bulk-delete")
async def bulk_delete_events(
    request: Dict[str, Any],
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    Bulk delete events by IDs.
    
    Args:
        request: Dict with event_ids list
        db: Database session
        
    Returns:
        Dict with deleted_count and failed_ids
        
    Raises:
        HTTPException: 400 if validation fails, 500 if error
    """
    try:
        event_ids = request.get("event_ids", [])
        
        if not event_ids:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "VALIDATION_ERROR",
                    "message": "event_ids is required"
                }
            )
        
        deleted_count = 0
        failed_ids = []
        
        for event_id in event_ids:
            try:
                deleted = event_service.delete_event(db=db, event_id=event_id)
                if deleted:
                    deleted_count += 1
                else:
                    failed_ids.append(event_id)
            except Exception as e:
                logger.error(f"Failed to delete event {event_id}: {e}")
                failed_ids.append(event_id)
        
        return {
            "deleted_count": deleted_count,
            "failed_ids": failed_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk delete failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Bulk delete failed: {str(e)}"
            }
        )


@app.get("/api/events/{event_id}/collage")
async def get_event_collage(event_id: str) -> FileResponse:
    """
    Get event collage image.
    
    Args:
        event_id: Event ID
        
    Returns:
        JPEG collage image
        
    Raises:
        HTTPException: 404 if media not found
    """
    try:
        media_path = media_service.get_media_path(event_id, "collage")
        
        if not media_path or not media_path.exists():
            raise HTTPException(
                status_code=404,
                detail={
                    "error": True,
                    "code": "MEDIA_NOT_FOUND",
                    "message": f"Collage not found for event {event_id}"
                }
            )
        
        return FileResponse(
            path=str(media_path),
            media_type="image/jpeg",
            filename=f"event-{event_id}-collage.jpg"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get collage for event {event_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to retrieve collage: {str(e)}"
            }
        )


@app.get("/api/events/{event_id}/preview.gif")
async def get_event_gif(event_id: str) -> FileResponse:
    """
    Get event preview GIF.
    
    Args:
        event_id: Event ID
        
    Returns:
        Animated GIF
        
    Raises:
        HTTPException: 404 if media not found
    """
    try:
        media_path = media_service.get_media_path(event_id, "gif")
        
        if not media_path or not media_path.exists():
            raise HTTPException(
                status_code=404,
                detail={
                    "error": True,
                    "code": "MEDIA_NOT_FOUND",
                    "message": f"GIF not found for event {event_id}"
                }
            )
        
        return FileResponse(
            path=str(media_path),
            media_type="image/gif",
            filename=f"event-{event_id}-preview.gif"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get GIF for event {event_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to retrieve GIF: {str(e)}"
            }
        )


@app.get("/api/events/{event_id}/timelapse.mp4")
async def get_event_mp4(event_id: str) -> FileResponse:
    """
    Get event timelapse MP4.
    
    Args:
        event_id: Event ID
        
    Returns:
        MP4 video
        
    Raises:
        HTTPException: 404 if media not found
    """
    try:
        media_path = media_service.get_media_path(event_id, "mp4")
        
        if not media_path or not media_path.exists():
            raise HTTPException(
                status_code=404,
                detail={
                    "error": True,
                    "code": "MEDIA_NOT_FOUND",
                    "message": f"MP4 not found for event {event_id}"
                }
            )
        
        return FileResponse(
            path=str(media_path),
            media_type="video/mp4",
            filename=f"event-{event_id}-timelapse.mp4"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get MP4 for event {event_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to retrieve MP4: {str(e)}"
            }
        )


@app.get("/api/live")
async def get_live_streams(db: Session = Depends(get_session)) -> Dict[str, Any]:
    """
    Get live stream URLs for all cameras.
    
    Returns:
        Dict containing list of live streams
        
    Raises:
        HTTPException: 500 if error occurs
    """
    try:
        settings = settings_service.load_config()
        output_mode = settings.live.output_mode
        cameras = camera_crud_service.get_cameras(db)
        streams = []

        for camera in cameras:
            if not camera.enabled or "live" not in (camera.stream_roles or []):
                continue
            streams.append({
                "camera_id": camera.id,
                "name": camera.name,
                "stream_url": f"/api/live/{camera.id}.mjpeg" if output_mode == "mjpeg" else "",
                "output_mode": output_mode
            })

        return {"streams": streams}

    except Exception as e:
        logger.error(f"Failed to get live streams: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to retrieve live streams: {str(e)}"
            }
        )


@app.get("/api/live/{camera_id}.mjpeg")
async def get_live_stream(camera_id: str, db: Session = Depends(get_session)):
    """
    Stream live MJPEG feed for a camera.

    Args:
        camera_id: Camera ID
        db: Database session

    Returns:
        StreamingResponse of MJPEG frames
    """
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(
            status_code=404,
            detail={
                "error": True,
                "code": "CAMERA_NOT_FOUND",
                "message": f"Camera not found: {camera_id}"
            }
        )

    settings = settings_service.load_config()
    if settings.live.output_mode == "webrtc":
        raise HTTPException(
            status_code=409,
            detail={
                "error": True,
                "code": "LIVE_MODE_MISMATCH",
                "message": "Live output mode is WebRTC; MJPEG stream unavailable."
            }
        )

    stream_url = _resolve_camera_rtsp_url(camera)

    if not stream_url:
        raise HTTPException(
            status_code=400,
            detail={
                "error": True,
                "code": "STREAM_URL_MISSING",
                "message": "No RTSP URL configured for live stream."
            }
        )

    if settings.stream.protocol == "tcp":
        stream_url = camera_service.force_tcp_protocol(stream_url)
    logger.info(
        "Opening live stream for camera %s: %s",
        camera_id,
        stream_url
    )

    def detector_stream_generator():
        while True:
            frame = detector_worker.get_latest_frame(camera_id)
            if frame is None:
                time.sleep(0.1)
                continue
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            success, buffer = cv2.imencode(".jpg", frame, encode_params)
            if not success:
                time.sleep(0.05)
                continue
            frame_bytes = buffer.tobytes()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )

    cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, settings.stream.buffer_size)
    if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
    if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
    if not cap.isOpened():
        logger.warning("Live stream fallback to detector frames for %s", camera_id)
        return StreamingResponse(
            detector_stream_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )

    # Warmup read to fail fast on dead streams
    warmup_ok, warmup_frame = cap.read()
    if not warmup_ok or warmup_frame is None:
        cap.release()
        logger.warning("Live stream read failed, fallback to detector frames for %s", camera_id)
        return StreamingResponse(
            detector_stream_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )

    def stream_generator():
        consecutive_failures = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures >= 30:
                        logger.error("Live stream stalled for camera %s", camera_id)
                        break
                    time.sleep(0.2)
                    continue
                consecutive_failures = 0

                encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                success, buffer = cv2.imencode(".jpg", frame, encode_params)
                if not success:
                    continue

                frame_bytes = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
        finally:
            cap.release()

    return StreamingResponse(
        stream_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/cameras/{camera_id}/snapshot")
async def get_camera_snapshot(camera_id: str, db: Session = Depends(get_session)):
    """
    Get a snapshot for a camera.
    """
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(
            status_code=404,
            detail={
                "error": True,
                "code": "CAMERA_NOT_FOUND",
                "message": f"Camera not found: {camera_id}"
            }
        )

    stream_url = _resolve_camera_rtsp_url(camera)
    if not stream_url:
        raise HTTPException(
            status_code=400,
            detail={
                "error": True,
                "code": "STREAM_URL_MISSING",
                "message": "No RTSP URL configured for snapshot."
            }
        )

    settings = settings_service.load_config()
    if settings.stream.protocol == "tcp":
        stream_url = camera_service.force_tcp_protocol(stream_url)

    result = camera_service.test_rtsp_connection(stream_url)
    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "RTSP_CONNECTION_FAILED",
                "message": result["error_reason"] or "Snapshot capture failed"
            }
        )

    snapshot_data = result["snapshot_base64"].split(",", 1)[1]
    image_bytes = base64.b64decode(snapshot_data)
    return Response(content=image_bytes, media_type="image/jpeg")


@app.get("/api/cameras/{camera_id}/zones")
async def get_camera_zones(camera_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(
            status_code=404,
            detail={
                "error": True,
                "code": "CAMERA_NOT_FOUND",
                "message": f"Camera not found: {camera_id}"
            }
        )

    zones = (
        db.query(Zone)
        .filter(Zone.camera_id == camera_id)
        .all()
    )
    return {
        "zones": [
            {
                "id": zone.id,
                "name": zone.name,
                "enabled": zone.enabled,
                "mode": zone.mode.value,
                "polygon": zone.polygon,
                "created_at": zone.created_at.isoformat() + "Z",
                "updated_at": zone.updated_at.isoformat() + "Z",
            }
            for zone in zones
        ]
    }


@app.post("/api/cameras/{camera_id}/zones")
async def create_zone(camera_id: str, request: Dict[str, Any], db: Session = Depends(get_session)) -> Dict[str, Any]:
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(
            status_code=404,
            detail={
                "error": True,
                "code": "CAMERA_NOT_FOUND",
                "message": f"Camera not found: {camera_id}"
            }
        )

    name = request.get("name", "").strip()
    mode = request.get("mode", "person")
    polygon = request.get("polygon", [])

    if not name:
        raise HTTPException(
            status_code=400,
            detail={
                "error": True,
                "code": "VALIDATION_ERROR",
                "message": "Zone name is required"
            }
        )

    if not isinstance(polygon, list) or len(polygon) < 3 or len(polygon) > 20:
        raise HTTPException(
            status_code=400,
            detail={
                "error": True,
                "code": "VALIDATION_ERROR",
                "message": "Polygon must have 3-20 points"
            }
        )

    for point in polygon:
        if (
            not isinstance(point, list)
            or len(point) != 2
            or not all(isinstance(value, (int, float)) for value in point)
            or not (0.0 <= point[0] <= 1.0)
            or not (0.0 <= point[1] <= 1.0)
        ):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "VALIDATION_ERROR",
                    "message": "Polygon points must be [x,y] normalized (0-1)"
                }
            )

    zone = Zone(
        camera_id=camera_id,
        name=name,
        enabled=bool(request.get("enabled", True)),
        mode=ZoneMode(mode),
        polygon=polygon
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)

    return {
        "id": zone.id,
        "name": zone.name,
        "enabled": zone.enabled,
        "mode": zone.mode.value,
        "polygon": zone.polygon,
        "created_at": zone.created_at.isoformat() + "Z",
        "updated_at": zone.updated_at.isoformat() + "Z",
    }


@app.put("/api/zones/{zone_id}")
async def update_zone(zone_id: str, request: Dict[str, Any], db: Session = Depends(get_session)) -> Dict[str, Any]:
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=404,
            detail={
                "error": True,
                "code": "ZONE_NOT_FOUND",
                "message": f"Zone not found: {zone_id}"
            }
        )

    if "name" in request:
        zone.name = request["name"]
    if "enabled" in request:
        zone.enabled = bool(request["enabled"])
    if "mode" in request:
        zone.mode = ZoneMode(request["mode"])
    if "polygon" in request:
        zone.polygon = request["polygon"]

    db.commit()
    db.refresh(zone)

    return {
        "id": zone.id,
        "name": zone.name,
        "enabled": zone.enabled,
        "mode": zone.mode.value,
        "polygon": zone.polygon,
        "created_at": zone.created_at.isoformat() + "Z",
        "updated_at": zone.updated_at.isoformat() + "Z",
    }


@app.delete("/api/zones/{zone_id}")
async def delete_zone(zone_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=404,
            detail={
                "error": True,
                "code": "ZONE_NOT_FOUND",
                "message": f"Zone not found: {zone_id}"
            }
        )

    db.delete(zone)
    db.commit()
    return {"deleted": True, "zone_id": zone_id}


@app.get("/api/cameras")
async def get_cameras(db: Session = Depends(get_session)) -> Dict[str, Any]:
    """
    Get all cameras.
    
    Returns:
        Dict containing list of cameras with masked RTSP URLs
        
    Raises:
        HTTPException: 500 if error occurs
    """
    try:
        cameras = camera_crud_service.get_cameras(db)
        
        # Convert to dict with masked URLs
        cameras_list = [camera_crud_service.mask_rtsp_urls(cam) for cam in cameras]
        
        return {
            "cameras": cameras_list
        }
        
    except Exception as e:
        logger.error(f"Failed to get cameras: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to retrieve cameras: {str(e)}"
            }
        )


@app.post("/api/cameras")
async def create_camera(
    request: Dict[str, Any],
    db: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Create a new camera.
    
    Args:
        request: Camera data
        db: Database session
        
    Returns:
        Created camera with masked RTSP URLs
        
    Raises:
        HTTPException: 400 if validation fails, 500 if creation fails
    """
    try:
        camera = camera_crud_service.create_camera(
            db=db,
            name=request.get("name"),
            camera_type=request.get("type"),
            rtsp_url_thermal=request.get("rtsp_url_thermal"),
            rtsp_url_color=request.get("rtsp_url_color"),
            channel_color=request.get("channel_color"),
            channel_thermal=request.get("channel_thermal"),
            detection_source=request.get("detection_source", "auto"),
            stream_roles=request.get("stream_roles", ["detect", "live"]),
            enabled=request.get("enabled", True),
            zones=request.get("zones", []),
            motion_config=request.get("motion_config")
        )

        if camera.enabled and "detect" in (camera.stream_roles or []):
            try:
                detector_worker.start_camera_detection(camera)
            except Exception as e:
                logger.error("Failed to start detection for camera %s: %s", camera.id, e)
        else:
            detector_worker.stop_camera_detection(camera.id)

        # Add to go2rtc
        rtsp_url = camera.rtsp_url_thermal or camera.rtsp_url_color or camera.rtsp_url
        if rtsp_url:
            go2rtc_service.add_camera(camera.id, rtsp_url)

        return camera_crud_service.mask_rtsp_urls(camera)
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": True,
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Failed to create camera: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to create camera: {str(e)}"
            }
        )


@app.put("/api/cameras/{camera_id}")
async def update_camera(
    camera_id: str,
    request: Dict[str, Any],
    db: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Update camera.
    
    Args:
        camera_id: Camera ID
        request: Update data (partial)
        db: Database session
        
    Returns:
        Updated camera with masked RTSP URLs
        
    Raises:
        HTTPException: 404 if not found, 400 if validation fails, 500 if update fails
    """
    try:
        camera = camera_crud_service.update_camera(db, camera_id, request)
        
        if not camera:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": True,
                    "code": "CAMERA_NOT_FOUND",
                    "message": f"Camera with id {camera_id} not found"
                }
            )
        
        if camera.enabled and "detect" in (camera.stream_roles or []):
            try:
                detector_worker.start_camera_detection(camera)
            except Exception as e:
                logger.error("Failed to start detection for camera %s: %s", camera.id, e)

        return camera_crud_service.mask_rtsp_urls(camera)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": True,
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Failed to update camera {camera_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to update camera: {str(e)}"
            }
        )


@app.delete("/api/cameras/{camera_id}")
async def delete_camera(
    camera_id: str,
    db: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Delete camera.
    
    Args:
        camera_id: Camera ID
        db: Database session
        
    Returns:
        Dict with deleted status
        
    Raises:
        HTTPException: 404 if not found, 500 if deletion fails
    """
    try:
        # Remove from go2rtc first
        go2rtc_service.remove_camera(camera_id)
        
        detector_worker.stop_camera_detection(camera_id)
        deleted = camera_crud_service.delete_camera(db, camera_id)
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": True,
                    "code": "CAMERA_NOT_FOUND",
                    "message": f"Camera with id {camera_id} not found"
                }
            )
        
        return {
            "deleted": True,
            "id": camera_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete camera {camera_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to delete camera: {str(e)}"
            }
        )


@app.get("/api/cameras/{camera_id}/record")
async def get_recording_status(camera_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(
            status_code=404,
            detail={
                "error": True,
                "code": "CAMERA_NOT_FOUND",
                "message": f"Camera not found: {camera_id}",
            },
        )
    return {"camera_id": camera_id, "recording": recording_state.get(camera_id, False)}


@app.post("/api/cameras/{camera_id}/record/start")
async def start_recording(camera_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(
            status_code=404,
            detail={
                "error": True,
                "code": "CAMERA_NOT_FOUND",
                "message": f"Camera not found: {camera_id}",
            },
        )
    recording_state[camera_id] = True
    return {"camera_id": camera_id, "recording": True}


@app.post("/api/cameras/{camera_id}/record/stop")
async def stop_recording(camera_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(
            status_code=404,
            detail={
                "error": True,
                "code": "CAMERA_NOT_FOUND",
                "message": f"Camera not found: {camera_id}",
            },
        )
    recording_state[camera_id] = False
    return {"camera_id": camera_id, "recording": False}

@app.websocket("/api/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time event and status updates.
    
    Clients can connect to receive:
    - Event notifications: {"type": "event", "data": {...}}
    - Status updates: {"type": "status", "data": {...}}
    
    Args:
        websocket: WebSocket connection
    """
    await websocket_manager.connect(websocket)
    
    try:
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for any message from client (ping/pong)
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received WebSocket message: {data}")
                
                # Echo back for ping/pong
                if data == "ping":
                    await websocket.send_text("pong")
                    
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    finally:
        await websocket_manager.disconnect(websocket)


@app.post("/api/ai/test")
async def test_ai(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test OpenAI API connection.
    
    Args:
        request: Dict with api_key and model
        
    Returns:
        Dict with test results
        
    Raises:
        HTTPException: 400 if validation fails, 500 if test fails
    """
    try:
        api_key = request.get("api_key")
        model = request.get("model", "gpt-4o")
        
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "VALIDATION_ERROR",
                    "message": "api_key is required"
                }
            )
        
        # Test connection
        result = await test_openai_connection(api_key, model)
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": True,
                    "code": "AI_TEST_FAILED",
                    "message": result["message"]
                }
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"AI test failed: {str(e)}"
            }
        )


class AiEventTestRequest(BaseModel):
    event_id: str


@app.post("/api/ai/test-event")
async def test_ai_event(
    request: AiEventTestRequest,
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    Test AI summary generation for an existing event.
    """
    try:
        config = settings_service.load_config()
        if not config.ai.enabled:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "AI_DISABLED",
                    "message": "AI is disabled"
                }
            )
        if not config.ai.api_key or config.ai.api_key == "***REDACTED***":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "NO_API_KEY",
                    "message": "API key is required"
                }
            )

        event = event_service.get_event_by_id(db=db, event_id=request.event_id)
        if not event:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": True,
                    "code": "EVENT_NOT_FOUND",
                    "message": f"Event with id {request.event_id} not found"
                }
            )

        camera = db.query(Camera).filter(Camera.id == event.camera_id).first()
        if not camera:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": True,
                    "code": "CAMERA_NOT_FOUND",
                    "message": f"Camera with id {event.camera_id} not found"
                }
            )

        collage_path = media_service.get_media_path(event.id, "collage")
        if not collage_path or not collage_path.exists():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "COLLAGE_NOT_FOUND",
                    "message": "Event collage not found"
                }
            )

        detection_source = get_detection_source(camera.detection_source.value)
        camera_payload = {
            "id": camera.id,
            "name": camera.name,
            "type": camera.type.value if camera.type else None,
            "detection_source": detection_source,
            "use_custom_prompt": False,
            "ai_prompt_override": None,
        }
        event_payload = {
            "id": event.id,
            "camera_id": event.camera_id,
            "timestamp": event.timestamp.isoformat() + "Z",
            "confidence": event.confidence,
        }

        prompt = ai_service._get_prompt_for_event(event_payload, camera_payload)
        summary = await ai_service.analyze_event(event_payload, collage_path, camera_payload)

        return {
            "success": bool(summary),
            "event_id": event.id,
            "camera_id": event.camera_id,
            "camera_type": camera_payload["type"],
            "detection_source": detection_source,
            "prompt": prompt,
            "summary": summary,
            "model": config.ai.model,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI event test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"AI event test failed: {str(e)}"
            }
        )


class TelegramTestRequest(BaseModel):
    bot_token: Optional[str] = None
    chat_ids: List[str]
    event_id: Optional[str] = None


@app.post("/api/telegram/test")
async def test_telegram(
    request: TelegramTestRequest,
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    Test Telegram bot connection.
    
    Args:
        request: Dict with bot_token and chat_ids
        
    Returns:
        Dict with test results
        
    Raises:
        HTTPException: 400 if validation fails, 500 if test fails
    """
    try:
        bot_token = request.bot_token
        chat_ids = request.chat_ids

        if not bot_token or bot_token == "***REDACTED***":
            config = settings_service.load_config()
            bot_token = config.telegram.bot_token

        if not bot_token or bot_token == "***REDACTED***":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "VALIDATION_ERROR",
                    "message": "bot_token is required"
                }
            )
        
        if not chat_ids:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": True,
                    "code": "VALIDATION_ERROR",
                    "message": "chat_ids is required"
                }
            )
        
        # Try to send a sample with latest event media (if available)
        event = None
        if request.event_id:
            event = event_service.get_event_by_id(db=db, event_id=request.event_id)
        if not event:
            event = db.query(Event).order_by(Event.timestamp.desc()).first()

        if event:
            camera_name = "Test Camera"
            camera = db.query(Camera).filter(Camera.id == event.camera_id).first()
            if camera and camera.name:
                camera_name = camera.name

            message = f"🧪 Telegram test\n📹 {camera_name}"
            collage_path = media_service.get_media_path(event.id, "collage")
            gif_path = media_service.get_media_path(event.id, "gif")

            bot = Bot(token=bot_token)
            for chat_id in chat_ids:
                if collage_path and collage_path.exists():
                    with open(collage_path, "rb") as photo:
                        await bot.send_photo(chat_id=chat_id, photo=photo, caption=message)
                else:
                    await bot.send_message(chat_id=chat_id, text=message)

                if gif_path and gif_path.exists():
                    with open(gif_path, "rb") as gif:
                        await bot.send_document(chat_id=chat_id, document=gif, caption="🎬 Event Animation")

            return {"success": True, "message": "Telegram test message sent"}

        # Fallback: basic connection test
        result = await telegram_service.test_connection(bot_token, chat_ids)
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": True,
                    "code": "TELEGRAM_TEST_FAILED",
                    "message": result["error_reason"]
                }
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Telegram test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Telegram test failed: {str(e)}"
            }
        )




@app.get("/api/logs")
async def get_logs(lines: int = Query(200, ge=1, le=1000, description="Number of log lines")) -> Dict[str, Any]:
    """
    Get application logs.
    
    Args:
        lines: Number of log lines to return (max 1000)
        
    Returns:
        Dict with log lines
        
    Raises:
        HTTPException: 500 if error occurs
    """
    try:
        log_lines = logs_service.get_logs(lines)
        
        return {
            "lines": log_lines,
            "count": len(log_lines)
        }
        
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to retrieve logs: {str(e)}"
            }
        )


@app.get("/api/system/info")
async def get_system_info() -> Dict[str, Any]:
    """
    Get system information (CPU, memory, disk).
    
    Returns:
        Dict with system metrics
        
    Raises:
        HTTPException: 500 if error occurs
    """
    try:
        import psutil
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024 ** 3)
        memory_total_gb = memory.total / (1024 ** 3)
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_used_gb = disk.used / (1024 ** 3)
        disk_total_gb = disk.total / (1024 ** 3)
        disk_percent = disk.percent
        
        return {
            "cpu": {
                "percent": round(cpu_percent, 1)
            },
            "memory": {
                "used_gb": round(memory_used_gb, 2),
                "total_gb": round(memory_total_gb, 2),
                "percent": round(memory_percent, 1)
            },
            "disk": {
                "used_gb": round(disk_used_gb, 2),
                "total_gb": round(disk_total_gb, 2),
                "percent": round(disk_percent, 1)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to retrieve system info: {str(e)}"
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
