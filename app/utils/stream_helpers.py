"""
Shared stream URL helpers used by multiple routers.
"""
from typing import List, Optional

from app.dependencies import go2rtc_service


def resolve_default_stream_source(camera) -> Optional[str]:
    if camera.type.value == "thermal" and camera.rtsp_url_thermal:
        return "thermal"
    if camera.type.value == "color" and camera.rtsp_url_color:
        return "color"
    if camera.rtsp_url_color:
        return "color"
    if camera.rtsp_url_thermal:
        return "thermal"
    return None


def resolve_default_rtsp_url(camera) -> Optional[str]:
    if camera.type.value == "thermal":
        return camera.rtsp_url_thermal or camera.rtsp_url
    if camera.type.value == "color":
        return camera.rtsp_url_color or camera.rtsp_url
    return camera.rtsp_url_color or camera.rtsp_url_thermal or camera.rtsp_url


def get_recording_rtsp_url(camera) -> str:
    """Return go2rtc restream URL for recording, or empty string if unavailable."""
    restream = go2rtc_service.get_restream_url(camera.id, source=resolve_default_stream_source(camera))
    return restream or ""


def get_live_rtsp_urls(camera) -> List[str]:
    """Return list of RTSP URLs for live streaming (go2rtc restream only)."""
    restream = go2rtc_service.get_restream_url(camera.id, source=resolve_default_stream_source(camera))
    return [restream] if restream else []
