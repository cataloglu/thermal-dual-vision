import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Camera, Event, Zone, ZoneMode
from app.db.session import get_session
from app.dependencies import (
    camera_crud_service,
    camera_service,
    continuous_recorder,
    detector_worker,
    go2rtc_service,
    mqtt_service,
    recording_state_service,
    settings_service,
)
from app.models.camera import CameraTestRequest, CameraTestResponse
from app.utils.rtsp import validate_rtsp_url
from app.utils.stream_helpers import (
    get_live_rtsp_urls,
    get_recording_rtsp_url,
    resolve_default_rtsp_url,
    resolve_default_stream_source,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _normalize_rtsp_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return validate_rtsp_url(cleaned)


def _sanitize_rtsp_updates(payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
    sanitized: Dict[str, Optional[str]] = {}
    for key in ("rtsp_url", "rtsp_url_color", "rtsp_url_thermal", "rtsp_url_detection"):
        if key not in payload:
            continue
        value = payload.get(key)
        if value is None:
            sanitized[key] = None
            continue
        if not isinstance(value, str):
            raise ValueError(f"{key} must be a string")
        sanitized[key] = _normalize_rtsp_value(value)
    return sanitized


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.post("/api/cameras/test", response_model=CameraTestResponse)
async def test_camera(request: CameraTestRequest) -> CameraTestResponse:
    try:
        if request.type == "thermal":
            result = camera_service.test_rtsp_connection(request.rtsp_url_thermal)
        elif request.type == "color":
            result = camera_service.test_rtsp_connection(request.rtsp_url_color)
        elif request.type == "dual":
            result = camera_service.test_dual_camera(request.rtsp_url_thermal, request.rtsp_url_color)
        else:
            raise ValueError(f"Invalid camera type: {request.type}")
        if not result["success"]:
            raise HTTPException(status_code=500, detail={"error": True, "code": "RTSP_CONNECTION_FAILED", "message": result["error_reason"]})
        return CameraTestResponse(success=True, snapshot_base64=result["snapshot_base64"], latency_ms=result["latency_ms"], error_reason=None)
    except HTTPException:
        raise
    except ValidationError as e:
        errors = [f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in e.errors()]
        raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": "Camera test validation failed", "errors": errors})
    except Exception as e:
        logger.error(f"Camera test failed: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "SNAPSHOT_FAILED", "message": f"Failed to test camera: {str(e)}"})


@router.get("/api/cameras")
async def get_cameras(db: Session = Depends(get_session)) -> Dict[str, Any]:
    try:
        cameras = camera_crud_service.get_cameras(db)
        return {"cameras": [camera_crud_service.mask_rtsp_urls(cam) for cam in cameras]}
    except Exception as e:
        logger.error(f"Failed to get cameras: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to retrieve cameras: {str(e)}"})


@router.get("/api/cameras/status")
async def get_cameras_status(db: Session = Depends(get_session)) -> Dict[str, Any]:
    """Return camera monitor status payload used by CameraMonitor page."""
    try:
        cameras = camera_crud_service.get_cameras(db)
        go2rtc_ok = bool(go2rtc_service.ensure_enabled())

        # Aggregate event stats once to avoid per-camera N+1 queries.
        since_24h = _utc_now_naive() - timedelta(hours=24)
        event_rows = (
            db.query(
                Event.camera_id.label("camera_id"),
                func.count(Event.id).label("event_count_24h"),
                func.max(Event.timestamp).label("last_event_ts"),
            )
            .filter(Event.timestamp >= since_24h)
            .group_by(Event.camera_id)
            .all()
        )
        event_map = {
            row.camera_id: {
                "count": int(row.event_count_24h or 0),
                "last_ts": row.last_event_ts,
            }
            for row in event_rows
        }

        # Determine detecting state from the active worker mode.
        detecting_ids: set[str] = set()
        try:
            worker_mode = (
                getattr(getattr(settings_service.load_config(), "performance", None), "worker_mode", "threading")
                or "threading"
            )
            if worker_mode == "multiprocessing":
                from app.workers.detector_mp import get_mp_detector_worker
                mp_worker = get_mp_detector_worker()
                if mp_worker.running:
                    detecting_ids = set(mp_worker.processes.keys())
            else:
                from app.workers.detector import get_detector_worker
                thread_worker = get_detector_worker()
                if thread_worker.running:
                    detecting_ids = set(thread_worker.threads.keys())
        except Exception as e:
            logger.debug("Could not resolve detecting state: %s", e)

        payload = []
        for cam in cameras:
            roles = cam.stream_roles if isinstance(cam.stream_roles, list) else []
            can_detect = (not roles) or ("detect" in roles)
            event_stats = event_map.get(cam.id, {"count": 0, "last_ts": None})

            payload.append({
                "id": cam.id,
                "name": cam.name,
                "type": cam.type.value if cam.type else "color",
                "enabled": bool(cam.enabled),
                "status": cam.status.value if cam.status else "initializing",
                "last_frame_ts": cam.last_frame_ts.isoformat() + "Z" if cam.last_frame_ts else None,
                "event_count_24h": event_stats["count"],
                "last_event_ts": event_stats["last_ts"].isoformat() + "Z" if event_stats["last_ts"] else None,
                "recording": bool(cam.enabled and continuous_recorder.is_recording(cam.id)),
                "detecting": bool(cam.enabled and can_detect and cam.id in detecting_ids),
                "go2rtc_ok": go2rtc_ok,
                "stream_roles": roles,
            })

        return {"cameras": payload, "go2rtc_ok": go2rtc_ok}
    except Exception as e:
        logger.error("Failed to get cameras status: %s", e)
        raise HTTPException(
            status_code=500,
            detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to retrieve camera status: {str(e)}"},
        )


@router.post("/api/cameras")
async def create_camera(request: Dict[str, Any], db: Session = Depends(get_session)) -> JSONResponse:
    try:
        try:
            rtsp_updates = _sanitize_rtsp_updates(request)
        except ValueError as e:
            raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": str(e)})

        camera = camera_crud_service.create_camera(
            db=db,
            name=request.get("name"),
            camera_type=request.get("type"),
            rtsp_url_thermal=rtsp_updates.get("rtsp_url_thermal"),
            rtsp_url_color=rtsp_updates.get("rtsp_url_color"),
            rtsp_url_detection=rtsp_updates.get("rtsp_url_detection"),
            channel_color=request.get("channel_color"),
            channel_thermal=request.get("channel_thermal"),
            detection_source=request.get("detection_source", "auto"),
            stream_roles=request.get("stream_roles", ["detect", "live"]),
            enabled=request.get("enabled", True),
            zones=request.get("zones", []),
            motion_config=request.get("motion_config"),
        )
        go2rtc_service.update_camera_streams(
            camera_id=camera.id,
            rtsp_url=camera.rtsp_url,
            rtsp_url_color=camera.rtsp_url_color,
            rtsp_url_thermal=camera.rtsp_url_thermal,
            rtsp_url_detection=camera.rtsp_url_detection,
            default_url=resolve_default_rtsp_url(camera),
        )
        roles = camera.stream_roles if isinstance(camera.stream_roles, list) else []
        if camera.enabled and (not roles or "detect" in roles):
            try:
                detector_worker.start_camera_detection(camera)
            except Exception as e:
                logger.error("Failed to start detection for camera %s: %s", camera.id, e)
        else:
            detector_worker.stop_camera_detection(camera.id)
        if camera.enabled:
            try:
                rtsp_url = get_recording_rtsp_url(camera)
                if rtsp_url:
                    continuous_recorder.start_recording(camera.id, rtsp_url)
            except Exception as e:
                logger.error("Failed to start continuous recording for camera %s: %s", camera.id, e)
        else:
            continuous_recorder.stop_recording(camera.id)
        mqtt_service.publish_camera_update(camera.id)
        return JSONResponse(content=camera_crud_service.mask_rtsp_urls(camera), status_code=201)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": str(e)})
    except Exception as e:
        logger.error(f"Failed to create camera: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to create camera: {str(e)}"})


@router.put("/api/cameras/{camera_id}")
async def update_camera(camera_id: str, request: Dict[str, Any], db: Session = Depends(get_session)) -> Dict[str, Any]:
    try:
        try:
            request.update(_sanitize_rtsp_updates(request))
        except ValueError as e:
            raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": str(e)})
        camera = camera_crud_service.update_camera(db, camera_id, request)
        if not camera:
            raise HTTPException(status_code=404, detail={"error": True, "code": "CAMERA_NOT_FOUND", "message": f"Camera with id {camera_id} not found"})
        detector_worker.stop_camera_detection(camera.id)
        go2rtc_service.update_camera_streams(
            camera_id=camera.id,
            rtsp_url=camera.rtsp_url,
            rtsp_url_color=camera.rtsp_url_color,
            rtsp_url_thermal=camera.rtsp_url_thermal,
            rtsp_url_detection=camera.rtsp_url_detection,
            default_url=resolve_default_rtsp_url(camera),
        )
        roles = camera.stream_roles if isinstance(camera.stream_roles, list) else []
        if camera.enabled and (not roles or "detect" in roles):
            try:
                detector_worker.start_camera_detection(camera)
            except Exception as e:
                logger.error("Failed to start detection for camera %s: %s", camera.id, e)
        if camera.enabled:
            try:
                rtsp_url = get_recording_rtsp_url(camera)
                if rtsp_url:
                    continuous_recorder.start_recording(camera.id, rtsp_url)
            except Exception as e:
                logger.error("Failed to start continuous recording for camera %s: %s", camera.id, e)
        else:
            continuous_recorder.stop_recording(camera.id)
        mqtt_service.publish_camera_update(camera.id)
        return camera_crud_service.mask_rtsp_urls(camera)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": str(e)})
    except Exception as e:
        logger.error(f"Failed to update camera {camera_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to update camera: {str(e)}"})


