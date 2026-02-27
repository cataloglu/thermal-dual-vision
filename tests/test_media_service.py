"""
Unit tests for media service background replacement behavior.
"""
from datetime import datetime, timedelta

import cv2
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Camera, CameraStatus, CameraType, DetectionSource, Event
from app.services import media as media_service


def test_delayed_replace_skips_when_media_dir_missing(tmp_path, monkeypatch):
    """Delayed recorder replace should no-op if event media directory was deleted."""
    called = {"extract": False}

    class DummyRecorder:
        def extract_clip(self, *args, **kwargs):
            called["extract"] = True
            return True

    missing_mp4 = tmp_path / "deleted_event" / "timelapse.mp4"
    monkeypatch.setattr(media_service, "get_continuous_recorder", lambda: DummyRecorder())

    start = datetime.utcnow()
    end = start + timedelta(seconds=7)
    media_service._replace_mp4_from_recording(
        "camera-1",
        start,
        end,
        str(missing_mp4),
        4.0,
    )

    assert called["extract"] is False


def test_delayed_replace_attempts_when_media_dir_exists(tmp_path, monkeypatch):
    """Delayed recorder replace should attempt extraction when media dir exists."""
    called = {"extract": False}

    class DummyRecorder:
        def extract_clip(self, *args, **kwargs):
            called["extract"] = True
            return False

    event_dir = tmp_path / "event"
    event_dir.mkdir(parents=True, exist_ok=True)
    mp4_path = event_dir / "timelapse.mp4"
    monkeypatch.setattr(media_service, "get_continuous_recorder", lambda: DummyRecorder())

    start = datetime.utcnow()
    end = start + timedelta(seconds=7)
    media_service._replace_mp4_from_recording(
        "camera-1",
        start,
        end,
        str(mp4_path),
        4.0,
    )

    assert called["extract"] is True


def _make_db_session(tmp_path):
    db_path = tmp_path / "media_service_test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    return session, engine


def _add_camera_and_event(session, event_id: str, camera_id: str = "camera-1"):
    camera = Camera(
        id=camera_id,
        name="Test Camera",
        type=CameraType.THERMAL,
        enabled=True,
        rtsp_url_thermal="rtsp://test",
        detection_source=DetectionSource.THERMAL,
        stream_roles=["detect", "live"],
        status=CameraStatus.CONNECTED,
    )
    session.add(camera)
    event = Event(
        id=event_id,
        camera_id=camera_id,
        timestamp=datetime.utcnow(),
        confidence=0.6,
    )
    session.add(event)
    session.commit()


def _patch_media_dependencies(monkeypatch, duplicate_percentage: float, extract_ok: bool, timer_calls: list):
    class DummyRecorder:
        def extract_clip(self, *args, **kwargs):
            return extract_ok

    class DummyWorker:
        def create_collage(self, *_args, **_kwargs):
            output_path = _args[3]
            with open(output_path, "wb") as f:
                f.write(b"collage")
            return output_path

        def create_timelapse_mp4(self, *_args, **_kwargs):
            output_path = _args[2]
            with open(output_path, "wb") as f:
                f.write(b"mp4")
            return output_path

        def create_timeline_gif(self, *_args, **_kwargs):
            output_path = _args[1]
            with open(output_path, "wb") as f:
                f.write(b"gif")
            return output_path

    class DummySettings:
        class _Cfg:
            class event:
                prebuffer_seconds = 5.0
                postbuffer_seconds = 2.0

            class telegram:
                video_speed = 4

            class live:
                overlay_timezone = "local"

        def load_config(self):
            return self._Cfg()

    class DummyTimer:
        def __init__(self, interval, callback, args=None, kwargs=None):
            self.interval = interval
            self.callback = callback
            self.args = args or ()
            self.kwargs = kwargs or {}
            self.daemon = False

        def start(self):
            timer_calls.append(
                {
                    "interval": self.interval,
                    "callback_name": getattr(self.callback, "__name__", "unknown"),
                    "args_count": len(self.args),
                }
            )

    monkeypatch.setattr(media_service, "get_continuous_recorder", lambda: DummyRecorder())
    monkeypatch.setattr(media_service, "get_settings_service", lambda: DummySettings())
    monkeypatch.setattr(
        media_service,
        "analyze_video",
        lambda _path: {
            "analysis": {
                "actual_duration": 6.0,
                "duplicate_percentage": duplicate_percentage,
            }
        },
    )
    monkeypatch.setattr(media_service.threading, "Timer", DummyTimer)
    return DummyWorker()


