"""Performance metrics collection for Smart Motion Detector."""

import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import psutil

from src.logger import get_logger

# Initialize logger
logger = get_logger("metrics")


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot."""
    fps: float = 0.0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    inference_ms: float = 0.0
    queue_size: int = 0
    uptime_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MetricsCollector:
    """Collects system and application performance metrics."""

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self.process = psutil.Process(os.getpid())
        self.start_time = time.time()

        # Frame tracking for FPS calculation
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0.0

        # Inference timing
        self.last_inference_ms = 0.0

        # Queue size
        self.current_queue_size = 0

        logger.info("MetricsCollector initialized")

    def record_frame(self) -> None:
        """Record a processed frame for FPS calculation."""
        self.frame_count += 1

        # Update FPS every second
        current_time = time.time()
        elapsed = current_time - self.last_fps_time
        if elapsed >= 1.0:
            self.current_fps = self.frame_count / elapsed
            self.frame_count = 0
            self.last_fps_time = current_time

    def record_inference_time(self, duration_ms: float) -> None:
        """
        Record inference duration.

        Args:
            duration_ms: Inference duration in milliseconds
        """
        self.last_inference_ms = duration_ms

    def update_queue_size(self, size: int) -> None:
        """
        Update current queue size.

        Args:
            size: Current queue size
        """
        self.current_queue_size = size

    def get_memory_mb(self) -> float:
        """
        Get current memory usage in MB.

        Returns:
            Memory usage in megabytes
        """
        try:
            memory_info = self.process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Convert bytes to MB
        except Exception as e:
            logger.warning(f"Failed to get memory info: {e}")
            return 0.0

    def get_cpu_percent(self) -> float:
        """
        Get current CPU usage percentage.

        Returns:
            CPU usage percentage (0-100)
        """
        try:
            # Use interval=0.1 for quick non-blocking measurement
            return self.process.cpu_percent(interval=0.1)
        except Exception as e:
            logger.warning(f"Failed to get CPU percent: {e}")
            return 0.0

    def get_uptime_seconds(self) -> float:
        """
        Get application uptime in seconds.

        Returns:
            Uptime in seconds
        """
        return time.time() - self.start_time

    def collect(self) -> PerformanceMetrics:
        """
        Collect all current metrics.

        Returns:
            PerformanceMetrics with current values
        """
        return PerformanceMetrics(
            fps=self.current_fps,
            memory_mb=self.get_memory_mb(),
            cpu_percent=self.get_cpu_percent(),
            inference_ms=self.last_inference_ms,
            queue_size=self.current_queue_size,
            uptime_seconds=self.get_uptime_seconds()
        )

    def log_metrics(self) -> None:
        """Log current metrics at INFO level."""
        metrics = self.collect()
        logger.info(
            f"Metrics - FPS: {metrics.fps:.1f}, "
            f"Memory: {metrics.memory_mb:.1f}MB, "
            f"CPU: {metrics.cpu_percent:.1f}%, "
            f"Inference: {metrics.inference_ms:.1f}ms, "
            f"Queue: {metrics.queue_size}, "
            f"Uptime: {metrics.uptime_seconds:.0f}s"
        )
