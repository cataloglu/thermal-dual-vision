import asyncio
import base64
import logging
import time
from typing import Any, Dict, List, Optional

import cv2
import httpx
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.dependencies import (
    camera_crud_service,
    camera_service,
    detector_worker,
    go2rtc_service,
    live_stream_semaphore,
    settings_service,
)
from app.utils.stream_helpers import get_live_rtsp_urls, resolve_default_stream_source, resolve_default_rtsp_url

logger = logging.getLogger(__name__)
router = APIRouter()


def _resolve_go2rtc_stream_name(camera) -> Optional[str]:
    source = resolve_default_stream_source(camera)
    if source in ("thermal", "color"):
        return f"{camera.id}_{source}"
    if resolve_default_rtsp_url(camera):
        return camera.id
    if getattr(camera, "rtsp_url_detection", None):
        return f"{camera.id}_detect"
    return camera.id


def _get_latest_worker_frame(camera_id: str) -> Optional[np.ndarray]:
    try:
        if hasattr(detector_worker, "get_latest_frame"):
            return detector_worker.get_latest_frame(camera_id)
    except Exception as e:
        logger.debug("Live frame fetch failed for %s: %s", camera_id, e)
    return None


def _iter_mjpeg_from_worker(camera_id: str, fps: float, quality: int):
    boundary = b"--frame\r\n"
    delay = 1.0 / max(fps, 1.0)
    while True:
        frame = _get_latest_worker_frame(camera_id)
        if frame is None:
            time.sleep(0.2)
            continue
        ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ok:
            time.sleep(0.2)
            continue
        jpg = buffer.tobytes()
        yield (
            boundary
            + b"Content-Type: image/jpeg\r\n"
            + f"Content-Length: {len(jpg)}\r\n\r\n".encode("ascii")
            + jpg
            + b"\r\n"
        )
        if delay > 0:
            time.sleep(delay)


@router.get("/api/live")
async def get_live_streams(request: Request, db: Session = Depends(get_session)) -> Dict[str, Any]:
    try:
        cameras = camera_crud_service.get_cameras(db)
        ingress_path = request.headers.get("X-Ingress-Path", "")
        prefix = ingress_path.rstrip("/") if ingress_path else ""
        streams = []
        for camera in cameras:
            if not camera.enabled or "live" not in (camera.stream_roles or []):
                continue
            base_url = f"/api/live/{camera.id}.mjpeg"
            stream_url = f"{prefix}{base_url}" if prefix else base_url
            streams.append({"camera_id": camera.id, "name": camera.name, "stream_url": stream_url})
        return {"streams": streams}
    except Exception as e:
        logger.error(f"Failed to get live streams: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to retrieve live streams: {str(e)}"})


