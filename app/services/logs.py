"""
Logs service for Smart Motion Detector v2.

Handles log file reading for diagnostics.
"""
import logging
from pathlib import Path
from typing import List

from app.utils.rtsp import redact_rtsp_urls_in_text

logger = logging.getLogger(__name__)


class LogsService:
    """
    Logs service for reading application logs.
    
    Handles:
    - Log file reading
    - Line limiting
    - Tail functionality
    """
    
    # Default log file path (can be configured)
    LOG_FILE = Path("logs/app.log")
    
    def __init__(self, log_file: Path = None):
        """
        Initialize logs service.
        
        Args:
            log_file: Path to log file (optional)
        """
        self.log_file = log_file or self.LOG_FILE
        logger.info(f"LogsService initialized with log file: {self.log_file}")
    
    def get_logs(self, lines: int = 200) -> List[str]:
        """
        Get last N lines from log file.
        Reads from the end of file to avoid scanning the full file on every poll.
        """
        try:
            if not self.log_file.exists():
                logger.warning(f"Log file not found: {self.log_file}")
                return [f"Log file not found: {self.log_file}"]

            # Read from end: scan backward in 32 KB chunks until we have enough lines
            chunk_size = 32 * 1024
            file_size = self.log_file.stat().st_size
            collected: list[str] = []

            with open(self.log_file, "rb") as f:
                pos = file_size
                leftover = b""
                while pos > 0 and len(collected) < lines:
                    read_size = min(chunk_size, pos)
                    pos -= read_size
                    f.seek(pos)
                    chunk = f.read(read_size) + leftover
                    # Split on newlines; last partial line becomes leftover for next chunk
                    parts = chunk.split(b"\n")
                    leftover = parts[0]
                    new_lines = [p.decode("utf-8", errors="ignore") for p in reversed(parts[1:])]
                    collected = new_lines + collected
                # Include any leading leftover
                if leftover:
                    collected = [leftover.decode("utf-8", errors="ignore")] + collected

            tail = collected[-lines:] if len(collected) > lines else collected

            # Redact RTSP credentials
            log_lines = [redact_rtsp_urls_in_text(line) for line in tail]

            logger.debug(f"Retrieved {len(log_lines)} log lines")
            return log_lines
            
        except Exception as e:
            logger.error(f"Failed to read logs: {e}")
            return [f"Error reading logs: {str(e)}"]
    
    def get_log_file_size(self) -> int:
        """
        Get log file size in bytes.
        
        Returns:
            File size in bytes, or 0 if not found
        """
        try:
            if self.log_file.exists():
                return self.log_file.stat().st_size
            return 0
        except Exception:
            return 0

    def clear_logs(self) -> bool:
        """
        Truncate the log file.
        
        Returns:
            True if the file existed and was cleared, False otherwise
        """
        try:
            if not self.log_file.exists():
                return False
            with open(self.log_file, "w", encoding="utf-8"):
                pass
            return True
        except Exception as e:
            logger.error("Failed to clear logs: %s", e)
            return False


# Global singleton instance
_logs_service: LogsService | None = None


def get_logs_service() -> LogsService:
    """
    Get or create the global logs service instance.
    
    Returns:
        LogsService: Global logs service instance
    """
    global _logs_service
    if _logs_service is None:
        _logs_service = LogsService()
    return _logs_service
