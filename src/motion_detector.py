"""Motion detection with optimized numpy array reuse."""

import logging
import queue
import threading
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

        # Threading for camera capture
        self._frame_queue: queue.Queue = queue.Queue(maxsize=30)
        self._capture_thread: Optional[threading.Thread] = None
        self._capture_running = False
        self._camera: Optional[cv2.VideoCapture] = None

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

    def start_capture_thread(self, camera_index: int = 0) -> bool:
        """
        Start background thread for camera capture.

        Args:
            camera_index: Camera device index (default 0)

        Returns:
            True if thread started successfully, False otherwise
        """
        if self._capture_running:
            logger.warning("Capture thread already running")
            return False

        try:
            # Initialize camera
            self._camera = cv2.VideoCapture(camera_index)
            if not self._camera.isOpened():
                logger.error(f"Failed to open camera {camera_index}")
                return False

            # Start capture thread
            self._capture_running = True
            self._capture_thread = threading.Thread(
                target=self._capture_worker,
                daemon=True,
                name="CameraCapture"
            )
            self._capture_thread.start()

            logger.info(f"Camera capture thread started (camera_index={camera_index})")
            return True

        except Exception as e:
            logger.error(f"Failed to start capture thread: {e}")
            self._capture_running = False
            if self._camera:
                self._camera.release()
                self._camera = None
            return False

    def stop_capture_thread(self, timeout: float = 5.0) -> None:
        """
        Stop background camera capture thread.

        Args:
            timeout: Maximum seconds to wait for thread to stop
        """
        if not self._capture_running:
            logger.debug("Capture thread not running")
            return

        logger.info("Stopping camera capture thread...")
        self._capture_running = False

        # Wait for thread to finish
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=timeout)
            if self._capture_thread.is_alive():
                logger.warning("Capture thread did not stop within timeout")

        # Release camera
        if self._camera:
            self._camera.release()
            self._camera = None

        # Clear queue
        while not self._frame_queue.empty():
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                break

        logger.info("Camera capture thread stopped")

    def _capture_worker(self) -> None:
        """
        Worker function for capture thread.

        Continuously reads frames from camera and puts them in queue.
        """
        if not self._camera:
            logger.error("Camera not initialized in capture worker")
            return

        logger.debug("Capture worker thread started")

        while self._capture_running:
            try:
                ret, frame = self._camera.read()

                if not ret:
                    logger.error("Failed to read frame from camera")
                    break

                # Put frame in queue (non-blocking, drop if full)
                try:
                    self._frame_queue.put_nowait(frame)
                except queue.Full:
                    # Drop oldest frame and add new one
                    try:
                        self._frame_queue.get_nowait()
                        self._frame_queue.put_nowait(frame)
                    except (queue.Empty, queue.Full):
                        pass

            except Exception as e:
                logger.error(f"Error in capture worker: {e}")
                break

        logger.debug("Capture worker thread finished")

    def get_frame(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """
        Get latest frame from capture queue.

        Args:
            timeout: Maximum seconds to wait for frame

        Returns:
            Frame from queue, or None if timeout or error
        """
        try:
            return self._frame_queue.get(timeout=timeout)
        except queue.Empty:
            logger.debug("Frame queue empty (timeout)")
            return None
        except Exception as e:
            logger.error(f"Error getting frame from queue: {e}")
            return None

    @property
    def queue_size(self) -> int:
        """Get current size of frame queue."""
        return self._frame_queue.qsize()

    @property
    def is_capturing(self) -> bool:
        """Check if capture thread is running."""
        return self._capture_running
