"""Motion detection module for Smart Motion Detector."""

import threading
import time
from typing import Callable, List, Optional

import cv2
import numpy as np

from src.config import CameraConfig, MotionConfig
from src.logger import get_logger

logger = get_logger("motion_detector")

# Connection timeout constants (in milliseconds)
OPEN_TIMEOUT_MS = 10000  # 10 seconds to open connection
READ_TIMEOUT_MS = 5000   # 5 seconds to read frame


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
        # Initialize BackgroundSubtractorMOG2 with sensible defaults
        # history: Number of frames for background model (500 frames ~= 100s at 5fps)
        # varThreshold: Threshold for pixel-model match (lower = more sensitive)
        # detectShadows: Detect and mark shadows (reduces false positives)
        self._background_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=16,
            detectShadows=True
        )
        self._callbacks: List[Callable[[np.ndarray, List], None]] = []

        # Frame storage
        self._current_frame: Optional[np.ndarray] = None

        logger.info("MotionDetector initialized")

    def _attempt_connection(self) -> bool:
        """
        Attempt a single connection to the camera.

        Internal method that performs one connection attempt without retry logic.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Close existing connection if any
            if self.capture is not None:
                self._disconnect()

            # Create VideoCapture instance
            self.capture = cv2.VideoCapture(self.camera_config.url)

            # Set timeout properties
            self.capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, OPEN_TIMEOUT_MS)
            self.capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, READ_TIMEOUT_MS)

            # Attempt to open the stream
            if not self.capture.isOpened():
                logger.warning(f"Failed to open camera stream: {self.camera_config.url}")
                self._disconnect()
                return False

            # Validate connection by reading a test frame
            ret, frame = self.capture.read()
            if not ret or frame is None:
                logger.warning("Failed to read test frame from camera")
                self._disconnect()
                return False

            # Log success with frame info
            height, width = frame.shape[:2]
            logger.info(
                f"Camera connected successfully - Resolution: {width}x{height}"
            )

            return True

        except Exception as e:
            logger.warning(f"Connection attempt failed: {e}")
            self._disconnect()
            return False

    def connect(self) -> bool:
        """
        Connect to RTSP camera stream with retry mechanism.

        Establishes connection to the camera using cv2.VideoCapture with
        timeout handling and exponential backoff retry logic. Validates
        connection by attempting to read a test frame.

        Uses configurable retry parameters:
        - retry_max_attempts: Maximum number of connection attempts
        - retry_initial_delay: Initial delay between attempts (seconds)
        - retry_backoff: Multiplier for delay after each attempt

        Returns:
            True if connection successful, False otherwise

        Raises:
            ValueError: If camera URL is not configured
        """
        if not self.camera_config.url:
            logger.error("Camera URL is not configured")
            raise ValueError("Camera URL is required")

        logger.info(f"Connecting to camera: {self.camera_config.url}")

        max_attempts = self.camera_config.retry_max_attempts
        current_delay = self.camera_config.retry_initial_delay
        backoff = self.camera_config.retry_backoff

        for attempt in range(1, max_attempts + 1):
            logger.info(f"Connection attempt {attempt}/{max_attempts}")

            if self._attempt_connection():
                return True

            # If not the last attempt, wait before retrying
            if attempt < max_attempts:
                logger.info(f"Retrying in {current_delay:.1f} seconds...")
                time.sleep(current_delay)
                current_delay *= backoff

        logger.error(
            f"Failed to connect to camera after {max_attempts} attempts"
        )
        return False

    def _disconnect(self) -> None:
        """
        Disconnect from camera and release resources.

        Internal method to cleanup VideoCapture instance safely.
        """
        if self.capture is not None:
            try:
                self.capture.release()
                logger.debug("Camera connection released")
            except Exception as e:
                logger.warning(f"Error releasing camera: {e}")
            finally:
                self.capture = None

    def disconnect(self) -> None:
        """
        Disconnect from camera stream.

        Public method to safely disconnect from camera and release
        all resources.
        """
        logger.info("Disconnecting from camera")
        self._disconnect()

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

    @property
    def is_connected(self) -> bool:
        """
        Check if camera is connected.

        Returns:
            True if connected, False otherwise
        """
        return self.capture is not None and self.capture.isOpened()