@router.get("/api/live/{camera_id}.mjpeg")
async def get_live_stream(
    camera_id: str,
    db: Session = Depends(get_session),
    probe: bool = Query(False),
) -> Response:
    """Stream live MJPEG from go2rtc with fallbacks."""
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail={"error": True, "code": "CAMERA_NOT_FOUND", "message": f"Camera not found: {camera_id}"})

    config = settings_service.load_config()
    go2rtc_mjpeg = None
    media_type = "multipart/x-mixed-replace; boundary=frame"
    use_go2rtc_mjpeg = False
    stream_name = None
    go2rtc_error = None
    go2rtc_ready = bool(go2rtc_service and go2rtc_service.ensure_enabled())

    if go2rtc_ready:
        stream_name = _resolve_go2rtc_stream_name(camera)
        if stream_name:
            go2rtc_mjpeg = f"{go2rtc_service.api_url}/api/stream.mjpeg?src={stream_name}"
            try:
                probe_timeout = 3.0
                timeout = httpx.Timeout(5.0, read=probe_timeout)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream("GET", go2rtc_mjpeg) as check_resp:
                        if check_resp.status_code == 200:
                            media_type = check_resp.headers.get("content-type", media_type)
                            aiter = check_resp.aiter_bytes()
                            try:
                                first_chunk = await asyncio.wait_for(aiter.__anext__(), timeout=probe_timeout)
                                if first_chunk:
                                    use_go2rtc_mjpeg = True
                                else:
                                    go2rtc_error = "empty"
                            except asyncio.TimeoutError:
                                go2rtc_error = "timeout"
                            except StopAsyncIteration:
                                go2rtc_error = "ended"
                        else:
                            go2rtc_error = f"status_{check_resp.status_code}"
            except Exception as e:
                go2rtc_error = "error"
                logger.debug("go2rtc live check for %s failed: %s", camera_id, e)
        else:
            go2rtc_error = "stream_missing"
    else:
        go2rtc_error = "disabled" if go2rtc_service else "not_configured"

    worker_supported = hasattr(detector_worker, "get_latest_frame")

    if probe:
        rtsp_urls = get_live_rtsp_urls(camera)
        worker_frame = _get_latest_worker_frame(camera_id)
        if use_go2rtc_mjpeg:
            source = "go2rtc"
        elif worker_supported:
            source = "worker"
        elif rtsp_urls:
            source = "rtsp"
        else:
            source = None
        return JSONResponse({
            "ok": source is not None, "source": source,
            "go2rtc_ok": use_go2rtc_mjpeg, "go2rtc_error": go2rtc_error,
            "rtsp_available": bool(rtsp_urls), "worker_frame": worker_frame is not None,
            "stream_name": stream_name,
        })

    def _acquire():
        return live_stream_semaphore.acquire(blocking=True, timeout=3)

    acquired = await asyncio.get_event_loop().run_in_executor(None, _acquire)
    if not acquired:
        raise HTTPException(status_code=503, detail={"error": True, "code": "TOO_MANY_LIVE_STREAMS", "message": "Another live stream is open. Close it and try again."})

    def _proxy_rtsp_mjpeg(rtsp_url: str, quality: int):
        try:
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
            if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
            while True:
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
                if not ok:
                    continue
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        finally:
            try:
                cap.release()
            except Exception:
                pass
            live_stream_semaphore.release()

    stream_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "X-Accel-Buffering": "no",
        "Content-Encoding": "identity",
    }

    if use_go2rtc_mjpeg and go2rtc_mjpeg:
        async def proxy_go2rtc():
            try:
                async with httpx.AsyncClient(timeout=60.0) as c2:
                    async with c2.stream("GET", go2rtc_mjpeg) as r:
                        async for chunk in r.aiter_bytes():
                            yield chunk
            finally:
                live_stream_semaphore.release()

        logger.info("Live stream from go2rtc for %s", camera_id)
        return StreamingResponse(proxy_go2rtc(), media_type=media_type, headers=stream_headers)

    if worker_supported:
        mjpeg_quality = int(getattr(config.live, "mjpeg_quality", 92))
        fallback_fps = float(getattr(config.detection, "inference_fps", 2))
        fallback_fps = max(1.0, min(fallback_fps, 10.0))

        def fallback_stream():
            try:
                yield from _iter_mjpeg_from_worker(camera_id, fallback_fps, mjpeg_quality)
            finally:
                live_stream_semaphore.release()

        logger.warning("Live stream fallback for %s (worker frames)", camera_id)
        return StreamingResponse(fallback_stream(), media_type="multipart/x-mixed-replace; boundary=frame", headers=stream_headers)

    stream_urls = get_live_rtsp_urls(camera)
    if stream_urls:
        quality = int(getattr(getattr(config, "live", None), "mjpeg_quality", 92))
        logger.info("Live stream fallback via RTSP for %s", camera_id)
        return StreamingResponse(_proxy_rtsp_mjpeg(stream_urls[0], quality), media_type="multipart/x-mixed-replace; boundary=frame", headers=stream_headers)

    live_stream_semaphore.release()
    raise HTTPException(status_code=503, detail={"error": True, "code": "LIVE_FRAME_UNAVAILABLE", "message": "Live frame not available. Check go2rtc and detection stream."})


@router.get("/api/live/{camera_id}.jpg")
async def get_live_snapshot(camera_id: str, db: Session = Depends(get_session)) -> Response:
    """Return a single JPEG frame for live view."""
    camera = camera_crud_service.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail={"error": True, "code": "CAMERA_NOT_FOUND", "message": f"Camera not found: {camera_id}"})

    config = settings_service.load_config()
    quality = int(getattr(getattr(config, "live", None), "mjpeg_quality", 92))
    headers = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}

    frame = _get_latest_worker_frame(camera_id)
    if frame is not None:
        ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if ok:
            return Response(content=buffer.tobytes(), media_type="image/jpeg", headers=headers)

    stream_urls = get_live_rtsp_urls(camera)
    if stream_urls:
        settings = settings_service.load_config()
        if settings.stream.protocol == "tcp":
            stream_urls = [camera_service.force_tcp_protocol(url) for url in stream_urls]
        result = None
        for candidate_url in stream_urls:
            result = camera_service.test_rtsp_connection(candidate_url)
            if result["success"]:
                break
        if result and result.get("success"):
            snapshot_data = result["snapshot_base64"].split(",", 1)[1]
            image_bytes = base64.b64decode(snapshot_data)
            return Response(content=image_bytes, media_type="image/jpeg", headers=headers)

    raise HTTPException(status_code=503, detail={"error": True, "code": "LIVE_SNAPSHOT_UNAVAILABLE", "message": "Live snapshot not available. Check go2rtc and detection stream."})
