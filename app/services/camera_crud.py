"""
Camera CRUD service for Smart Motion Detector v2.

Handles camera database operations (Create, Read, Update, Delete).
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.db.models import Camera, CameraType, CameraStatus, DetectionSource


logger = logging.getLogger(__name__)


class CameraCRUDService:
    """
    Camera CRUD service for database operations.
    
    Handles:
    - Create camera
    - Read cameras (all or by ID)
    - Update camera
    - Delete camera
    """
    
    def __init__(self):
        """Initialize camera CRUD service."""
        logger.info("CameraCRUDService initialized")
    
    def create_camera(
        self,
        db: Session,
        name: str,
        camera_type: str,
        rtsp_url_thermal: Optional[str] = None,
        rtsp_url_color: Optional[str] = None,
        rtsp_url_detection: Optional[str] = None,
        channel_color: Optional[int] = None,
        channel_thermal: Optional[int] = None,
        detection_source: str = "auto",
        stream_roles: List[str] = None,
        enabled: bool = True,
        zones: List[Dict[str, Any]] = None,
        motion_config: Dict[str, Any] = None
    ) -> Camera:
        """
        Create a new camera.
        
        Args:
            db: Database session
            name: Camera name
            camera_type: Camera type (color/thermal/dual)
            rtsp_url_thermal: Thermal RTSP URL
            rtsp_url_color: Color RTSP URL
            channel_color: Color channel number
            channel_thermal: Thermal channel number
            detection_source: Detection source (color/thermal/auto)
            stream_roles: Stream roles (detect/live/record)
            enabled: Camera enabled status
            zones: Zone configurations
            motion_config: Motion detection config
            
        Returns:
            Created camera object
        """
        try:
            # Create camera
            camera = Camera(
                name=name,
                type=CameraType(camera_type),
                enabled=enabled,
                rtsp_url_thermal=rtsp_url_thermal,
                rtsp_url_color=rtsp_url_color,
                rtsp_url_detection=rtsp_url_detection,
                channel_color=channel_color,
                channel_thermal=channel_thermal,
                detection_source=DetectionSource(detection_source),
                stream_roles=stream_roles or ["detect", "live"],
                status=CameraStatus.INITIALIZING,
                motion_config=motion_config or {
                    "enabled": True,
                    "sensitivity": 7,
                    "threshold": 500,
                    "cooldown": 5,
                    "min_area": 500,
                    "cooldown_seconds": 5,
                    "roi": ""
                }
            )
            
            db.add(camera)
            db.commit()
            db.refresh(camera)
            
            logger.info(f"Camera created: {camera.id} ({camera.name})")
            return camera
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create camera: {e}")
            raise
    
    def get_cameras(self, db: Session) -> List[Camera]:
        """
        Get all cameras.
        
        Args:
            db: Database session
            
        Returns:
            List of camera objects
        """
        try:
            cameras = db.query(Camera).all()
            logger.debug(f"Retrieved {len(cameras)} cameras")
            return cameras
        except Exception as e:
            logger.error(f"Failed to get cameras: {e}")
            raise
    
    def get_camera(self, db: Session, camera_id: str) -> Optional[Camera]:
        """
        Get camera by ID.
        
        Args:
            db: Database session
            camera_id: Camera ID
            
        Returns:
            Camera object or None if not found
        """
        try:
            camera = db.query(Camera).filter(Camera.id == camera_id).first()
            if camera:
                logger.debug(f"Retrieved camera: {camera_id}")
            else:
                logger.warning(f"Camera not found: {camera_id}")
            return camera
        except Exception as e:
            logger.error(f"Failed to get camera {camera_id}: {e}")
            raise
    
    def update_camera(
        self,
        db: Session,
        camera_id: str,
        data: Dict[str, Any]
    ) -> Optional[Camera]:
        """
        Update camera.
        
        Args:
            db: Database session
            camera_id: Camera ID
            data: Update data (partial)
            
        Returns:
            Updated camera object or None if not found
        """
        try:
            camera = self.get_camera(db, camera_id)
            if not camera:
                return None

            allowed_fields = {
                "name",
                "type",
                "enabled",
                "rtsp_url",
                "rtsp_url_color",
                "rtsp_url_thermal",
                "rtsp_url_detection",
                "channel_color",
                "channel_thermal",
                "detection_source",
                "stream_roles",
                "motion_config",
            }
            # Update fields
            for key, value in data.items():
                if key not in allowed_fields or not hasattr(camera, key):
                    continue
                # Handle enum conversions
                if key == "type" and isinstance(value, str):
                    value = CameraType(value)
                elif key == "detection_source" and isinstance(value, str):
                    value = DetectionSource(value)
                elif key == "status" and isinstance(value, str):
                    value = CameraStatus(value)
                
                setattr(camera, key, value)
            
            db.commit()
            db.refresh(camera)
            
            logger.info(f"Camera updated: {camera_id}")
            return camera
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update camera {camera_id}: {e}")
            raise
    
    def delete_camera(self, db: Session, camera_id: str) -> bool:
        """
        Delete camera.
        
        Args:
            db: Database session
            camera_id: Camera ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            camera = self.get_camera(db, camera_id)
            if not camera:
                return False
            
            db.delete(camera)
            db.commit()
            
            logger.info(f"Camera deleted: {camera_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete camera {camera_id}: {e}")
            raise
    
    def mask_rtsp_urls(self, camera: Camera) -> Dict[str, Any]:
        """
        Convert camera to dict with RTSP URLs.
        
        Args:
            camera: Camera object
            
        Returns:
            Dict with RTSP URLs
        """
        return {
            "id": camera.id,
            "name": camera.name,
            "type": camera.type.value,
            "enabled": camera.enabled,
            "rtsp_url": camera.rtsp_url,
            "rtsp_url_color": camera.rtsp_url_color,
            "rtsp_url_thermal": camera.rtsp_url_thermal,
            "rtsp_url_detection": getattr(camera, "rtsp_url_detection", None),
            "channel_color": camera.channel_color,
            "channel_thermal": camera.channel_thermal,
            "detection_source": camera.detection_source.value,
            "stream_roles": camera.stream_roles,
            "status": camera.status.value,
            "last_frame_ts": camera.last_frame_ts.isoformat() + "Z" if camera.last_frame_ts else None,
            "motion_config": camera.motion_config,
            "zones": [
                {
                    "id": zone.id,
                    "name": zone.name,
                    "enabled": zone.enabled,
                    "mode": zone.mode.value,
                    "polygon": zone.polygon,
                }
                for zone in (camera.zones or [])
            ],
            "created_at": camera.created_at.isoformat() + "Z",
            "updated_at": camera.updated_at.isoformat() + "Z",
        }


# Global singleton instance
_camera_crud_service: Optional[CameraCRUDService] = None


def get_camera_crud_service() -> CameraCRUDService:
    """
    Get or create the global camera CRUD service instance.
    
    Returns:
        CameraCRUDService: Global camera CRUD service instance
    """
    global _camera_crud_service
    if _camera_crud_service is None:
        _camera_crud_service = CameraCRUDService()
    return _camera_crud_service
