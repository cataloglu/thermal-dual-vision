"""
go2rtc integration service.
Manages camera streams in go2rtc configuration.
"""
import os
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import httpx

logger = logging.getLogger(__name__)


class Go2RTCService:
    """Service for go2rtc integration."""
    
    def __init__(self):
        self.config_path = Path("go2rtc.yaml")
        # Environment variable kullan (Docker için)
        # Use 127.0.0.1 instead of localhost for HA addon compatibility
        self.api_url = os.getenv("GO2RTC_URL", "http://127.0.0.1:1984")
        self._last_check_ts = 0.0
        self._check_interval = float(os.getenv("GO2RTC_CHECK_INTERVAL", "10"))
        self.enabled = self._check_availability()
        logger.info(f"go2rtc service initialized - URL: {self.api_url}, enabled: {self.enabled}")

    def refresh_enabled(self, force: bool = False) -> bool:
        """Refresh go2rtc availability (cached for a short interval)."""
        now = time.time()
        if not force and (now - self._last_check_ts) < self._check_interval:
            return self.enabled
        self._last_check_ts = now
        self.enabled = self._check_availability()
        return self.enabled

    def ensure_enabled(self) -> bool:
        """Force a refresh only when currently disabled."""
        if self.enabled:
            return True
        return self.refresh_enabled(force=True)
    
    def _check_availability(self) -> bool:
        """Check if go2rtc is available."""
        try:
            response = httpx.get(f"{self.api_url}/api", timeout=2.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"go2rtc not available: {e}")
            return False

    def _restart_go2rtc(self) -> None:
        """Restart go2rtc to reload configuration."""
        try:
            response = httpx.post(f"{self.api_url}/api/restart", timeout=5.0)
            if response.status_code == 200:
                logger.info("go2rtc restarted to reload config")
            else:
                logger.warning(f"go2rtc restart returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to restart go2rtc: {e}")

    def _load_config(self) -> Dict:
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config or {}
        return {}

    def _write_config(self, config: Dict) -> None:
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

    def _resolve_default_stream_url(
        self,
        rtsp_url: Optional[str],
        rtsp_url_color: Optional[str],
        rtsp_url_thermal: Optional[str],
        default_url: Optional[str],
    ) -> Optional[str]:
        if default_url:
            return default_url
        if rtsp_url:
            return rtsp_url
        return rtsp_url_color or rtsp_url_thermal

    def _build_camera_streams(
        self,
        camera_id: str,
        rtsp_url: Optional[str],
        rtsp_url_color: Optional[str],
        rtsp_url_thermal: Optional[str],
        rtsp_url_detection: Optional[str] = None,
        default_url: Optional[str] = None,
    ) -> Dict[str, str]:
        streams: Dict[str, str] = {}
        default_stream_url = self._resolve_default_stream_url(
            rtsp_url,
            rtsp_url_color,
            rtsp_url_thermal,
            default_url,
        )
        if default_stream_url:
            streams[camera_id] = default_stream_url
        if rtsp_url_color:
            streams[f"{camera_id}_color"] = rtsp_url_color
        if rtsp_url_thermal:
            streams[f"{camera_id}_thermal"] = rtsp_url_thermal
        # Substream for detection (low CPU - 10 cameras @ ~5%)
        if rtsp_url_detection:
            streams[f"{camera_id}_detect"] = rtsp_url_detection
        return streams

    def _resolve_default_url_from_camera(self, camera: Any) -> Optional[str]:
        camera_type = getattr(camera, "type", None)
        type_value = getattr(camera_type, "value", camera_type)
        if type_value == "thermal":
            return getattr(camera, "rtsp_url_thermal", None) or getattr(camera, "rtsp_url", None)
        if type_value == "color":
            return getattr(camera, "rtsp_url_color", None) or getattr(camera, "rtsp_url", None)
        return (
            getattr(camera, "rtsp_url_color", None)
            or getattr(camera, "rtsp_url_thermal", None)
            or getattr(camera, "rtsp_url", None)
        )

    def update_camera_streams(
        self,
        camera_id: str,
        rtsp_url: Optional[str] = None,
        rtsp_url_color: Optional[str] = None,
        rtsp_url_thermal: Optional[str] = None,
        rtsp_url_detection: Optional[str] = None,
        reload: bool = True,
        default_url: Optional[str] = None,
    ) -> bool:
        """Upsert camera streams in go2rtc config."""
        can_restart = self.refresh_enabled()
        try:
            config = self._load_config()
            streams = config.get("streams") or {}
            if not isinstance(streams, dict):
                streams = {}

            desired = self._build_camera_streams(
                camera_id,
                rtsp_url,
                rtsp_url_color,
                rtsp_url_thermal,
                rtsp_url_detection=rtsp_url_detection,
                default_url=default_url,
            )
            managed_keys = {camera_id, f"{camera_id}_color", f"{camera_id}_thermal", f"{camera_id}_detect"}
            changed = False

            for key in list(streams.keys()):
                if key in managed_keys and key not in desired:
                    del streams[key]
                    changed = True

            for key, url in desired.items():
                desired_entry = [url]
                current = streams.get(key)
                if isinstance(current, str):
                    current_entry = [current]
                else:
                    current_entry = current
                if current_entry != desired_entry:
                    streams[key] = desired_entry
                    changed = True

            if changed:
                config["streams"] = streams
                self._write_config(config)
                logger.info("go2rtc config updated for camera %s", camera_id)
                if reload and can_restart:
                    self._restart_go2rtc()
            else:
                logger.debug("go2rtc config already up to date for camera %s", camera_id)

            return changed

        except Exception as e:
            logger.error(f"Failed to update camera in go2rtc: {e}", exc_info=True)
            return False

    def add_camera(self, camera_id: str, rtsp_url: str, reload: bool = True) -> bool:
        """Add or update camera default stream in go2rtc."""
        return self.update_camera_streams(
            camera_id=camera_id,
            rtsp_url=rtsp_url,
            reload=reload,
        )

    def remove_camera(self, camera_id: str) -> bool:
        """Remove camera from go2rtc streams."""
        try:
            if not self.config_path.exists():
                return True

            self.update_camera_streams(camera_id=camera_id, reload=True)
            logger.info(f"Camera {camera_id} removed from go2rtc successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to remove camera from go2rtc: {e}", exc_info=True)
            return False
            
    def sync_all_cameras(self, cameras: list) -> None:
        """Sync all cameras to go2rtc."""
        can_restart = self.refresh_enabled()
        logger.info(f"Syncing {len(cameras)} cameras to go2rtc...")
        
        success_count = 0
        config_changed = False
        for camera in cameras:
            try:
                default_url = self._resolve_default_url_from_camera(camera)
                changed = self.update_camera_streams(
                    camera_id=camera.id,
                    rtsp_url=camera.rtsp_url,
                    rtsp_url_color=camera.rtsp_url_color,
                    rtsp_url_thermal=camera.rtsp_url_thermal,
                    rtsp_url_detection=getattr(camera, "rtsp_url_detection", None),
                    reload=False,
                    default_url=default_url,
                )
                if changed:
                    success_count += 1
                    config_changed = True
            except Exception as e:
                logger.error(f"Failed to sync camera {camera.id}: {e}", exc_info=True)
        
        logger.info(f"Camera sync complete: {success_count}/{len(cameras)} cameras synced")
        if config_changed and can_restart:
            self._restart_go2rtc()


# Singleton instance
_go2rtc_service: Optional[Go2RTCService] = None


def get_go2rtc_service() -> Go2RTCService:
    """Get or create go2rtc service instance."""
    global _go2rtc_service
    if _go2rtc_service is None:
        _go2rtc_service = Go2RTCService()
    return _go2rtc_service
