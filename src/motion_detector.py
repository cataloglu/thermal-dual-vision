"""Motion detection with optimized numpy array reuse."""

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

try:
    import psutil
except ImportError:
    psutil = None

from .config import MotionConfig

logger = logging.getLogger(__name__)


class MotionDetector:
    """
    Optimized motion detector with pre-allocated numpy arrays.

    Reuses arrays across frames to minimize memory allocations and improve performance.
    """

    def __init__(self, config: MotionConfig, frame_shape: Tuple[int, int, int]):
        """
        Initialize motion detector with pre-allocated buffers.

        Args:
            config: Motion detection configuration
            frame_shape: Expected frame shape (height, width, channels)
        """
        self.config = config
        self.frame_shape = frame_shape
        height, width, _ = frame_shape

        # Initialize background subtractor
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=self.config.sensitivity,
            detectShadows=True
        )

        # Pre-allocate numpy arrays for reuse (memory optimization)
        self._gray_frame = np.zeros((height, width), dtype=np.uint8)
        self._fg_mask = np.zeros((height, width), dtype=np.uint8)
        self._thresh = np.zeros((height, width), dtype=np.uint8)
        self._blur = np.zeros((height, width), dtype=np.uint8)

        # Frame skip mechanism for CPU optimization
        self._skip_count = 0
        self._total_frames = 0
        self._last_cpu_check = 0

        logger.info(
            f"MotionDetector initialized with pre-allocated arrays "
            f"({width}x{height}), sensitivity={config.sensitivity}, "
            f"frame_skip_threshold={config.frame_skip_threshold}%"
        )

    def should_skip_frame(self, queue_size: Optional[int] = None) -> bool:
        """
        Determine if frame should be skipped based on CPU load or queue size.

        Args:
            queue_size: Optional queue size to check against threshold

        Returns:
            True if frame should be skipped due to high load
        """
        self._total_frames += 1

        # Check CPU usage (avoid checking every frame for performance)
        high_load = False
        if self._total_frames % 10 == 0 and psutil:
            try:
                cpu_percent = psutil.cpu_percent(interval=0)
                if cpu_percent > self.config.frame_skip_threshold:
                    high_load = True
                    logger.debug(f"High CPU load detected: {cpu_percent:.1f}%")
            except Exception as e:
                logger.warning(f"Failed to check CPU usage: {e}")

        # Check queue size if provided (simple heuristic: skip if queue > 10)
        if queue_size is not None and queue_size > 10:
            high_load = True
            logger.debug(f"High queue size detected: {queue_size}")

        if high_load:
            self._skip_count += 1

        return high_load

    def detect(self, frame: np.ndarray, queue_size: Optional[int] = None) -> Tuple[bool, List[Tuple[int, int, int, int]]]:
        """
        Detect motion in frame using pre-allocated arrays.

        Args:
            frame: Input frame (BGR format)
            queue_size: Optional queue size for frame skip decision

        Returns:
            Tuple of (motion_detected, contours_bounding_boxes)
            where contours_bounding_boxes is list of (x, y, w, h) tuples
        """
        # Skip frame if under high load (CPU optimization)
        if self.should_skip_frame(queue_size):
            logger.debug("Skipping frame due to high load")
            return False, []
        # Convert to grayscale - reuse pre-allocated array
        cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY, dst=self._gray_frame)

        # Apply background subtraction - reuse pre-allocated mask
        self._fg_mask = self.bg_subtractor.apply(self._gray_frame, learningRate=-1)

        # Apply Gaussian blur to reduce noise - reuse pre-allocated array
        cv2.GaussianBlur(self._fg_mask, (5, 5), 0, dst=self._blur)

        # Threshold - reuse pre-allocated array
        cv2.threshold(self._blur, 127, 255, cv2.THRESH_BINARY, dst=self._thresh)

        # Find contours (this creates new arrays, but unavoidable with OpenCV API)
        contours, _ = cv2.findContours(
            self._thresh,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Filter contours by minimum area
        motion_detected = False
        bounding_boxes: List[Tuple[int, int, int, int]] = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self.config.min_area:
                motion_detected = True
                x, y, w, h = cv2.boundingRect(contour)
                bounding_boxes.append((x, y, w, h))

        return motion_detected, bounding_boxes

    def reset(self) -> None:
        """Reset background subtractor and clear pre-allocated arrays."""
        # Reset background model
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=self.config.sensitivity,
            detectShadows=True
        )

        # Clear pre-allocated arrays (reuse existing memory)
        self._gray_frame.fill(0)
        self._fg_mask.fill(0)
        self._thresh.fill(0)
        self._blur.fill(0)

        # Reset frame skip counters
        self._skip_count = 0
        self._total_frames = 0

        logger.info("MotionDetector reset - background model cleared")

    def get_debug_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Get debug visualization frame with motion detection overlay.

        Args:
            frame: Original input frame

        Returns:
            Frame with motion detection visualization
        """
        motion_detected, bounding_boxes = self.detect(frame)

        # Create copy for visualization (avoid modifying original)
        debug_frame = frame.copy()

        # Draw bounding boxes
        for x, y, w, h in bounding_boxes:
            cv2.rectangle(debug_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Add motion status text
        status = "MOTION DETECTED" if motion_detected else "No Motion"
        color = (0, 0, 255) if motion_detected else (0, 255, 0)
        cv2.putText(
            debug_frame,
            status,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            color,
            2
        )

        return debug_frame

    @property
    def memory_usage_bytes(self) -> int:
        """Calculate approximate memory usage of pre-allocated arrays."""
        total_bytes = (
            self._gray_frame.nbytes +
            self._fg_mask.nbytes +
            self._thresh.nbytes +
            self._blur.nbytes
        )
        return total_bytes

    @property
    def skip_stats(self) -> Tuple[int, int, float]:
        """
        Get frame skip statistics.

        Returns:
            Tuple of (total_frames, skipped_frames, skip_percentage)
        """
        skip_percentage = (self._skip_count / self._total_frames * 100) if self._total_frames > 0 else 0
        return self._total_frames, self._skip_count, skip_percentage