@router.delete("/api/cameras/{camera_id}")
async def delete_camera(camera_id: str, db: Session = Depends(get_session)) -> Response:
    try:
        go2rtc_service.remove_camera(camera_id)
        continuous_recorder.stop_recording(camera_id)
        recording_state_service.clear_state(db, camera_id)
        detector_worker.stop_camera_detection(camera_id)
        deleted = camera_crud_service.delete_camera(db, camera_id)
        if not deleted:
            raise HTTPException(status_code=404, detail={"error": True, "code": "CAMERA_NOT_FOUND", "message": f"Camera with id {camera_id} not found"})
        mqtt_service.clear_camera_discovery(camera_id)
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete camera {camera_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to delete camera: {str(e)}"})


@router.get("/api/cameras/{camera_id}/record")
async def get_recording_status(camera_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail={"error": True, "code": "CAMERA_NOT_FOUND", "message": f"Camera not found: {camera_id}"})
    return {"camera_id": camera_id, "recording": continuous_recorder.is_recording(camera_id)}


@router.post("/api/cameras/{camera_id}/record/start")
async def start_recording(camera_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail={"error": True, "code": "CAMERA_NOT_FOUND", "message": f"Camera not found: {camera_id}"})
    rtsp_url = get_recording_rtsp_url(camera)
    if not rtsp_url:
        raise HTTPException(status_code=400, detail={"error": True, "code": "NO_RTSP_URL", "message": "Camera has no RTSP URL configured"})
    ok = continuous_recorder.start_recording(camera_id, rtsp_url)
    recording_state_service.set_state(db, camera_id, ok)
    return {"camera_id": camera_id, "recording": ok}


@router.post("/api/cameras/{camera_id}/record/stop")
async def stop_recording(camera_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail={"error": True, "code": "CAMERA_NOT_FOUND", "message": f"Camera not found: {camera_id}"})
    continuous_recorder.stop_recording(camera_id)
    recording_state_service.set_state(db, camera_id, False)
    return {"camera_id": camera_id, "recording": False}


@router.get("/api/cameras/{camera_id}/snapshot")
async def get_camera_snapshot(camera_id: str, db: Session = Depends(get_session)) -> Response:
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail={"error": True, "code": "CAMERA_NOT_FOUND", "message": f"Camera not found: {camera_id}"})
    stream_urls = get_live_rtsp_urls(camera)
    if not stream_urls:
        raise HTTPException(status_code=400, detail={"error": True, "code": "STREAM_URL_MISSING", "message": "No RTSP URL configured for snapshot."})
    settings = settings_service.load_config()
    if settings.stream.protocol == "tcp":
        stream_urls = [camera_service.force_tcp_protocol(url) for url in stream_urls]
    result = None
    for candidate_url in stream_urls:
        result = camera_service.test_rtsp_connection(candidate_url)
        if result["success"]:
            break
    if not result or not result.get("success"):
        raise HTTPException(status_code=502, detail={"error": True, "code": "RTSP_CONNECTION_FAILED", "message": (result or {}).get("error_reason", "Snapshot capture failed")})
    snapshot_data = result["snapshot_base64"].split(",", 1)[1]
    image_bytes = base64.b64decode(snapshot_data)
    return Response(content=image_bytes, media_type="image/jpeg")


