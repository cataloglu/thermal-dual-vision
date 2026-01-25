"""
go2rtc integration service.
Manages camera streams in go2rtc configuration.
"""
import os
import logging
from pathlib import Path
from typing import Optional
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
        self.enabled = self._check_availability()
        logger.info(f"go2rtc service initialized - URL: {self.api_url}, enabled: {self.enabled}")
    
    def _check_availability(self) -> bool:
        """Check if go2rtc is available."""
        try:
            response = httpx.get(f"{self.api_url}/api", timeout=2.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"go2rtc not available: {e}")
            return False
    
    def add_camera(self, camera_id: str, rtsp_url: str) -> bool:
        """Add camera to go2rtc streams."""
        if not self.enabled:
            logger.debug("go2rtc not enabled, skipping camera add")
            return False
            
        try:
            # Load existing config
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if config is None:
                        config = {}
            else:
                config = {}
            
            # Ensure streams exists and is not None
            if 'streams' not in config or config['streams'] is None:
                config['streams'] = {}
            
            # Use rtsp url directly
            config['streams'][camera_id] = [rtsp_url]
            
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            logger.info(f"Camera {camera_id} added to go2rtc successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add camera to go2rtc: {e}", exc_info=True)
            return False
            
    def sync_all_cameras(self, cameras: list) -> None:
        """Sync all cameras to go2rtc."""
        if not self.enabled:
            logger.info("go2rtc disabled, skipping camera sync")
            return
        
        logger.info(f"Syncing {len(cameras)} cameras to go2rtc...")
        
        success_count = 0
        for camera in cameras:
            try:
                rtsp_url = camera.rtsp_url_thermal or camera.rtsp_url_color or camera.rtsp_url
                if rtsp_url:
                    if self.add_camera(camera.id, rtsp_url):
                        success_count += 1
            except Exception as e:
                logger.error(f"Failed to sync camera {camera.id}: {e}", exc_info=True)
        
        logger.info(f"Camera sync complete: {success_count}/{len(cameras)} cameras synced")


# Singleton instance
_go2rtc_service: Optional[Go2RTCService] = None


def get_go2rtc_service() -> Go2RTCService:
    """Get or create go2rtc service instance."""
    global _go2rtc_service
    if _go2rtc_service is None:
        _go2rtc_service = Go2RTCService()
    return _go2rtc_service
