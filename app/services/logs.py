"""
Logs service for Smart Motion Detector v2.

Handles log file reading for diagnostics.
"""
import logging
from collections import deque
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
        
        Args:
            lines: Number of lines to return (default 200)
            
        Returns:
            List of log lines (newest last)
        """
        try:
            if not self.log_file.exists():
                logger.warning(f"Log file not found: {self.log_file}")
                return [f"Log file not found: {self.log_file}"]
            
            # Read file with bounded memory
            tail: deque[str] = deque(maxlen=lines)
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    tail.append(line.rstrip('\n'))

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
