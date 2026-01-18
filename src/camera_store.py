"""Camera persistence and status helpers."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import cv2

from src.config_store import ConfigStore, merge_config
from src.logger import get_logger
from src.utils import encode_frame_to_base64

logger = get_logger("camera_store")

_status_cache: Dict[str, Dict[str, Any]] = {}


class CameraStore:
    """CRUD operations for cameras stored in config.json."""

    def __init__(self, store: Optional[ConfigStore] = None) -> None:
        self.store = store or ConfigStore()

    def list_cameras(self) -> List[Dict[str, Any]]:
        payload = self.store.load()
        cameras = payload.get("cameras", [])
        return [self._attach_status(self._redact_camera(camera)) for camera in cameras]

    def get_camera(self, camera_id: str) -> Optional[Dict[str, Any]]:
        payload = self.store.load()
        for camera in payload.get("cameras", []):
            if camera.get("id") == camera_id:
                return self._attach_status(self._redact_camera(camera))
        return None

    def get_camera_raw(self, camera_id: str) -> Optional[Dict[str, Any]]:
        payload = self.store.load()
        for camera in payload.get("cameras", []):
            if camera.get("id") == camera_id:
                return camera
        return None

    def create_camera(self, data: Dict[str, Any]) -> Dict[str, Any]:
        errors = _validate_camera_payload(data)
        if errors:
            raise ValueError("; ".join(errors))

        payload = self.store.load()
        cameras = payload.get("cameras", [])
        camera = _normalize_camera(data)
        camera["id"] = camera.get("id") or str(uuid4())
        cameras.append(camera)
        payload["cameras"] = cameras
        self.store.save(payload)
        return self._attach_status(self._redact_camera(camera))

    def update_camera(self, camera_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.store.load()
        cameras = payload.get("cameras", [])
        for idx, camera in enumerate(cameras):
            if camera.get("id") == camera_id:
                merged = merge_config(camera, _normalize_camera(data, partial=True))
                merged["id"] = camera_id
                errors = _validate_camera_payload(merged)
                if errors:
                    raise ValueError("; ".join(errors))
                cameras[idx] = merged
                payload["cameras"] = cameras
                self.store.save(payload)
                return self._attach_status(self._redact_camera(merged))
        raise KeyError(camera_id)

    def delete_camera(self, camera_id: str) -> None:
        payload = self.store.load()
        cameras = payload.get("cameras", [])
        payload["cameras"] = [camera for camera in cameras if camera.get("id") != camera_id]
        self.store.save(payload)
        _status_cache.pop(camera_id, None)

    def test_camera(self, camera_id: str) -> Dict[str, Any]:
        payload = self.store.load()
        camera = next((item for item in payload.get("cameras", []) if item.get("id") == camera_id), None)
        if not camera:
            raise KeyError(camera_id)

        return _test_camera_url(
            _primary_camera_url(camera),
            camera_id=camera_id,
            update_status=self._update_status,
        )

    def snapshot_camera(self, camera_id: str) -> Dict[str, Any]:
        payload = self.store.load()
        camera = next((item for item in payload.get("cameras", []) if item.get("id") == camera_id), None)
        if not camera:
            raise KeyError(camera_id)
        return _test_camera_url(_primary_camera_url(camera))

    def test_camera_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        camera = _normalize_camera(data, partial=True)
        return _test_camera_url(_primary_camera_url(camera))

    def _update_status(self, camera_id: str, status: str, last_error: Optional[str]) -> None:
        _status_cache[camera_id] = {
            "status": status,
            "last_error": last_error,
            "last_frame_ts": time.time() if status == "connected" else _status_cache.get(camera_id, {}).get("last_frame_ts"),
        }

    def _attach_status(self, camera: Dict[str, Any]) -> Dict[str, Any]:
        status = _status_cache.get(camera.get("id"), {})
        camera["status"] = status.get("status", "disconnected")
        camera["last_error"] = status.get("last_error")
        camera["last_frame_ts"] = status.get("last_frame_ts")
        return camera

    def _redact_camera(self, camera: Dict[str, Any]) -> Dict[str, Any]:
        redacted = dict(camera)
        redacted["rtsp_url_color"] = _redact_url(camera.get("rtsp_url_color", ""))
        redacted["rtsp_url_thermal"] = _redact_url(camera.get("rtsp_url_thermal", ""))
        return redacted


def _normalize_camera(data: Dict[str, Any], partial: bool = False) -> Dict[str, Any]:
    camera = {
        "id": data.get("id"),
        "name": data.get("name"),
        "type": data.get("type", "color"),
        "rtsp_url_color": data.get("rtsp_url_color", ""),
        "rtsp_url_thermal": data.get("rtsp_url_thermal", ""),
        "channel_color": data.get("channel_color", 102),
        "channel_thermal": data.get("channel_thermal", 202),
    }
    if partial:
        return {key: value for key, value in camera.items() if value is not None}
    return camera


def _primary_camera_url(camera: Dict[str, Any]) -> str:
    if camera.get("type") == "dual":
        return camera.get("rtsp_url_color") or camera.get("rtsp_url_thermal") or ""
    if camera.get("type") == "thermal":
        return camera.get("rtsp_url_thermal") or camera.get("rtsp_url_color") or ""
    return camera.get("rtsp_url_color") or camera.get("rtsp_url_thermal") or ""


def _validate_camera_payload(camera: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not camera.get("name"):
        errors.append("Camera name is required")
    camera_type = camera.get("type")
    if camera_type not in {"color", "thermal", "dual"}:
        errors.append("Camera type must be color, thermal, or dual")

    if camera_type == "dual":
        if not camera.get("rtsp_url_color") or not camera.get("rtsp_url_thermal"):
            errors.append("Both color and thermal RTSP URLs are required for dual cameras")
    elif camera_type == "thermal":
        if not camera.get("rtsp_url_thermal"):
            errors.append("Thermal RTSP URL is required")
    else:
        if not camera.get("rtsp_url_color"):
            errors.append("Color RTSP URL is required")
    return errors


def _redact_url(url: str) -> str:
    if not url:
        return url
    parsed = urlsplit(url)
    if "@" not in parsed.netloc:
        return url
    userinfo, host = parsed.netloc.split("@", 1)
    if ":" in userinfo:
        user, _password = userinfo.split(":", 1)
        userinfo = f"{user}:***"
    else:
        userinfo = f"{userinfo}:***"
    return urlunsplit((parsed.scheme, f"{userinfo}@{host}", parsed.path, parsed.query, parsed.fragment))


def _test_camera_url(
    url: str,
    camera_id: Optional[str] = None,
    update_status=None,
) -> Dict[str, Any]:
    if not url:
        if update_status and camera_id:
            update_status(camera_id, "disconnected", "Missing RTSP URL")
        return {"ok": False, "error": "Missing RTSP URL"}

    capture = cv2.VideoCapture(url)
    try:
        if not capture.isOpened():
            if update_status and camera_id:
                update_status(camera_id, "disconnected", "Unable to open stream")
            return {"ok": False, "error": "Unable to open stream"}
        ok, frame = capture.read()
        if not ok:
            if update_status and camera_id:
                update_status(camera_id, "disconnected", "Unable to read frame")
            return {"ok": False, "error": "Unable to read frame"}
        snapshot = encode_frame_to_base64(frame)
        if update_status and camera_id:
            update_status(camera_id, "connected", None)
        return {"ok": True, "snapshot": snapshot}
    finally:
        capture.release()