@router.get("/api/cameras/{camera_id}/zones")
async def get_camera_zones(camera_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail={"error": True, "code": "CAMERA_NOT_FOUND", "message": f"Camera not found: {camera_id}"})
    zones = db.query(Zone).filter(Zone.camera_id == camera_id).all()
    return {"zones": [{"id": z.id, "name": z.name, "enabled": z.enabled, "mode": z.mode.value, "polygon": z.polygon, "created_at": z.created_at.isoformat() + "Z", "updated_at": z.updated_at.isoformat() + "Z"} for z in zones]}


@router.post("/api/cameras/{camera_id}/zones")
async def create_zone(camera_id: str, request: Dict[str, Any], db: Session = Depends(get_session)) -> Dict[str, Any]:
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail={"error": True, "code": "CAMERA_NOT_FOUND", "message": f"Camera not found: {camera_id}"})
    name = request.get("name", "").strip()
    mode = request.get("mode", "person")
    polygon = request.get("polygon", [])
    if not name:
        raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": "Zone name is required"})
    if not isinstance(polygon, list) or len(polygon) < 3 or len(polygon) > 20:
        raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": "Polygon must have 3-20 points"})
    for point in polygon:
        if not isinstance(point, list) or len(point) != 2 or not all(isinstance(v, (int, float)) for v in point) or not (0.0 <= point[0] <= 1.0) or not (0.0 <= point[1] <= 1.0):
            raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": "Polygon points must be [x,y] normalized (0-1)"})
    zone = Zone(camera_id=camera_id, name=name, enabled=bool(request.get("enabled", True)), mode=ZoneMode(mode), polygon=polygon)
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return {"id": zone.id, "name": zone.name, "enabled": zone.enabled, "mode": zone.mode.value, "polygon": zone.polygon, "created_at": zone.created_at.isoformat() + "Z", "updated_at": zone.updated_at.isoformat() + "Z"}


@router.put("/api/zones/{zone_id}")
async def update_zone(zone_id: str, request: Dict[str, Any], db: Session = Depends(get_session)) -> Dict[str, Any]:
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail={"error": True, "code": "ZONE_NOT_FOUND", "message": f"Zone not found: {zone_id}"})
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
    return {"id": zone.id, "name": zone.name, "enabled": zone.enabled, "mode": zone.mode.value, "polygon": zone.polygon, "created_at": zone.created_at.isoformat() + "Z", "updated_at": zone.updated_at.isoformat() + "Z"}


@router.delete("/api/zones/{zone_id}")
async def delete_zone(zone_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail={"error": True, "code": "ZONE_NOT_FOUND", "message": f"Zone not found: {zone_id}"})
    db.delete(zone)
    db.commit()
    return {"deleted": True, "zone_id": zone_id}
