"""
Unit tests for recorder extraction error handling.
"""
import errno
import logging
import os
from datetime import datetime, timedelta

from app.services import recorder as recorder_service


def _patch_mkstemp_enoent_for_output(monkeypatch):
    real_mkstemp = recorder_service.tempfile.mkstemp

    def _fake_mkstemp(*args, **kwargs):
        # Keep regular temp files (e.g. concat list), but fail output temp creation.
        output_dir = kwargs.get("dir")
        if output_dir:
            missing_target = os.path.join(output_dir, "extract_missing.mp4")
            raise OSError(errno.ENOENT, "No such file or directory", missing_target)
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr(recorder_service.tempfile, "mkstemp", _fake_mkstemp)


def test_extract_single_treats_enoent_as_debug_skip(tmp_path, monkeypatch, caplog):
    recorder = recorder_service.ContinuousRecorder()
    output_dir = tmp_path / "event"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "timelapse.mp4"

    _patch_mkstemp_enoent_for_output(monkeypatch)

    start_time = datetime.utcnow()
    end_time = start_time + timedelta(seconds=6)

    with caplog.at_level(logging.DEBUG):
        ok = recorder._extract_single(
            "ffmpeg",
            tmp_path / "20260227_120000.mp4",
            start_time,
            end_time,
            str(output_path),
            speed_factor=4.0,
        )

    assert ok is False
    assert "Extract clip skipped: output path vanished during extraction" in caplog.text
    assert "Extract clip failed:" not in caplog.text


def test_extract_multi_treats_enoent_as_debug_skip(tmp_path, monkeypatch, caplog):
    recorder = recorder_service.ContinuousRecorder()
    output_dir = tmp_path / "event"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "timelapse.mp4"

    _patch_mkstemp_enoent_for_output(monkeypatch)

    files = [
        tmp_path / "20260227_120000.mp4",
        tmp_path / "20260227_120100.mp4",
    ]
    start_time = datetime(2026, 2, 27, 12, 0, 20)
    end_time = start_time + timedelta(seconds=8)

    with caplog.at_level(logging.DEBUG):
        ok = recorder._extract_multi(
            "ffmpeg",
            files,
            start_time,
            end_time,
            str(output_path),
            speed_factor=4.0,
        )

    assert ok is False
    assert "Multi-segment extract skipped: output path vanished during extraction" in caplog.text
    assert "Multi-segment extraction error:" not in caplog.text