def test_generate_event_media_skips_delayed_timer_for_phantom_event(tmp_path, monkeypatch):
    session, engine = _make_db_session(tmp_path)
    try:
        event_id = "event-phantom-1"
        _add_camera_and_event(session, event_id)

        media_root = tmp_path / "media"
        monkeypatch.setattr(media_service.MediaService, "MEDIA_DIR", media_root)
        service = media_service.MediaService()

        timer_calls = []
        service.media_worker = _patch_media_dependencies(
            monkeypatch,
            duplicate_percentage=99.0,
            extract_ok=False,
            timer_calls=timer_calls,
        )

        result = service.generate_event_media(
            db=session,
            event_id=event_id,
            frames=[np.zeros((8, 8, 3), dtype=np.uint8)],
            detections=[None],
        )

        assert result == {"collage_url": None, "gif_url": None, "mp4_url": None}
        assert session.query(Event).filter(Event.id == event_id).first() is None
        assert timer_calls == []
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_generate_event_media_starts_delayed_timer_for_kept_event(tmp_path, monkeypatch):
    session, engine = _make_db_session(tmp_path)
    try:
        event_id = "event-keep-1"
        _add_camera_and_event(session, event_id)

        media_root = tmp_path / "media"
        monkeypatch.setattr(media_service.MediaService, "MEDIA_DIR", media_root)
        service = media_service.MediaService()

        timer_calls = []
        service.media_worker = _patch_media_dependencies(
            monkeypatch,
            duplicate_percentage=10.0,
            extract_ok=False,
            timer_calls=timer_calls,
        )

        result = service.generate_event_media(
            db=session,
            event_id=event_id,
            frames=[np.zeros((8, 8, 3), dtype=np.uint8)],
            detections=[None],
        )

        assert result["mp4_url"] is not None
        assert session.query(Event).filter(Event.id == event_id).first() is not None
        assert len(timer_calls) == 1
        assert timer_calls[0]["interval"] == media_service.RECORDING_MP4_DELAY_SEC
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_generate_event_media_keeps_event_on_moderate_duplicate_mp4(tmp_path, monkeypatch):
    session, engine = _make_db_session(tmp_path)
    try:
        event_id = "event-keep-dup-1"
        _add_camera_and_event(session, event_id)

        media_root = tmp_path / "media"
        monkeypatch.setattr(media_service.MediaService, "MEDIA_DIR", media_root)
        service = media_service.MediaService()

        timer_calls = []
        service.media_worker = _patch_media_dependencies(
            monkeypatch,
            duplicate_percentage=97.8,
            extract_ok=False,
            timer_calls=timer_calls,
        )

        result = service.generate_event_media(
            db=session,
            event_id=event_id,
            frames=[np.zeros((8, 8, 3), dtype=np.uint8)],
            detections=[None],
        )

        assert result["mp4_url"] is not None
        assert session.query(Event).filter(Event.id == event_id).first() is not None
        assert len(timer_calls) == 1
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_generate_collage_for_ai_uses_detection_focused_collage(tmp_path, monkeypatch):
    session, engine = _make_db_session(tmp_path)
    try:
        event_id = "event-ai-collage-1"
        _add_camera_and_event(session, event_id)

        media_root = tmp_path / "media"
        monkeypatch.setattr(media_service.MediaService, "MEDIA_DIR", media_root)
        service = media_service.MediaService()

        called = {"detections": None, "output_path": None}

        class DummyWorker:
            def create_ai_collage(
                self,
                frames,
                detections,
                timestamps,
                output_path,
                camera_name,
                timestamp,
                confidence,
            ):
                called["detections"] = detections
                called["output_path"] = output_path
                with open(output_path, "wb") as f:
                    f.write(b"ai-collage")
                return output_path

        service.media_worker = DummyWorker()
        detections = [{"bbox": [1, 1, 6, 7], "confidence": 0.88}]
        result = service.generate_collage_for_ai(
            db=session,
            event_id=event_id,
            frames=[np.zeros((8, 8, 3), dtype=np.uint8)],
            detections=detections,
            timestamps=[1700000000.0],
            camera_name="Test Cam",
        )

        assert result is not None
        assert result.exists()
        assert called["output_path"] == str(result)
        assert result.name == "collage_ai.jpg"
        assert called["detections"] == detections
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_generate_collage_for_review_uses_standard_collage(tmp_path, monkeypatch):
    session, engine = _make_db_session(tmp_path)
    try:
        event_id = "event-review-collage-1"
        _add_camera_and_event(session, event_id)

        media_root = tmp_path / "media"
        monkeypatch.setattr(media_service.MediaService, "MEDIA_DIR", media_root)
        service = media_service.MediaService()

        called = {"detections": None, "output_path": None}

        class DummyWorker:
            def create_collage(
                self,
                frames,
                detections,
                timestamps,
                output_path,
                camera_name,
                timestamp,
                confidence,
            ):
                called["detections"] = detections
                called["output_path"] = output_path
                with open(output_path, "wb") as f:
                    f.write(b"review-collage")
                return output_path

        service.media_worker = DummyWorker()
        detections = [{"bbox": [1, 1, 6, 7], "confidence": 0.88}]
        result = service.generate_collage_for_review(
            db=session,
            event_id=event_id,
            frames=[np.zeros((8, 8, 3), dtype=np.uint8)],
            detections=detections,
            timestamps=[1700000000.0],
            camera_name="Test Cam",
        )

        assert result is not None
        assert result.exists()
        assert called["output_path"] == str(result)
        assert result.name == "collage.jpg"
        assert called["detections"] == detections
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_ensure_user_collage_quality_repairs_legacy_ai_collage(tmp_path, monkeypatch):
    media_root = tmp_path / "media"
    event_id = "event-legacy-ai-collage-1"
    event_dir = media_root / event_id
    event_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(media_service.MediaService, "MEDIA_DIR", media_root)
    service = media_service.MediaService()

    ai_w = service.media_worker.AI_COLLAGE_FRAME_SIZE[0] * service.media_worker.AI_COLLAGE_GRID[0]
    ai_h = service.media_worker.AI_COLLAGE_FRAME_SIZE[1] * service.media_worker.AI_COLLAGE_GRID[1]
    legacy_ai_collage = np.full((ai_h, ai_w, 3), 22, dtype=np.uint8)
    cv2.imwrite(str(event_dir / "collage.jpg"), legacy_ai_collage)
    (event_dir / "timelapse.mp4").write_bytes(b"mp4")

    rebuilt_frames = [np.full((480, 640, 3), 30 + i * 10, dtype=np.uint8) for i in range(8)]
    monkeypatch.setattr(
        service,
        "_extract_frames_from_mp4",
        lambda _path, max_frames=18: rebuilt_frames,
    )

    result = service.ensure_user_collage_quality(event_id, camera_name="Repair Cam")
    assert result is not None
    assert result.exists()

    repaired = cv2.imread(str(result))
    assert repaired is not None
    expected_h = service.media_worker.COLLAGE_FRAME_SIZE[1] * service.media_worker.COLLAGE_GRID[1]
    expected_w = service.media_worker.COLLAGE_FRAME_SIZE[0] * service.media_worker.COLLAGE_GRID[0]
    assert repaired.shape[:2] == (expected_h, expected_w)


