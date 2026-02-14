"""
Recording state service for Smart Motion Detector v2.

Stores per-camera recording toggles in the database so multiple processes
share consistent state.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import RecordingState

logger = logging.getLogger(__name__)


class RecordingStateService:
    """Service for managing recording state in the database."""

    def get_state(self, db: Session, camera_id: str) -> bool:
        state = db.query(RecordingState).filter(RecordingState.camera_id == camera_id).first()
        return bool(state.recording) if state else False

    def set_state(self, db: Session, camera_id: str, recording: bool) -> None:
        state = db.query(RecordingState).filter(RecordingState.camera_id == camera_id).first()
        if state is None:
            state = RecordingState(camera_id=camera_id, recording=bool(recording))
            db.add(state)
        else:
            state.recording = bool(recording)
        db.commit()

    def clear_state(self, db: Session, camera_id: str) -> None:
        state = db.query(RecordingState).filter(RecordingState.camera_id == camera_id).first()
        if state:
            db.delete(state)
            db.commit()


_recording_state_service: Optional[RecordingStateService] = None


def get_recording_state_service() -> RecordingStateService:
    global _recording_state_service
    if _recording_state_service is None:
        _recording_state_service = RecordingStateService()
    return _recording_state_service
