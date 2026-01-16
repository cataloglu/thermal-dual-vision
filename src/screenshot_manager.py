"""Screenshot management for Smart Motion Detector."""

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Deque, List, Optional, Tuple

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

        # Initialize storage for captured screenshot sets
        self._screenshot_sets: List[ScreenshotSet] = []

        self.logger.info(
            f"ScreenshotManager initialized with buffer size: {buffer_size} "
            f"({config.buffer_seconds}s at {fps} fps), max_stored: {config.max_stored}"
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

    def get_buffer_memory_usage(self) -> int:
        """
        Calculate total memory usage of frames in the buffer.

        Calculates the sum of memory used by all numpy arrays
        stored in the ring buffer.

        Returns:
            Total memory usage in bytes
        """
        total_bytes = 0
        for frame, _ in self._buffer:
            # Calculate memory size of numpy array
            # nbytes gives the total bytes consumed by the array's data
            total_bytes += frame.nbytes
        return total_bytes

    def get_buffer_statistics(self) -> dict:
        """
        Get comprehensive buffer statistics.

        Returns a dictionary with buffer state information including
        frame count, memory usage, and capacity utilization.

        Returns:
            Dictionary containing:
                - frame_count: Current number of frames in buffer
                - max_capacity: Maximum buffer capacity
                - utilization: Buffer utilization percentage (0-100)
                - memory_bytes: Total memory used by frames
                - memory_mb: Memory usage in megabytes
        """
        frame_count = len(self._buffer)
        max_capacity = self._buffer.maxlen if self._buffer.maxlen else 0
        memory_bytes = self.get_buffer_memory_usage()

        utilization = (frame_count / max_capacity * 100) if max_capacity > 0 else 0

        return {
            "frame_count": frame_count,
            "max_capacity": max_capacity,
            "utilization": round(utilization, 2),
            "memory_bytes": memory_bytes,
            "memory_mb": round(memory_bytes / (1024 * 1024), 2)
        }

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

        screenshot_set = ScreenshotSet(
            before=before_bytes,
            current=current_bytes,
            after=after_bytes,
            timestamp=timestamp,
            before_base64=before_base64,
            current_base64=current_base64,
            after_base64=after_base64,
        )

        # Store the screenshot set
        self._screenshot_sets.append(screenshot_set)

        return screenshot_set

    def cleanup_old(self, max_count: int) -> int:
        """
        Remove old screenshot sets to keep only the most recent max_count.

        Keeps the most recent screenshot sets and removes older ones
        to prevent unbounded memory growth.

        Args:
            max_count: Maximum number of screenshot sets to keep

        Returns:
            Number of screenshot sets removed
        """
        current_count = len(self._screenshot_sets)

        if current_count <= max_count:
            return 0

        # Calculate how many to remove
        remove_count = current_count - max_count

        # Remove the oldest screenshot sets (first in list)
        self._screenshot_sets = self._screenshot_sets[remove_count:]

        self.logger.info(
            f"Cleaned up {remove_count} old screenshot sets. "
            f"Retained {len(self._screenshot_sets)} most recent sets."
        )

        return remove_count
