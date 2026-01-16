"""Motion detection module for Smart Motion Detector."""

import threading
from typing import Callable, List, Optional

import cv2
import numpy as np

from src.config import CameraConfig, MotionConfig
from src.logger import get_logger

logger = get_logger("motion_detector")


class MotionDetector:
    """
    Motion detector using OpenCV background subtraction.

    Captures video from RTSP stream and detects motion using
    background subtraction algorithm. Runs in a separate thread
    for non-blocking operation.
    """

    def __init__(self, camera_config: CameraConfig, motion_config: MotionConfig):
        """
        Initialize motion detector.

        Args:
            camera_config: Camera configuration
            motion_config: Motion detection configuration
        """
        self.camera_config = camera_config
        self.motion_config = motion_config

        # VideoCapture instance
        self.capture: Optional[cv2.VideoCapture] = None

        # Thread management
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Motion detection
        self._background_subtractor = None
        self._callbacks: List[Callable[[np.ndarray, List], None]] = []

        # Frame storage
        self._current_frame: Optional[np.ndarray] = None

        logger.info("MotionDetector initialized")

    @property
    def is_running(self) -> bool:
        """
        Check if motion detector is running.

        Returns:
            True if running, False otherwise
        """
        return self._running

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Get the current frame.

        Returns:
            Current frame as numpy array, or None if not available
        """
        with self._lock:
            if self._current_frame is not None:
                return self._current_frame.copy()
            return None
