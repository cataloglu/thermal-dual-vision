"""
Continuous recorder service (Scrypted-style approach).

Records camera streams 24/7 to disk using FFmpeg.
Event clips are extracted from continuous recordings.
"""
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from app.utils.paths import DATA_DIR


logger = logging.getLogger(__name__)


class ContinuousRecorder:
    """
    Continuous recording service for cameras.
    
    Uses FFmpeg to record camera streams directly to disk without re-encoding.
    Segments recordings into 60-second chunks for efficient storage and retrieval.
    """
    
    def __init__(self):
        """Initialize continuous recorder."""
        self.recording_dir = DATA_DIR / "recordings"
        self.recording_dir.mkdir(parents=True, exist_ok=True)
        
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = False
        
        logger.info(f"ContinuousRecorder initialized - recordings dir: {self.recording_dir}")
    
    def start_recording(self, camera_id: str, rtsp_url: str) -> bool:
        """
        Start continuous recording for a camera.
        
        Args:
            camera_id: Camera identifier
            rtsp_url: RTSP stream URL
            
        Returns:
            True if started successfully
        """
        if camera_id in self.processes:
            logger.warning(f"Recording already running for camera {camera_id}")
            return False
        
        # Create camera recording directory
        camera_dir = self.recording_dir / camera_id
        camera_dir.mkdir(parents=True, exist_ok=True)
        
        # Output pattern: YYYYMMDD_HHMMSS.mp4
        output_pattern = str(camera_dir / "%Y%m%d_%H%M%S.mp4")
        
        # FFmpeg command: continuous recording with segmentation
        cmd = [
            "ffmpeg",
            "-rtsp_transport", "tcp",  # Use TCP for reliability
            "-i", rtsp_url,
            "-c", "copy",  # NO re-encoding! Direct copy
            "-f", "segment",  # Segment output
            "-segment_time", "60",  # 60 second segments
            "-segment_format", "mp4",
            "-reset_timestamps", "1",  # Reset timestamps per segment
            "-strftime", "1",  # Enable strftime in output
            output_pattern,
            "-loglevel", "error",  # Only show errors
        ]
        
        try:
            # Start FFmpeg process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )
            
            self.processes[camera_id] = process
            logger.info(f"Started continuous recording for camera {camera_id} (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start recording for camera {camera_id}: {e}")
            return False
    
    def stop_recording(self, camera_id: str) -> None:
        """
        Stop continuous recording for a camera.
        
        Args:
            camera_id: Camera identifier
        """
        process = self.processes.pop(camera_id, None)
        if not process:
            logger.warning(f"No recording process for camera {camera_id}")
            return
        
        try:
            process.terminate()
            process.wait(timeout=5)
            logger.info(f"Stopped continuous recording for camera {camera_id}")
        except Exception as e:
            logger.error(f"Failed to stop recording for camera {camera_id}: {e}")
            try:
                process.kill()
            except:
                pass
    
    def extract_clip(
        self,
        camera_id: str,
        start_time: datetime,
        end_time: datetime,
        output_path: str,
    ) -> bool:
        """
        Extract event clip from continuous recording.
        
        Args:
            camera_id: Camera identifier
            start_time: Clip start time
            end_time: Clip end time
            output_path: Output MP4 path
            
        Returns:
            True if extracted successfully
        """
        camera_dir = self.recording_dir / camera_id
        
        if not camera_dir.exists():
            logger.error(f"No recordings found for camera {camera_id}")
            return False
        
        # Find relevant recording files (by timestamp)
        recording_files = self._find_recordings_in_range(camera_id, start_time, end_time)
        
        if not recording_files:
            logger.warning(f"No recordings found for time range: {start_time} - {end_time}")
            return False
        
        # If multiple segments, concatenate first
        if len(recording_files) > 1:
            # TODO: Implement multi-file concatenation
            logger.warning("Multi-segment extraction not yet implemented, using first file")
            input_file = recording_files[0]
        else:
            input_file = recording_files[0]
        
        # Calculate time offset within the recording file
        # (Simplified: assume start_time is file start)
        duration = (end_time - start_time).total_seconds()
        
        # Extract clip with FFmpeg
        cmd = [
            "ffmpeg",
            "-i", str(input_file),
            "-t", str(duration),  # Duration
            "-c", "copy",  # NO re-encoding!
            "-y",  # Overwrite output
            output_path,
            "-loglevel", "error",
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Extracted clip: {output_path}")
                return True
            else:
                logger.error(f"FFmpeg extraction failed: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to extract clip: {e}")
            return False
    
    def _find_recordings_in_range(
        self,
        camera_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list:
        """
        Find recording files that overlap with time range.
        
        Args:
            camera_id: Camera identifier
            start_time: Range start
            end_time: Range end
            
        Returns:
            List of recording file paths
        """
        camera_dir = self.recording_dir / camera_id
        
        if not camera_dir.exists():
            return []
        
        # Get all MP4 files
        files = sorted(camera_dir.glob("*.mp4"))
        
        # TODO: Parse timestamps from filenames and filter by range
        # For now, return last 3 files (covers ~3 minutes)
        return files[-3:] if len(files) >= 3 else files
    
    def cleanup_old_recordings(self, max_age_days: int = 7) -> None:
        """
        Delete recordings older than max_age_days.
        
        Args:
            max_age_days: Maximum recording age in days
        """
        cutoff_time = time.time() - (max_age_days * 86400)
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
                        logger.error(f"Failed to delete {recording_file}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old recording files")


# Global singleton
_recorder: Optional[ContinuousRecorder] = None


def get_continuous_recorder() -> ContinuousRecorder:
    """
    Get or create the global continuous recorder instance.
    
    Returns:
        ContinuousRecorder: Global instance
    """
    global _recorder
    if _recorder is None:
        _recorder = ContinuousRecorder()
    return _recorder
