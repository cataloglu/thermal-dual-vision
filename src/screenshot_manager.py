"""Screenshot manager with optimized ring buffer for Smart Motion Detector."""

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Deque, Optional

logger = logging.getLogger(__name__)


@dataclass
class FrameSnapshot:
    """Single frame snapshot with timestamp."""
    frame: Any  # NDArray[np.uint8]
    timestamp: datetime


class ScreenshotManager:
    """
    Manages screenshot capture with optimized ring buffer.

    Uses collections.deque with dynamic maxlen based on FPS and buffer_seconds
    to efficiently manage memory usage.
    """

    def __init__(self, fps: int, buffer_seconds: int):
        """
        Initialize screenshot manager with ring buffer.

        Args:
            fps: Frames per second from camera
            buffer_seconds: Number of seconds to buffer
        """
        self.fps = fps
        self.buffer_seconds = buffer_seconds

        # Calculate ring buffer size: fps * buffer_seconds
        # This ensures we only keep the necessary frames in memory
        maxlen = fps * buffer_seconds

        # Use deque with maxlen for automatic old frame eviction
        self.buffer: Deque[FrameSnapshot] = deque(maxlen=maxlen)

        logger.info(
            f"Initialized ScreenshotManager with ring buffer size: {maxlen} "
            f"({fps} fps × {buffer_seconds}s)"
        )

    def add_frame(self, frame: Any, timestamp: Optional[datetime] = None) -> None:
        """
        Add a frame to the ring buffer.

        Args:
            frame: Frame to add (NDArray[np.uint8])
            timestamp: Frame timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        snapshot = FrameSnapshot(frame=frame, timestamp=timestamp)
        self.buffer.append(snapshot)

    def get_before_frame(self, seconds_before: int) -> Optional[Any]:
        """
        Get frame from N seconds before now.

        Args:
            seconds_before: How many seconds to look back

        Returns:
            Frame from N seconds ago, or None if not available
        """
        if not self.buffer:
            return None

        # Calculate target index: fps * seconds
        target_offset = self.fps * seconds_before

        # Get from buffer (from oldest to newest)
        if len(self.buffer) <= target_offset:
            # Return oldest frame if we don't have enough history
            return self.buffer[0].frame

        # Return frame from N seconds ago
        index = len(self.buffer) - target_offset - 1
        return self.buffer[max(0, index)].frame

    def get_current_frame(self) -> Optional[Any]:
        """
        Get most recent frame from buffer.

        Returns:
            Most recent frame, or None if buffer is empty
        """
        if not self.buffer:
            return None
        return self.buffer[-1].frame

    def clear(self) -> None:
        """Clear all frames from buffer."""
        self.buffer.clear()
        logger.debug("Screenshot buffer cleared")

    def get_buffer_size(self) -> int:
        """
        Get current number of frames in buffer.

        Returns:
            Number of frames currently buffered
        """
        return len(self.buffer)

    def get_buffer_capacity(self) -> int:
        """
        Get maximum buffer capacity.

        Returns:
            Maximum number of frames that can be buffered
        """
        return self.buffer.maxlen or 0

    def is_buffer_full(self) -> bool:
        """
        Check if buffer is at capacity.

        Returns:
            True if buffer is full, False otherwise
        """
        maxlen = self.buffer.maxlen
        return maxlen is not None and len(self.buffer) >= maxlen
