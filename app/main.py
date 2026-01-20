"""
Smart Motion Detector v2 - Main Entry Point
"""
import logging
from datetime import date
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_session, init_db
from app.models.camera import CameraTestRequest, CameraTestResponse
from app.services.camera import get_camera_service
from app.services.camera_crud import get_camera_crud_service
from app.services.events import get_event_service
from app.services.media import get_media_service
from app.services.settings import get_settings_service
from app.services.websocket import get_websocket_manager
from app.services.telegram import get_telegram_service
from app.services.logs import get_logs_service
from app.workers.retention import get_retention_worker


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Smart Motion Detector API",
    version="2.0.0",
    description="Person detection with thermal/color camera support"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production'da değiştir
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
media_service = get_media_service()
retention_worker = get_retention_worker()
websocket_manager = get_websocket_manager()
telegram_service = get_telegram_service()
logs_service = get_logs_service()


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Starting Smart Motion Detector v2")
    
    # Start retention worker
    retention_worker.start()
    logger.info("Retention worker started")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Smart Motion Detector v2")
    
    # Stop retention worker
    retention_worker.stop()
    logger.info("Retention worker stopped")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Smart Motion Detector v2", "status": "ok"}


@app.get("/ready")
async def ready():
    """Readiness probe endpoint."""
    return {"ready": True, "status": "ok"}


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "2.0.0",
        "uptime_s": 0,
        "ai": {"enabled": False, "reason": "not_configured"},
        "cameras": {"online": 0, "retrying": 0, "down": 0},
        "components": {"pipeline": "ok", "telegram": "disabled", "mqtt": "disabled"}
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
        
        # Convert events to dict
        events_list = []
        for event in result["events"]:
            events_list.append({
                "id": event.id,
                "camera_id": event.camera_id,
                "timestamp": event.timestamp.isoformat() + "Z",
                "confidence": event.confidence,
                "event_type": event.event_type,
                "summary": event.summary,
                "collage_url": event.collage_url or f"/api/events/{event.id}/collage",
                "gif_url": event.gif_url or f"/api/events/{event.id}/preview.gif",
                "mp4_url": event.mp4_url or f"/api/events/{event.id}/timelapse.mp4",
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
                "collage_url": event.collage_url or f"/api/events/{event.id}/collage",
                "gif_url": event.gif_url or f"/api/events/{event.id}/preview.gif",
                "mp4_url": event.mp4_url or f"/api/events/{event.id}/timelapse.mp4",
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
async def get_live_streams() -> Dict[str, Any]:
    """
    Get live stream URLs for all cameras.
    
    Returns:
        Dict containing list of live streams
        
    Raises:
        HTTPException: 500 if error occurs
    """
    try:
        # TODO: Implement camera service integration
        # For now, return empty list
        return {
            "streams": []
        }
        
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


@app.post("/api/telegram/test")
async def test_telegram(request: Dict[str, Any]) -> Dict[str, Any]:
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
        bot_token = request.get("bot_token")
        chat_ids = request.get("chat_ids", [])
        
        if not bot_token:
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
        
        # Test connection
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