def test_ensure_user_collage_quality_uses_recording_fallback_when_mp4_missing(tmp_path, monkeypatch):
    media_root = tmp_path / "media"
    event_id = "event-legacy-ai-collage-2"
    event_dir = media_root / event_id
    event_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(media_service.MediaService, "MEDIA_DIR", media_root)
    service = media_service.MediaService()

    ai_w = service.media_worker.AI_COLLAGE_FRAME_SIZE[0] * service.media_worker.AI_COLLAGE_GRID[0]
    ai_h = service.media_worker.AI_COLLAGE_FRAME_SIZE[1] * service.media_worker.AI_COLLAGE_GRID[1]
    legacy_ai_collage = np.full((ai_h, ai_w, 3), 18, dtype=np.uint8)
    cv2.imwrite(str(event_dir / "collage.jpg"), legacy_ai_collage)

    rebuilt_frames = [np.full((480, 640, 3), 20 + i * 12, dtype=np.uint8) for i in range(7)]
    monkeypatch.setattr(
        service,
        "_extract_frames_from_mp4",
        lambda _path, max_frames=18: [],
    )
    monkeypatch.setattr(
        service,
        "_extract_frames_from_recording",
        lambda _event_id, max_frames=18, prebuffer_seconds=5.0, postbuffer_seconds=2.0: rebuilt_frames,
    )

    result = service.ensure_user_collage_quality(event_id, camera_name="Repair Cam")
    assert result is not None
    assert result.exists()

    repaired = cv2.imread(str(result))
    assert repaired is not None
    expected_h = service.media_worker.COLLAGE_FRAME_SIZE[1] * service.media_worker.COLLAGE_GRID[1]
    expected_w = service.media_worker.COLLAGE_FRAME_SIZE[0] * service.media_worker.COLLAGE_GRID[0]
    assert repaired.shape[:2] == (expected_h, expected_w)
