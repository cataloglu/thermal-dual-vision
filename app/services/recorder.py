"""
Continuous recorder service (rolling buffer for event clips).

Records camera streams to disk using FFmpeg.
Event clips are extracted from this buffer when motion is detected.

Recording segment filenames use UTC (TZ=UTC) for consistency with event timestamps.
"""
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.utils.paths import DATA_DIR

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

logger = logging.getLogger(__name__)

# Fixed recording buffer (no user config - full performance)
RECORDING_BUFFER_HOURS = 1  # Her kamera son 1 saat
SEGMENT_DURATION = 60  # seconds per segment
CLEANUP_INTERVAL_SEC = 300  # 5 dakikada bir temizlik


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
        self._processes_lock = threading.Lock()
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
        with self._processes_lock:
            if camera_id in self.processes:
                proc = self.processes[camera_id]
                if proc.poll() is None:
                    logger.debug("Recording already running for camera %s", camera_id)
                    return True
                # Process died, clean up before restart (lock held)
                self._cleanup_process_locked(camera_id)

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
            env = os.environ.copy()
            env["TZ"] = "UTC"
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                env=env,
            )
            with self._processes_lock:
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
        with self._processes_lock:
            process = self.processes.pop(camera_id, None)
            self.rtsp_urls.pop(camera_id, None)
        if not process:
            return
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        except Exception:
            pass
        logger.info("Stopped continuous recording for camera %s", camera_id)

    def is_recording(self, camera_id: str) -> bool:
        with self._processes_lock:
            proc = self.processes.get(camera_id)
        return proc is not None and proc.poll() is None

    # ------------------------------------------------------------------
    # Health monitor — restart crashed FFmpeg processes
    # ------------------------------------------------------------------

    def _monitor_loop(self) -> None:
        last_buffer_cleanup = 0.0
        while self.running:
            try:
                with self._processes_lock:
                    snapshot = list(self.processes.items())
                for camera_id, proc in snapshot:
                    if proc.poll() is not None:
                        with self._processes_lock:
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

                now = time.time()
                if now - last_buffer_cleanup >= CLEANUP_INTERVAL_SEC:
                    last_buffer_cleanup = now
                    try:
                        self.cleanup_old_recordings(max_age_seconds=RECORDING_BUFFER_HOURS * 3600)
                    except Exception as e:
                        logger.error("Recording buffer cleanup error: %s", e)
            except Exception as e:
                logger.error("Recorder monitor error: %s", e)
            time.sleep(10)

    def _cleanup_process(self, camera_id: str) -> None:
        """Remove and reap the process for camera_id (no lock held required)."""
        with self._processes_lock:
            proc = self.processes.pop(camera_id, None)
            self.rtsp_urls.pop(camera_id, None)
        if proc and proc.poll() is None:
            try:
                proc.kill()
                proc.wait()
            except Exception:
                pass

    def _cleanup_process_locked(self, camera_id: str) -> None:
        """Like _cleanup_process but assumes _processes_lock is already held."""
        proc = self.processes.pop(camera_id, None)
        self.rtsp_urls.pop(camera_id, None)
        if proc and proc.poll() is None:
            try:
                proc.kill()
                proc.wait()
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
        speed_factor: float = 4.0,
        *,
        use_utc_for_cutoff: bool = True,
    ) -> bool:
        camera_dir = self.recording_dir / camera_id
        if not camera_dir.exists():
            logger.error("No recordings found for camera %s", camera_id)
            return False

        files = self._find_recordings_in_range(camera_id, start_time, end_time, use_utc_for_cutoff=use_utc_for_cutoff)
        if not files:
            camera_dir = self.recording_dir / camera_id
            all_files = sorted(camera_dir.glob("*.mp4")) if camera_dir.exists() else []
            sample = [f.stem for f in all_files[:5]] if all_files else []
            # Diagnostic: show segment time range vs search range
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            safe = now_utc - timedelta(seconds=3)
            min_ts = max_ts = None
            for f in all_files:
                ts = self._parse_filename_timestamp(f)
                if ts:
                    min_ts = ts if min_ts is None else min(min_ts, ts)
                    max_ts = ts if max_ts is None else max(max_ts, ts)
            logger.info(
                "Recording segment not ready for %s (search %s–%s UTC, segments %s–%s); using buffer MP4, will replace in ~58s.",
                camera_id, start_time, end_time,
                min_ts.isoformat() if min_ts else "none",
                max_ts.isoformat() if max_ts else "none",
            )
            return False

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            logger.error("ffmpeg not found on PATH")
            return False

        if len(files) == 1:
            return self._extract_single(
                ffmpeg, files[0], start_time, end_time, output_path, speed_factor
            )
        return self._extract_multi(
            ffmpeg, files, start_time, end_time, output_path, speed_factor
        )

    def extract_frames(
        self,
        camera_id: str,
        start_time: "datetime",
        end_time: "datetime",
        max_frames: int = 5,
    ) -> List:
        """
        Extract frames from recording for event collage when buffer has no frames.
        Returns list of numpy arrays (BGR) or empty list on failure.
        """
        if not _CV2_AVAILABLE:
            return []
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(suffix=".mp4", prefix="event_frames_")
            os.close(fd)
            if not self.extract_clip(camera_id, start_time, end_time, tmp, speed_factor=1.0):
                # Fallback: try local timezone
                start_utc = start_time.replace(tzinfo=timezone.utc)
                end_utc = end_time.replace(tzinfo=timezone.utc)
                start_local = start_utc.astimezone().replace(tzinfo=None)
                end_local = end_utc.astimezone().replace(tzinfo=None)
                if not self.extract_clip(
                    camera_id, start_local, end_local, tmp,
                    speed_factor=1.0, use_utc_for_cutoff=False,
                ):
                    return []
            cap = cv2.VideoCapture(tmp)
            frames = []
            try:
                while len(frames) < max_frames:
                    ret, fr = cap.read()
                    if not ret or fr is None:
                        break
                    frames.append(fr.copy())
            finally:
                cap.release()
            return frames
        except Exception as e:
            logger.warning("extract_frames failed: %s", e)
            return []
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except Exception:
                    pass

    def _extract_single(
        self,
        ffmpeg: str,
        recording: Path,
        start_time: datetime,
        end_time: datetime,
        output_path: str,
        speed_factor: float = 4.0,
    ) -> bool:
        file_start = self._parse_filename_timestamp(recording)
        if file_start is None:
            offset = 0.0
        else:
            offset = max(0.0, (start_time - file_start).total_seconds())

        duration = (end_time - start_time).total_seconds()

        tmp_path = None
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(
                suffix=".mp4", prefix="extract_", dir=os.path.dirname(output_path)
            )
            os.close(tmp_fd)

            if speed_factor <= 1.0:
                cmd = [
                    ffmpeg, "-hide_banner", "-loglevel", "error",
                    "-i", str(recording),
                    "-ss", f"{offset:.2f}",
                    "-t", f"{duration:.2f}",
                    "-c", "copy",
                    "-movflags", "+faststart",
                    "-y", tmp_path,
                ]
            else:
                pts = 1.0 / speed_factor
                cmd = [
                    ffmpeg, "-hide_banner", "-loglevel", "error",
                    "-i", str(recording),
                    "-ss", f"{offset:.2f}",
                    "-t", f"{duration:.2f}",
                    "-filter:v", f"setpts={pts}*PTS",
                    "-an",
                    "-c:v", "libx264",
                    "-preset", "medium",
                    "-crf", "18",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    "-y", tmp_path,
                ]
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode == 0:
                # Verify the output is a real video file (not just an empty container).
                # FFmpeg returns 0 even when it writes 0 frames (e.g. gap in recording).
                min_size = 4096  # 4 KB — any valid single-frame MP4 will exceed this
                actual_size = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
                if actual_size < min_size:
                    logger.warning(
                        "FFmpeg produced a suspiciously small clip (%d bytes) for %s — "
                        "likely an empty container; keeping existing file.",
                        actual_size,
                        output_path,
                    )
                    return False
                os.replace(tmp_path, output_path)
                tmp_path = None
                logger.info("Extracted clip: %s (%.1fx speed)", output_path, speed_factor)
                return True
            stderr = result.stderr.decode(errors="ignore")
            if "moov atom not found" in stderr or "Invalid data" in stderr:
                logger.info(
                    "Segment still being written (moov not ready); using buffer MP4, delayed replace in ~58s."
                )
            else:
                logger.warning("FFmpeg extraction failed (rc=%s): %s", result.returncode, stderr[:200])
            return False
        except Exception as e:
            logger.warning("Extract clip failed: %s", e)
            return False
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _extract_multi(
        self,
        ffmpeg: str,
        files: List[Path],
        start_time: datetime,
        end_time: datetime,
        output_path: str,
        speed_factor: float = 4.0,
    ) -> bool:
        """Extract clip spanning multiple segment files using concat demuxer."""
        concat_fd = None
        concat_path = None
        tmp_path = None
        try:
            concat_fd, concat_path = tempfile.mkstemp(suffix=".txt", prefix="concat_")
            with open(concat_fd, "w", encoding="utf-8") as f:
                for fp in files:
                    escaped = str(fp).replace("'", "'\\''")
                    f.write(f"file '{escaped}'\n")
            concat_fd = None  # ownership transferred

            tmp_fd, tmp_path = tempfile.mkstemp(
                suffix=".mp4", prefix="extract_", dir=os.path.dirname(output_path)
            )
            os.close(tmp_fd)

            first_start = self._parse_filename_timestamp(files[0])
            if first_start is None:
                offset = 0.0
            else:
                offset = max(0.0, (start_time - first_start).total_seconds())

            duration = (end_time - start_time).total_seconds()

            if speed_factor <= 1.0:
                cmd = [
                    ffmpeg, "-hide_banner", "-loglevel", "error",
                    "-f", "concat", "-safe", "0",
                    "-i", concat_path,
                    "-ss", f"{offset:.2f}",
                    "-t", f"{duration:.2f}",
                    "-c", "copy",
                    "-movflags", "+faststart",
                    "-y", tmp_path,
                ]
            else:
                pts = 1.0 / speed_factor
                cmd = [
                    ffmpeg, "-hide_banner", "-loglevel", "error",
                    "-f", "concat", "-safe", "0",
                    "-i", concat_path,
                    "-ss", f"{offset:.2f}",
                    "-t", f"{duration:.2f}",
                    "-filter:v", f"setpts={pts}*PTS",
                    "-an",
                    "-c:v", "libx264",
                    "-preset", "medium",
                    "-crf", "18",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    "-y", tmp_path,
                ]
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode == 0:
                min_size = 4096
                actual_size = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
                if actual_size < min_size:
                    logger.warning(
                        "FFmpeg concat produced a suspiciously small clip (%d bytes) — "
                        "likely an empty container; keeping existing file.",
                        actual_size,
                    )
                    return False
                os.replace(tmp_path, output_path)
                tmp_path = None
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
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
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
        *,
        use_utc_for_cutoff: bool = True,
    ) -> List[Path]:
        camera_dir = self.recording_dir / camera_id
        if not camera_dir.exists():
            return []

        segment_len = timedelta(seconds=SEGMENT_DURATION)
        # Exclude segments still being written by FFmpeg (allow 3s margin)
        # now/safe_cutoff must match timezone of segment filenames and start/end_time
        if use_utc_for_cutoff:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            now = datetime.now()  # local (matches FFmpeg strftime when TZ not set)
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
