"""
Unit tests for media service background replacement behavior.
"""
from datetime import datetime, timedelta

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
