"""
Continuous recorder service (rollling buffer for event clips).

Records camera streams to disk using FFmpeg.
Each camera keeps only the last N hours (default 1) as a circular buffer.
Event clips are extracted from this buffer when motion is detected.
"""
import logging
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.utils.paths import DATA_DIR


logger = logging.getLogger(__name__)

SEGMENT_DURATION = 60  # seconds per segment


class ContinuousRecorder:
    """
    Continuous recording service for cameras.

    Uses FFmpeg to record camera streams directly to disk without re-encoding.
    Segments recordings into 60-second chunks for efficient storage and retrieval.
    """

    def __init__(self):
        self.recording_dir = DATA_DIR / "recordings"
        self.recording_dir.mkdir(parents=True, exist_ok=True)

        self.processes: Dict[str, subprocess.Popen] = {}
        self.rtsp_urls: Dict[str, str] = {}
        self.running = False
        self._monitor_thread: Optional[threading.Thread] = None

        logger.info("ContinuousRecorder initialized - dir: %s", self.recording_dir)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the health-monitor background thread."""
        if self.running:
            return
        self.running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="recorder-monitor",
        )
        self._monitor_thread.start()
        logger.info("Recorder health monitor started")

    def stop(self) -> None:
        """Stop all recordings and the monitor thread."""
        self.running = False
        for camera_id in list(self.processes.keys()):
            self.stop_recording(camera_id)
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("ContinuousRecorder stopped")

    # ------------------------------------------------------------------
    # Recording control
    # ------------------------------------------------------------------

    def start_recording(self, camera_id: str, rtsp_url: str) -> bool:
        if camera_id in self.processes:
            proc = self.processes[camera_id]
            if proc.poll() is None:
                logger.debug("Recording already running for camera %s", camera_id)
                return True
            # Process died, clean up and restart
            self._cleanup_process(camera_id)

        camera_dir = self.recording_dir / camera_id
        camera_dir.mkdir(parents=True, exist_ok=True)

        output_pattern = str(camera_dir / "%Y%m%d_%H%M%S.mp4")

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            logger.error("ffmpeg not found on PATH")
            return False

        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-c", "copy",
            "-f", "segment",
            "-segment_time", str(SEGMENT_DURATION),
            "-segment_format", "mp4",
            "-reset_timestamps", "1",
            "-strftime", "1",
            output_pattern,
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            self.processes[camera_id] = process
            self.rtsp_urls[camera_id] = rtsp_url
            logger.info(
                "Started continuous recording for camera %s (PID: %s)",
                camera_id,
                process.pid,
            )
            return True
        except Exception as e:
            logger.error("Failed to start recording for camera %s: %s", camera_id, e)
            return False

    def stop_recording(self, camera_id: str) -> None:
        process = self.processes.pop(camera_id, None)
        self.rtsp_urls.pop(camera_id, None)
        if not process:
            return
        try:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
        logger.info("Stopped continuous recording for camera %s", camera_id)

    def is_recording(self, camera_id: str) -> bool:
        proc = self.processes.get(camera_id)
        return proc is not None and proc.poll() is None

    # ------------------------------------------------------------------
    # Health monitor — restart crashed FFmpeg processes
    # ------------------------------------------------------------------

    def _monitor_loop(self) -> None:
        last_buffer_cleanup = 0.0
        while self.running:
            try:
                for camera_id in list(self.processes.keys()):
                    proc = self.processes.get(camera_id)
                    if proc is None:
                        continue
                    if proc.poll() is not None:
                        url = self.rtsp_urls.get(camera_id)
                        if url:
                            logger.warning(
                                "Recording process died for camera %s (rc=%s), restarting",
                                camera_id,
                                proc.returncode,
                            )
                            self._cleanup_process(camera_id)
                            self.start_recording(camera_id, url)
                        else:
                            self._cleanup_process(camera_id)

                # Circular buffer cleanup: keep only last 1 hour per camera (every 5 min)
                now = time.time()
                if now - last_buffer_cleanup >= 300:
                    last_buffer_cleanup = now
                    try:
                        self.cleanup_old_recordings(max_age_seconds=3600)
                    except Exception as e:
                        logger.error("Recording buffer cleanup error: %s", e)
            except Exception as e:
                logger.error("Recorder monitor error: %s", e)
            time.sleep(10)

    def _cleanup_process(self, camera_id: str) -> None:
        proc = self.processes.pop(camera_id, None)
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Clip extraction
    # ------------------------------------------------------------------

    def extract_clip(
        self,
        camera_id: str,
        start_time: datetime,
        end_time: datetime,
        output_path: str,
    ) -> bool:
        camera_dir = self.recording_dir / camera_id
        if not camera_dir.exists():
            logger.error("No recordings found for camera %s", camera_id)
            return False

        files = self._find_recordings_in_range(camera_id, start_time, end_time)
        if not files:
            all_files = list((self.recording_dir / camera_id).glob("*.mp4")) if (self.recording_dir / camera_id).exists() else []
            logger.warning(
                "No recordings for %s range %s - %s (found %d segment files)",
                camera_id, start_time, end_time, len(all_files),
            )
            return False

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            logger.error("ffmpeg not found on PATH")
            return False

        if len(files) == 1:
            return self._extract_single(
                ffmpeg, files[0], start_time, end_time, output_path
            )
        return self._extract_multi(
            ffmpeg, files, start_time, end_time, output_path
        )

    def _extract_single(
        self,
        ffmpeg: str,
        recording: Path,
        start_time: datetime,
        end_time: datetime,
        output_path: str,
    ) -> bool:
        file_start = self._parse_filename_timestamp(recording)
        if file_start is None:
            offset = 0.0
        else:
            offset = max(0.0, (start_time - file_start).total_seconds())

        duration = (end_time - start_time).total_seconds()

        # -i before -ss for accurate trim; -c copy = no re-encode, original quality
        cmd = [
            ffmpeg, "-hide_banner", "-loglevel", "error",
            "-i", str(recording),
            "-ss", f"{offset:.2f}",
            "-t", f"{duration:.2f}",
            "-c", "copy",
            "-movflags", "+faststart",
            "-y", output_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            if result.returncode == 0:
                logger.info("Extracted clip: %s", output_path)
                return True
            logger.error(
                "FFmpeg extraction failed (rc=%s): %s",
                result.returncode,
                result.stderr.decode(errors="ignore")[:300],
            )
            return False
        except Exception as e:
            logger.error("Failed to extract clip: %s", e)
            return False

    def _extract_multi(
        self,
        ffmpeg: str,
        files: List[Path],
        start_time: datetime,
        end_time: datetime,
        output_path: str,
    ) -> bool:
        """Extract clip spanning multiple segment files using concat demuxer."""
        concat_fd = None
        concat_path = None
        try:
            concat_fd, concat_path = tempfile.mkstemp(suffix=".txt", prefix="concat_")
            with open(concat_fd, "w", encoding="utf-8") as f:
                for fp in files:
                    escaped = str(fp).replace("'", "'\\''")
                    f.write(f"file '{escaped}'\n")
            concat_fd = None  # ownership transferred

            # Calculate global offset from first file
            first_start = self._parse_filename_timestamp(files[0])
            if first_start is None:
                offset = 0.0
            else:
                offset = max(0.0, (start_time - first_start).total_seconds())

            duration = (end_time - start_time).total_seconds()

            cmd = [
                ffmpeg, "-hide_banner", "-loglevel", "error",
                "-f", "concat", "-safe", "0",
                "-i", concat_path,
                "-ss", f"{offset:.2f}",
                "-t", f"{duration:.2f}",
                "-c", "copy",
                "-movflags", "+faststart",
                "-y", output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            if result.returncode == 0:
                logger.info("Extracted multi-segment clip: %s", output_path)
                return True
            logger.error(
                "FFmpeg concat extraction failed: %s",
                result.stderr.decode(errors="ignore")[:300],
            )
            return False
        except Exception as e:
            logger.error("Multi-segment extraction error: %s", e)
            return False
        finally:
            if concat_path:
                try:
                    Path(concat_path).unlink(missing_ok=True)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # File lookup helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_filename_timestamp(path: Path) -> Optional[datetime]:
        """Parse YYYYMMDD_HHMMSS from filename."""
        try:
            stem = path.stem  # e.g. "20260210_143022"
            return datetime.strptime(stem, "%Y%m%d_%H%M%S")
        except (ValueError, AttributeError):
            return None

    def _find_recordings_in_range(
        self,
        camera_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Path]:
        camera_dir = self.recording_dir / camera_id
        if not camera_dir.exists():
            return []

        segment_len = timedelta(seconds=SEGMENT_DURATION)
        # Exclude segments still being written by FFmpeg (allow 3s margin)
        now = datetime.now()
        safe_cutoff = now - timedelta(seconds=3)
        matched: List[Path] = []

        for mp4 in sorted(camera_dir.glob("*.mp4")):
            file_start = self._parse_filename_timestamp(mp4)
            if file_start is None:
                continue
            file_end = file_start + segment_len
            if file_end > safe_cutoff:
                continue  # Segment still being written
            if file_start <= end_time and file_end >= start_time:
                matched.append(mp4)

        return matched

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup_old_recordings(self, max_age_seconds: int) -> None:
        cutoff_time = time.time() - max_age_seconds
        deleted_count = 0

        for camera_dir in self.recording_dir.iterdir():
            if not camera_dir.is_dir():
                continue
            for recording_file in camera_dir.glob("*.mp4"):
                if recording_file.stat().st_mtime < cutoff_time:
                    try:
                        recording_file.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.error("Failed to delete %s: %s", recording_file, e)
            # Remove empty camera dirs
            try:
                if camera_dir.exists() and not any(camera_dir.iterdir()):
                    camera_dir.rmdir()
            except Exception:
                pass

        if deleted_count > 0:
            logger.info("Deleted %d old recording files", deleted_count)


# Global singleton
_recorder: Optional[ContinuousRecorder] = None


def get_continuous_recorder() -> ContinuousRecorder:
    global _recorder
    if _recorder is None:
        _recorder = ContinuousRecorder()
    return _recorder
