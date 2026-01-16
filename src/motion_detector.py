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


def map_sensitivity_to_params(sensitivity: int) -> tuple[int, int]:
    """
    Map sensitivity level (1-10) to motion detection parameters.

    The sensitivity scale works as follows:
    - 1 = Most sensitive: Detects subtle movements, small objects
    - 5 = Balanced: Good for general use cases
    - 10 = Least sensitive: Only detects significant movements, large objects

    Parameters mapped:
    - varThreshold: MOG2 background subtraction threshold
      Lower values = more pixels classified as foreground = more sensitive
      Range: 8 (sensitivity 1) to 50 (sensitivity 10)

    - min_area: Minimum contour area in pixels to trigger motion
      Lower values = smaller objects detected = more sensitive
      Range: 100 (sensitivity 1) to 2000 (sensitivity 10)

    Args:
        sensitivity: Sensitivity level from 1 (most sensitive) to 10 (least sensitive)

    Returns:
        Tuple of (var_threshold, min_area)

    Raises:
        ValueError: If sensitivity is not in range 1-10
    """
    if not 1 <= sensitivity <= 10:
        raise ValueError(f"Sensitivity must be between 1 and 10, got {sensitivity}")

    # Map sensitivity (1-10) to varThreshold (8-50)
    # Linear interpolation: threshold = 8 + (sensitivity - 1) * (50 - 8) / 9
    var_threshold = int(8 + (sensitivity - 1) * 4.67)

    # Map sensitivity (1-10) to min_area (100-2000)
    # Linear interpolation: min_area = 100 + (sensitivity - 1) * (2000 - 100) / 9
    min_area = int(100 + (sensitivity - 1) * 211.11)

    return var_threshold, min_area


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
        # Map sensitivity to detection parameters
        var_threshold, mapped_min_area = map_sensitivity_to_params(
            self.motion_config.sensitivity
        )

        # Override min_area if explicitly configured (not default)
        if self.motion_config.min_area != 500:
            # User has explicitly set min_area, use it instead of mapped value
            mapped_min_area = self.motion_config.min_area

        # Update config with mapped value for use in detection
        self.motion_config.min_area = mapped_min_area

        # Initialize BackgroundSubtractorMOG2 with sensitivity-based parameters
        # history: Number of frames for background model (500 frames ~= 100s at 5fps)
        # varThreshold: Threshold for pixel-model match (mapped from sensitivity)
        # detectShadows: Detect and mark shadows (reduces false positives)
        self._background_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=var_threshold,
            detectShadows=True
        )
        self._callbacks: List[Callable[[np.ndarray, List], None]] = []

        # Frame storage
        self._current_frame: Optional[np.ndarray] = None

        # Cooldown tracking
        self._last_motion_time: float = 0.0

        logger.info(
            f"MotionDetector initialized - "
            f"sensitivity={self.motion_config.sensitivity}, "
            f"varThreshold={var_threshold}, "
            f"min_area={mapped_min_area}"
        )

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

    def on_motion(self, callback: Callable[[np.ndarray, List], None]) -> None:
        """
        Register a callback to be invoked when motion is detected.

        The callback will be called with two arguments:
        - frame: The current frame as numpy array (BGR format)
        - contours: List of detected motion contours

        Callbacks are stored in a thread-safe manner and will be invoked
        sequentially when motion is detected.

        Args:
            callback: Function to call when motion is detected.
                     Signature: callback(frame: np.ndarray, contours: List) -> None

        Example:
            def handle_motion(frame, contours):
                print(f"Motion detected! {len(contours)} contours found")

            detector.on_motion(handle_motion)
        """
        with self._lock:
            self._callbacks.append(callback)
            logger.debug(f"Registered motion callback: {callback.__name__}")

    @property
    def is_connected(self) -> bool:
        """
        Check if camera is connected.

        Returns:
            True if connected, False otherwise
        """
        return self.capture is not None and self.capture.isOpened()

    def _detect_motion(self, frame: np.ndarray) -> List[np.ndarray]:
        """
        Detect motion in a frame using background subtraction and contour detection.

        Applies the following pipeline:
        1. Background subtraction using MOG2 to get foreground mask
        2. Morphological operations (erosion + dilation) to reduce noise
        3. Contour detection using cv2.findContours
        4. Area-based filtering using min_area from config

        Args:
            frame: Input frame as numpy array (BGR format)

        Returns:
            List of contours that exceed the minimum area threshold.
            Each contour is a numpy array of points.
        """
        # Apply background subtraction to get foreground mask
        # The mask will have white pixels (255) for foreground and black (0) for background
        fg_mask = self._background_subtractor.apply(frame)

        # Apply morphological operations to reduce noise
        # Erosion removes small white noise
        # Dilation restores the object size after erosion
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.erode(fg_mask, kernel, iterations=1)
        fg_mask = cv2.dilate(fg_mask, kernel, iterations=2)

        # Find contours in the foreground mask
        # RETR_EXTERNAL: only retrieve external contours (ignore holes)
        # CHAIN_APPROX_SIMPLE: compress horizontal/vertical/diagonal segments
        contours, _ = cv2.findContours(
            fg_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Filter contours by minimum area
        motion_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self.motion_config.min_area:
                motion_contours.append(contour)

        if motion_contours:
            total_area = sum(cv2.contourArea(c) for c in motion_contours)
            logger.debug(
                f"Motion detected: {len(motion_contours)} contours, "
                f"total area: {total_area:.0f} pixels"
            )

        return motion_contours

    def _capture_loop(self) -> None:
        """
        Continuous frame capture loop running in separate thread.

        This method runs in a background thread and performs the following:
        1. Reads frames from VideoCapture at configured FPS
        2. Stores current frame in thread-safe manner
        3. Performs motion detection on each frame
        4. Invokes callbacks when motion is detected
        5. Handles errors and reconnection attempts

        The loop continues until _running flag is set to False.
        """
        logger.info("Frame capture loop started")

        # Calculate frame delay based on configured FPS
        # frame_delay is in seconds (e.g., 5 FPS = 0.2 seconds between frames)
        frame_delay = 1.0 / self.camera_config.fps if self.camera_config.fps > 0 else 0.2

        while self._running:
            try:
                # Check if camera is connected
                if not self.is_connected:
                    logger.warning("Camera disconnected, attempting reconnection...")
                    if not self.connect():
                        logger.error("Reconnection failed, waiting before retry...")
                        time.sleep(5.0)  # Wait 5 seconds before retry
                        continue

                # Read frame from camera
                ret, frame = self.capture.read()

                if not ret or frame is None:
                    logger.warning("Failed to read frame from camera")
                    time.sleep(frame_delay)
                    continue

                # Store current frame (thread-safe)
                with self._lock:
                    self._current_frame = frame.copy()

                # Detect motion in frame
                motion_contours = self._detect_motion(frame)

                # If motion detected, invoke callbacks (with cooldown)
                if motion_contours:
                    current_time = time.time()
                    time_since_last_motion = current_time - self._last_motion_time

                    # Only invoke callbacks if cooldown period has passed
                    if time_since_last_motion >= self.motion_config.cooldown_seconds:
                        logger.debug(
                            f"Cooldown passed ({time_since_last_motion:.1f}s >= "
                            f"{self.motion_config.cooldown_seconds}s), invoking callbacks"
                        )

                        # Invoke all registered callbacks with thread safety
                        with self._lock:
                            callbacks = self._callbacks.copy()

                        for callback in callbacks:
                            try:
                                callback(frame.copy(), motion_contours)
                            except Exception as e:
                                logger.error(
                                    f"Error in motion callback {callback.__name__}: {e}"
                                )

                        # Update last motion time after invoking callbacks
                        self._last_motion_time = current_time
                    else:
                        logger.debug(
                            f"Motion detected but cooldown active "
                            f"({time_since_last_motion:.1f}s < "
                            f"{self.motion_config.cooldown_seconds}s)"
                        )

                # Sleep to maintain configured FPS
                time.sleep(frame_delay)

            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                time.sleep(frame_delay)

        logger.info("Frame capture loop stopped")
