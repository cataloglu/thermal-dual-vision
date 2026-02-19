"""
Shared service singletons for dependency injection across routers.

All module-level singleton instances are initialized here so that
both main.py and router files can import from a single source without
circular imports.
"""
import threading

from app.db.session import init_db
from app.services.camera import get_camera_service
from app.services.camera_crud import get_camera_crud_service
from app.services.events import get_event_service
from app.services.media import get_media_service
from app.services.settings import get_settings_service
from app.services.websocket import get_websocket_manager
from app.services.telegram import get_telegram_service
from app.services.logs import get_logs_service
from app.services.ai import get_ai_service
from app.services.go2rtc import get_go2rtc_service
from app.services.mqtt import get_mqtt_service
from app.services.recording_state import get_recording_state_service
from app.services.metrics import get_metrics_service
from app.services.recorder import get_continuous_recorder
from app.workers.retention import get_retention_worker
from app.workers.detector import get_detector_worker

init_db()

settings_service = get_settings_service()
camera_service = get_camera_service()
camera_crud_service = get_camera_crud_service()
event_service = get_event_service()
ai_service = get_ai_service()
media_service = get_media_service()
retention_worker = get_retention_worker()

# Default: threading mode. Overridden in lifespan based on performance.worker_mode
detector_worker = get_detector_worker()

websocket_manager = get_websocket_manager()
telegram_service = get_telegram_service()
logs_service = get_logs_service()
go2rtc_service = get_go2rtc_service()
mqtt_service = get_mqtt_service()
recording_state_service = get_recording_state_service()
metrics_service = get_metrics_service()
continuous_recorder = get_continuous_recorder()

# Max 2 concurrent live MJPEG streams (each stream = full RTSP decode + encode)
live_stream_semaphore = threading.Semaphore(2)
