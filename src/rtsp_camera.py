"""RTSP camera handler for Smart Motion Detector."""

import asyncio
import threading
import time
from typing import Optional
import cv2
import numpy as np
from src.config import CameraConfig
from src.logger import get_logger
from src.utils import mask_url

# Optional import for CPU/RAM monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None  # type: ignore

logger = get_logger("rtsp_camera")


class RTSPCamera:
    """RTSP camera handler with async frame reading."""

    def __init__(self, config: CameraConfig) -> None:
        """
        Initialize RTSP camera handler.

        Args:
            config: Camera configuration with RTSP URL
        """
        self.config = config
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._read_thread: Optional[threading.Thread] = None
        self._fps = config.fps
        self._frame_interval = 1.0 / self._fps if self._fps > 0 else 0.1
        self._use_dummy = not config.url or config.url.startswith(("dummy:", "test:", "mock:"))
        self._dummy_frame_counter = 0
        self._reconnect_enabled = True
        self._max_reconnect_attempts = 10  # Maximum reconnect attempts before giving up
        self._reconnect_delay = 2.0  # Initial delay in seconds
        self._max_reconnect_delay = 60.0  # Maximum delay in seconds
        self._reconnect_backoff = 2.0  # Backoff multiplier
        
        # CPU/RAM monitoring
        self._monitoring_enabled = PSUTIL_AVAILABLE
        self._monitoring_interval = 60.0  # Check every 60 seconds
        self._last_monitoring_time = 0.0
        self._cpu_threshold = 90.0  # Warning if CPU > 90%
        self._ram_threshold = 90.0  # Warning if RAM > 90%

    async def connect(self) -> None:
        """
        Connect to RTSP stream or start dummy frame generator.

        Opens RTSP connection and starts background thread for frame reading.
        If no RTSP URL is provided, generates dummy test frames.
        """
        if self._running:
            logger.warning("Camera already connected")
            return

        if self._use_dummy:
            logger.info("No RTSP URL provided, using dummy test video generator")
            # Generate initial dummy frame
            dummy_frame = self._generate_dummy_frame()
            with self._frame_lock:
                self._latest_frame = dummy_frame
            
            self._running = True
            self._read_thread = threading.Thread(target=self._read_dummy_frames, daemon=True)
            self._read_thread.start()
            logger.info("Dummy camera started successfully")
            return

        masked_url = mask_url(self.config.url)
        logger.info(f"Connecting to RTSP stream: {masked_url}")
        
        # Open RTSP stream with optimized settings
        self._cap = cv2.VideoCapture(
            self.config.url,
            cv2.CAP_FFMPEG
        )
        
        # Set buffer size to 1 to minimize latency
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not self._cap.isOpened():
            masked_url = mask_url(self.config.url)
            raise RuntimeError(f"Failed to open RTSP stream: {masked_url}")

        # Read first frame to verify connection
        ret, frame = self._cap.read()
        if not ret or frame is None:
            self._cap.release()
            self._cap = None
            raise RuntimeError("Failed to read initial frame from RTSP stream")

        logger.info("RTSP stream connected successfully")
        
        self._running = True
        self._read_thread = threading.Thread(target=self._read_frames, daemon=True)
        self._read_thread.start()

    async def disconnect(self) -> None:
        """
        Disconnect from RTSP stream.

        Stops background thread and releases camera resources.
        """
        if not self._running:
            return

        logger.info("Disconnecting from RTSP stream")
        self._running = False
        self._reconnect_enabled = False  # Disable reconnection during shutdown

        if self._read_thread:
            self._read_thread.join(timeout=5.0)
            if self._read_thread.is_alive():
                logger.warning("Read thread did not stop within timeout, continuing shutdown")

        if self._cap:
            self._cap.release()
            self._cap = None

        with self._frame_lock:
            self._latest_frame = None

        logger.info("RTSP stream disconnected")

    def _check_system_resources(self) -> None:
        """
        Check CPU and RAM usage and log warnings if thresholds are exceeded.
        
        This is called periodically during frame reading to monitor system health.
        """
        if not self._monitoring_enabled or not PSUTIL_AVAILABLE:
            return
        
        try:
            current_time = time.time()
            # Check monitoring interval
            if current_time - self._last_monitoring_time < self._monitoring_interval:
                return
            
            self._last_monitoring_time = current_time
            
            # Get CPU usage (non-blocking, interval=0)
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Get RAM usage
            memory = psutil.virtual_memory()
            ram_percent = memory.percent
            
            # Log resource usage periodically (every 10 monitoring cycles = ~10 minutes)
            if int(current_time) % 600 < self._monitoring_interval:
                logger.debug(f"System resources - CPU: {cpu_percent:.1f}%, RAM: {ram_percent:.1f}%")
            
            # Warn if thresholds exceeded
            if cpu_percent > self._cpu_threshold:
                logger.warning(
                    f"High CPU usage detected: {cpu_percent:.1f}% (threshold: {self._cpu_threshold}%)"
                )
            
            if ram_percent > self._ram_threshold:
                logger.warning(
                    f"High RAM usage detected: {ram_percent:.1f}% (threshold: {self._ram_threshold}%)"
                )
                
        except Exception as e:
            # Don't let monitoring errors break frame reading
            logger.debug(f"Error checking system resources: {e}")

    def _generate_dummy_frame(self) -> np.ndarray:
        """Generate a dummy test frame with moving elements."""
        width, height = self.config.resolution
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Background gradient
        for y in range(height):
            intensity = int(30 + (y / height) * 50)
            frame[y, :] = [intensity, intensity, intensity]
        
        # Moving circle
        center_x = int(width // 2 + np.cos(self._dummy_frame_counter * 0.05) * (width // 4))
        center_y = int(height // 2 + np.sin(self._dummy_frame_counter * 0.03) * (height // 4))
        cv2.circle(frame, (center_x, center_y), 50, (0, 255, 0), -1)
        
        # Text with frame counter
        text = f"DUMMY CAMERA - Frame {self._dummy_frame_counter}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
        text_x = (width - text_size[0]) // 2
        text_y = 50
        cv2.putText(frame, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness)
        
        # Timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (20, height - 30), font, 0.7, (200, 200, 200), 1)
        
        self._dummy_frame_counter += 1
        return frame

    def _read_dummy_frames(self) -> None:
        """Background thread function to continuously generate dummy frames."""
        while self._running:
            try:
                dummy_frame = self._generate_dummy_frame()
                with self._frame_lock:
                    self._latest_frame = dummy_frame.copy()
                
                # Control frame rate
                time.sleep(self._frame_interval)

            except Exception as e:
                logger.error(f"Error generating dummy frame: {e}")
                if self._running:
                    time.sleep(1.0)

    def _reconnect_stream(self) -> bool:
        """
        Attempt to reconnect to RTSP stream.
        
        Returns:
            True if reconnected successfully, False otherwise
        """
        if not self._reconnect_enabled or self._use_dummy:
            return False
        
        masked_url = mask_url(self.config.url)
        logger.warning(f"Attempting to reconnect to RTSP stream: {masked_url}")
        
        # Close existing connection
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        
        # Attempt to reconnect with exponential backoff
        delay = self._reconnect_delay
        for attempt in range(1, self._max_reconnect_attempts + 1):
            if not self._running:
                return False
            
            try:
                # Wait before retry (except first attempt)
                if attempt > 1:
                    logger.info(f"Reconnect attempt {attempt}/{self._max_reconnect_attempts} in {delay:.1f}s...")
                    time.sleep(delay)
                    delay = min(delay * self._reconnect_backoff, self._max_reconnect_delay)
                
                # Open new connection
                self._cap = cv2.VideoCapture(
                    self.config.url,
                    cv2.CAP_FFMPEG
                )
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                if not self._cap.isOpened():
                    logger.warning(f"Reconnect attempt {attempt}: Failed to open RTSP stream")
                    if self._cap:
                        self._cap.release()
                        self._cap = None
                    continue
                
                # Try to read first frame to verify connection
                ret, frame = self._cap.read()
                if ret and frame is not None:
                    with self._frame_lock:
                        self._latest_frame = frame.copy()
                    masked_url = mask_url(self.config.url)
                    logger.info(f"Successfully reconnected to RTSP stream: {masked_url} (attempt {attempt})")
                    return True
                else:
                    logger.warning(f"Reconnect attempt {attempt}: Failed to read initial frame")
                    if self._cap:
                        self._cap.release()
                        self._cap = None
                    
            except Exception as e:
                logger.error(f"Reconnect attempt {attempt} error: {e}")
                if self._cap:
                    try:
                        self._cap.release()
                    except Exception:
                        pass
                    self._cap = None
        
        # All reconnection attempts failed
        masked_url = mask_url(self.config.url)
        logger.error(f"Failed to reconnect to RTSP stream after {self._max_reconnect_attempts} attempts: {masked_url}")
        return False

    def _read_frames(self) -> None:
        """Background thread function to continuously read frames with auto-reconnect."""
        consecutive_failures = 0
        max_consecutive_failures = 5  # Trigger reconnect after N consecutive failures
        
        while self._running:
            try:
                # Check if we need to reconnect
                if self._cap is None or not self._cap.isOpened():
                    if not self._reconnect_stream():
                        # Reconnection failed, wait before trying again
                        logger.error("Stream reconnection failed, will retry later")
                        time.sleep(5.0)
                    continue
                
                # Periodic CPU/RAM monitoring
                self._check_system_resources()
                
                # Try to read frame
                ret, frame = self._cap.read()
                if ret and frame is not None:
                    consecutive_failures = 0  # Reset failure counter
                    with self._frame_lock:
                        self._latest_frame = frame.copy()
                    
                    # Control frame rate
                    time.sleep(self._frame_interval)
                else:
                    consecutive_failures += 1
                    logger.warning(f"Failed to read frame from RTSP stream (failure {consecutive_failures}/{max_consecutive_failures})")
                    
                    # If we've had too many consecutive failures, trigger reconnection
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning("Too many consecutive failures, triggering reconnection")
                        if not self._reconnect_stream():
                            # Reconnection failed, wait before trying again
                            time.sleep(5.0)
                        consecutive_failures = 0
                    else:
                        # Wait before retrying
                        time.sleep(1.0)
                    continue

            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Error reading frame: {e} (failure {consecutive_failures}/{max_consecutive_failures})")
                
                if self._running:
                    # If we've had too many consecutive failures, trigger reconnection
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning("Too many consecutive failures, triggering reconnection")
                        if not self._reconnect_stream():
                            # Reconnection failed, wait before trying again
                            time.sleep(5.0)
                        consecutive_failures = 0
                    else:
                        time.sleep(1.0)

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Get the latest frame from the camera.

        Returns:
            Latest frame as numpy array, or None if no frame available
        """
        with self._frame_lock:
            if self._latest_frame is not None:
                return self._latest_frame.copy()
            return None

    def is_connected(self) -> bool:
        """Check if camera is connected."""
        if self._use_dummy:
            return self._running
        return self._running and self._cap is not None and self._cap.isOpened()
