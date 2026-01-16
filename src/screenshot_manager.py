"""Screenshot management for Smart Motion Detector."""

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Deque, Optional, Tuple

import numpy as np

from .config import ScreenshotConfig
from .logger import get_logger
from .utils import encode_frame_to_base64, encode_frame_to_bytes


@dataclass
class ScreenshotSet:
    """A set of three screenshots captured around a motion event."""
    before: bytes
    current: bytes
    after: bytes
    timestamp: datetime
    before_base64: str
    current_base64: str
    after_base64: str


class ScreenshotManager:
    """
    Manages screenshot capture using a ring buffer for frame history.

    The ring buffer stores recent frames with timestamps, allowing
    retrieval of frames from before a motion event occurred.
    """

    def __init__(self, config: ScreenshotConfig):
        """
        Initialize screenshot manager with ring buffer.

        Args:
            config: Screenshot configuration including buffer size and quality settings
        """
        self.config = config
        self.logger = get_logger("screenshot_manager")

        # Calculate buffer size based on buffer_seconds and assumed fps
        # Using default fps of 5 from CameraConfig
        fps = 5  # frames per second
        buffer_size = config.buffer_seconds * fps

        # Initialize ring buffer to store (frame, timestamp) tuples
        self._buffer: Deque[Tuple[np.ndarray, datetime]] = deque(maxlen=buffer_size)

        self.logger.info(
            f"ScreenshotManager initialized with buffer size: {buffer_size} "
            f"({config.buffer_seconds}s at {fps} fps)"
        )

    def add_frame(self, frame: np.ndarray, timestamp: datetime) -> None:
        """
        Add a frame with timestamp to the ring buffer.

        The ring buffer automatically discards the oldest frame when full (maxlen).
        Deque operations are thread-safe for append operations.

        Args:
            frame: OpenCV frame (BGR format numpy array)
            timestamp: Timestamp when frame was captured
        """
        self._buffer.append((frame, timestamp))

    def get_buffer_size(self) -> int:
        """
        Get current number of frames in the buffer.

        Returns:
            Current buffer size (0 to maxlen)
        """
        return len(self._buffer)

    def _get_frame_before(self, timestamp: datetime, seconds: float) -> Optional[np.ndarray]:
        """
        Find frame closest to N seconds before the given timestamp.

        Searches the ring buffer for frames at or before the target time
        (timestamp - seconds) and returns the one closest to the target.

        Args:
            timestamp: Reference timestamp
            seconds: Number of seconds before timestamp to look for

        Returns:
            Frame closest to target time, or None if no suitable frame found
        """
        if not self._buffer:
            return None

        target_time = timestamp - timedelta(seconds=seconds)

        # Find frames that are at or before the target time
        candidates = [
            (frame, frame_time)
            for frame, frame_time in self._buffer
            if frame_time <= target_time
        ]

        if not candidates:
            return None

        # Return the frame closest to target_time (most recent before target)
        closest_frame, _ = max(candidates, key=lambda x: x[1])
        return closest_frame

    def _get_frame_after(self, timestamp: datetime, seconds: float) -> Optional[np.ndarray]:
        """
        Find frame closest to N seconds after the given timestamp.

        Searches the ring buffer for frames at or after the target time
        (timestamp + seconds) and returns the one closest to the target.

        Args:
            timestamp: Reference timestamp
            seconds: Number of seconds after timestamp to look for

        Returns:
            Frame closest to target time, or None if no suitable frame found
        """
        if not self._buffer:
            return None

        target_time = timestamp + timedelta(seconds=seconds)

        # Find frames that are at or after the target time
        candidates = [
            (frame, frame_time)
            for frame, frame_time in self._buffer
            if frame_time >= target_time
        ]

        if not candidates:
            return None

        # Return the frame closest to target_time (earliest after target)
        closest_frame, _ = min(candidates, key=lambda x: x[1])
        return closest_frame

    async def capture_sequence(self, current_frame: np.ndarray) -> ScreenshotSet:
        """
        Capture a sequence of three screenshots around a motion event.

        Gets a frame from before the event (from buffer), uses the provided
        current frame, and gets a frame from after the event (from buffer).

        Args:
            current_frame: The current frame at the moment of motion detection

        Returns:
            ScreenshotSet containing before/current/after frames with metadata

        Raises:
            ValueError: If unable to capture all three required frames
        """
        timestamp = datetime.now()

        # Get frame from before the event
        before_frame = self._get_frame_before(timestamp, self.config.before_seconds)
        if before_frame is None:
            raise ValueError(
                f"No frame found from {self.config.before_seconds}s before event. "
                f"Buffer size: {self.get_buffer_size()}"
            )

        # Wait for after_seconds to allow buffer to fill with post-event frames
        await asyncio.sleep(self.config.after_seconds)

        # Get frame from after the event
        after_frame = self._get_frame_after(timestamp, self.config.after_seconds)
        if after_frame is None:
            raise ValueError(
                f"No frame found from {self.config.after_seconds}s after event. "
                f"Buffer size: {self.get_buffer_size()}"
            )

        # Encode all frames to bytes and base64
        before_bytes = encode_frame_to_bytes(before_frame, self.config.quality)
        current_bytes = encode_frame_to_bytes(current_frame, self.config.quality)
        after_bytes = encode_frame_to_bytes(after_frame, self.config.quality)

        before_base64 = encode_frame_to_base64(before_frame, self.config.quality)
        current_base64 = encode_frame_to_base64(current_frame, self.config.quality)
        after_base64 = encode_frame_to_base64(after_frame, self.config.quality)

        self.logger.info(
            f"Captured screenshot sequence at {timestamp.isoformat()}: "
            f"before={len(before_bytes)} bytes, "
            f"current={len(current_bytes)} bytes, "
            f"after={len(after_bytes)} bytes"
        )

        return ScreenshotSet(
            before=before_bytes,
            current=current_bytes,
            after=after_bytes,
            timestamp=timestamp,
            before_base64=before_base64,
            current_base64=current_base64,
            after_base64=after_base64,
        )
