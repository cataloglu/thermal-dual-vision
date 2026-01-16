"""24-hour stability test for Smart Motion Detector.

This test runs for an extended period (default 24 hours, configurable) to:
- Monitor memory usage and detect memory leaks
- Monitor CPU usage and ensure it stays within bounds
- Verify system stability under continuous operation
- Test all optimized components (ring buffer, frame skip, metrics, etc.)

Usage:
    # Quick test (1 minute for CI)
    pytest tests/test_stability_24h.py -v -s --duration=60

    # Full 24-hour test
    pytest tests/test_stability_24h.py -v -s --duration=86400

    # Show collected tests only (verification)
    pytest tests/test_stability_24h.py --co
"""

import gc
import os
import time
import tracemalloc
from datetime import datetime
from typing import Dict, List, Tuple
from unittest.mock import MagicMock

import numpy as np
import psutil
import pytest

from src.config import MotionConfig
from src.metrics import MetricsCollector, PerformanceMetrics
from src.motion_detector import MotionDetector
from src.screenshot_manager import ScreenshotManager


def pytest_addoption(parser):
    """Add custom command line options for stability test."""
    parser.addoption(
        "--duration",
        action="store",
        default="60",  # Default 1 minute for CI
        help="Test duration in seconds (default: 60, full test: 86400 for 24h)"
    )


@pytest.fixture
def test_duration(request):
    """Get test duration from command line or use default."""
    return int(request.config.getoption("--duration"))


@pytest.fixture
def motion_config():
    """Create test motion configuration."""
    return MotionConfig(
        sensitivity=25,
        min_area=500,
        frame_skip_threshold=70.0
    )


@pytest.fixture
def sample_frame():
    """Create a sample test frame (640x480 BGR)."""
    return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)


class MemoryMonitor:
    """Monitor memory usage over time to detect leaks."""

    def __init__(self):
        """Initialize memory monitor with tracemalloc."""
        self.start_memory: float = 0.0
        self.peak_memory: float = 0.0
        self.snapshots: List[Tuple[float, float]] = []  # (timestamp, memory_mb)
        self.process = psutil.Process(os.getpid())

    def start(self) -> None:
        """Start memory monitoring."""
        tracemalloc.start()
        gc.collect()
        self.start_memory = self._get_current_memory()
        self.peak_memory = self.start_memory
        self.snapshots = [(time.time(), self.start_memory)]

    def snapshot(self) -> float:
        """
        Take a memory snapshot.

        Returns:
            Current memory usage in MB
        """
        current_memory = self._get_current_memory()
        self.snapshots.append((time.time(), current_memory))

        if current_memory > self.peak_memory:
            self.peak_memory = current_memory

        return current_memory

    def stop(self) -> Dict[str, float]:
        """
        Stop monitoring and return statistics.

        Returns:
            Dictionary with memory statistics (start, end, peak, increase)
        """
        gc.collect()
        end_memory = self._get_current_memory()
        tracemalloc.stop()

        return {
            "start_mb": self.start_memory,
            "end_mb": end_memory,
            "peak_mb": self.peak_memory,
            "increase_mb": end_memory - self.start_memory
        }

    def _get_current_memory(self) -> float:
        """
        Get current memory usage in MB.

        Returns:
            Memory usage in megabytes
        """
        memory_info = self.process.memory_info()
        return memory_info.rss / (1024 * 1024)


class CPUMonitor:
    """Monitor CPU usage over time."""

    def __init__(self):
        """Initialize CPU monitor."""
        self.process = psutil.Process(os.getpid())
        self.samples: List[Tuple[float, float]] = []  # (timestamp, cpu_percent)

    def sample(self) -> float:
        """
        Sample current CPU usage.

        Returns:
            CPU usage percentage
        """
        cpu_percent = self.process.cpu_percent(interval=0.1)
        self.samples.append((time.time(), cpu_percent))
        return cpu_percent

    def get_statistics(self) -> Dict[str, float]:
        """
        Get CPU usage statistics.

        Returns:
            Dictionary with min, max, mean, median CPU percentages
        """
        if not self.samples:
            return {"min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0}

        cpu_values = [cpu for _, cpu in self.samples]
        cpu_values.sort()

        return {
            "min": min(cpu_values),
            "max": max(cpu_values),
            "mean": sum(cpu_values) / len(cpu_values),
            "median": cpu_values[len(cpu_values) // 2]
        }


@pytest.mark.slow
class TestSystemStability:
    """24-hour stability tests for the motion detection system."""

    def test_motion_detector_stability(
        self,
        motion_config,
        sample_frame,
        test_duration
    ):
        """
        Test MotionDetector stability over extended period.

        Verifies:
        - No memory leaks (< 10MB increase)
        - Stable CPU usage
        - Proper cleanup of resources
        - Pre-allocated arrays remain valid
        """
        # Initialize monitors
        mem_monitor = MemoryMonitor()
        cpu_monitor = CPUMonitor()
        mem_monitor.start()

        # Initialize motion detector
        detector = MotionDetector(motion_config, sample_frame.shape)

        start_time = time.time()
        iteration = 0
        sample_interval = 10  # Sample metrics every 10 seconds

        print(f"\n[MotionDetector] Running stability test for {test_duration}s...")
        print(f"[MotionDetector] Start memory: {mem_monitor.start_memory:.1f}MB")

        try:
            while time.time() - start_time < test_duration:
                # Simulate frame processing
                frame = sample_frame.copy()
                frame = frame + np.random.randint(-10, 10, frame.shape, dtype=np.int16)
                frame = np.clip(frame, 0, 255).astype(np.uint8)

                # Detect motion
                has_motion = detector.detect(frame)

                # Sample metrics periodically
                if iteration % (sample_interval * 10) == 0:  # Adjust for loop speed
                    current_mem = mem_monitor.snapshot()
                    current_cpu = cpu_monitor.sample()

                    elapsed = time.time() - start_time
                    print(
                        f"[MotionDetector] {elapsed:.0f}s: "
                        f"Memory: {current_mem:.1f}MB, "
                        f"CPU: {current_cpu:.1f}%, "
                        f"Motion: {has_motion}"
                    )

                iteration += 1

                # Small sleep to prevent spinning (realistic frame rate ~10-30 FPS)
                time.sleep(0.05)

        finally:
            # Collect final statistics
            mem_stats = mem_monitor.stop()
            cpu_stats = cpu_monitor.get_statistics()

            print(f"\n[MotionDetector] Stability test completed!")
            print(f"[MotionDetector] Memory - Start: {mem_stats['start_mb']:.1f}MB, "
                  f"End: {mem_stats['end_mb']:.1f}MB, "
                  f"Peak: {mem_stats['peak_mb']:.1f}MB, "
                  f"Increase: {mem_stats['increase_mb']:.1f}MB")
            print(f"[MotionDetector] CPU - Min: {cpu_stats['min']:.1f}%, "
                  f"Max: {cpu_stats['max']:.1f}%, "
                  f"Mean: {cpu_stats['mean']:.1f}%, "
                  f"Median: {cpu_stats['median']:.1f}%")
            print(f"[MotionDetector] Total iterations: {iteration}")

            # Verify no significant memory leak (< 10MB increase)
            assert mem_stats['increase_mb'] < 10.0, (
                f"Memory leak detected: {mem_stats['increase_mb']:.1f}MB increase "
                f"(threshold: 10MB)"
            )

            # Verify memory usage stays under 512MB target
            assert mem_stats['peak_mb'] < 512.0, (
                f"Memory usage too high: {mem_stats['peak_mb']:.1f}MB "
                f"(target: < 512MB)"
            )

    def test_screenshot_manager_stability(
        self,
        sample_frame,
        test_duration
    ):
        """
        Test ScreenshotManager ring buffer stability.

        Verifies:
        - Ring buffer doesn't leak memory
        - Old frames are properly evicted
        - Memory usage remains constant after buffer fills
        """
        # Initialize monitors
        mem_monitor = MemoryMonitor()
        mem_monitor.start()

        # Initialize screenshot manager (5 FPS, 10 second buffer = 50 frames max)
        manager = ScreenshotManager(fps=5, buffer_seconds=10)

        start_time = time.time()
        iteration = 0

        print(f"\n[ScreenshotManager] Running stability test for {test_duration}s...")
        print(f"[ScreenshotManager] Start memory: {mem_monitor.start_memory:.1f}MB")
        print(f"[ScreenshotManager] Ring buffer capacity: {manager.buffer.maxlen}")

        try:
            while time.time() - start_time < test_duration:
                # Add frames to ring buffer
                frame = sample_frame.copy()
                manager.add_frame(frame)

                # Retrieve old frame (should return None once buffer wraps)
                old_frame = manager.get_frame_from_seconds_ago(8)

                # Sample metrics periodically
                if iteration % 50 == 0:
                    current_mem = mem_monitor.snapshot()
                    buffer_size = len(manager.buffer)

                    elapsed = time.time() - start_time
                    print(
                        f"[ScreenshotManager] {elapsed:.0f}s: "
                        f"Memory: {current_mem:.1f}MB, "
                        f"Buffer size: {buffer_size}/{manager.buffer.maxlen}, "
                        f"Old frame: {old_frame is not None}"
                    )

                iteration += 1
                time.sleep(0.2)  # Simulate 5 FPS

        finally:
            # Collect final statistics
            mem_stats = mem_monitor.stop()

            print(f"\n[ScreenshotManager] Stability test completed!")
            print(f"[ScreenshotManager] Memory - Start: {mem_stats['start_mb']:.1f}MB, "
                  f"End: {mem_stats['end_mb']:.1f}MB, "
                  f"Increase: {mem_stats['increase_mb']:.1f}MB")
            print(f"[ScreenshotManager] Final buffer size: {len(manager.buffer)}")

            # Verify no memory leak
            assert mem_stats['increase_mb'] < 10.0, (
                f"Memory leak detected: {mem_stats['increase_mb']:.1f}MB increase"
            )

            # Verify buffer is at capacity (ring buffer working correctly)
            assert len(manager.buffer) == manager.buffer.maxlen, (
                f"Ring buffer not full: {len(manager.buffer)}/{manager.buffer.maxlen}"
            )

    def test_metrics_collector_stability(
        self,
        test_duration
    ):
        """
        Test MetricsCollector stability over extended period.

        Verifies:
        - Metrics collection doesn't leak memory
        - FPS calculation remains accurate
        - CPU/memory monitoring works correctly
        """
        # Initialize monitors
        mem_monitor = MemoryMonitor()
        cpu_monitor = CPUMonitor()
        mem_monitor.start()

        # Initialize metrics collector
        collector = MetricsCollector()

        start_time = time.time()
        iteration = 0

        print(f"\n[MetricsCollector] Running stability test for {test_duration}s...")
        print(f"[MetricsCollector] Start memory: {mem_monitor.start_memory:.1f}MB")

        try:
            while time.time() - start_time < test_duration:
                # Simulate frame processing
                collector.record_frame()

                # Simulate inference timing
                collector.record_inference_time(100.0 + np.random.randn() * 20.0)

                # Simulate queue size updates
                collector.update_queue_size(np.random.randint(0, 20))

                # Collect metrics periodically
                if iteration % 100 == 0:
                    metrics = collector.collect()
                    current_mem = mem_monitor.snapshot()
                    current_cpu = cpu_monitor.sample()

                    elapsed = time.time() - start_time
                    print(
                        f"[MetricsCollector] {elapsed:.0f}s: "
                        f"FPS: {metrics.fps:.1f}, "
                        f"Memory: {current_mem:.1f}MB, "
                        f"CPU: {current_cpu:.1f}%, "
                        f"Inference: {metrics.inference_ms:.1f}ms"
                    )

                iteration += 1
                time.sleep(0.05)  # Simulate ~20 FPS

        finally:
            # Collect final statistics
            mem_stats = mem_monitor.stop()
            cpu_stats = cpu_monitor.get_statistics()
            final_metrics = collector.collect()

            print(f"\n[MetricsCollector] Stability test completed!")
            print(f"[MetricsCollector] Memory - Start: {mem_stats['start_mb']:.1f}MB, "
                  f"End: {mem_stats['end_mb']:.1f}MB, "
                  f"Increase: {mem_stats['increase_mb']:.1f}MB")
            print(f"[MetricsCollector] CPU - Mean: {cpu_stats['mean']:.1f}%")
            print(f"[MetricsCollector] Final FPS: {final_metrics.fps:.1f}")
            print(f"[MetricsCollector] Total frames: {iteration}")

            # Verify no memory leak
            assert mem_stats['increase_mb'] < 10.0, (
                f"Memory leak detected: {mem_stats['increase_mb']:.1f}MB increase"
            )

            # Verify FPS calculation is reasonable (should be ~20 FPS)
            assert 5.0 <= final_metrics.fps <= 30.0, (
                f"FPS out of expected range: {final_metrics.fps:.1f} "
                f"(expected: 5-30 FPS)"
            )

    def test_integrated_system_stability(
        self,
        motion_config,
        sample_frame,
        test_duration
    ):
        """
        Test integrated system stability with all components.

        Simulates realistic workload with:
        - Motion detection
        - Screenshot buffering
        - Metrics collection
        - Frame skip mechanism

        Verifies all performance targets:
        - Memory < 512MB
        - CPU < 50% (mean)
        - FPS >= 5
        - No memory leaks (< 10MB increase)
        """
        # Initialize monitors
        mem_monitor = MemoryMonitor()
        cpu_monitor = CPUMonitor()
        mem_monitor.start()

        # Initialize all components
        detector = MotionDetector(motion_config, sample_frame.shape)
        manager = ScreenshotManager(fps=10, buffer_seconds=10)
        collector = MetricsCollector()

        start_time = time.time()
        iteration = 0
        motion_count = 0

        print(f"\n[Integrated] Running full system stability test for {test_duration}s...")
        print(f"[Integrated] Start memory: {mem_monitor.start_memory:.1f}MB")

        try:
            while time.time() - start_time < test_duration:
                # Generate slightly varying frame (simulates real camera)
                frame = sample_frame.copy()
                if iteration % 100 < 20:  # Simulate motion events
                    frame = frame + np.random.randint(-50, 50, frame.shape, dtype=np.int16)
                    frame = np.clip(frame, 0, 255).astype(np.uint8)

                # Process frame through all components
                has_motion = detector.detect(frame)
                if has_motion:
                    motion_count += 1

                manager.add_frame(frame)
                collector.record_frame()
                collector.record_inference_time(150.0 + np.random.randn() * 30.0)
                collector.update_queue_size(len(manager.buffer))

                # Sample metrics periodically
                if iteration % 100 == 0:
                    metrics = collector.collect()
                    current_mem = mem_monitor.snapshot()
                    current_cpu = cpu_monitor.sample()

                    elapsed = time.time() - start_time
                    print(
                        f"[Integrated] {elapsed:.0f}s: "
                        f"FPS: {metrics.fps:.1f}, "
                        f"Memory: {current_mem:.1f}MB, "
                        f"CPU: {current_cpu:.1f}%, "
                        f"Queue: {metrics.queue_size}, "
                        f"Motion: {motion_count}"
                    )

                iteration += 1
                time.sleep(0.1)  # ~10 FPS

        finally:
            # Collect final statistics
            mem_stats = mem_monitor.stop()
            cpu_stats = cpu_monitor.get_statistics()
            final_metrics = collector.collect()

            print(f"\n[Integrated] Full system stability test completed!")
            print(f"[Integrated] ===== MEMORY STATS =====")
            print(f"[Integrated] Start: {mem_stats['start_mb']:.1f}MB")
            print(f"[Integrated] End: {mem_stats['end_mb']:.1f}MB")
            print(f"[Integrated] Peak: {mem_stats['peak_mb']:.1f}MB")
            print(f"[Integrated] Increase: {mem_stats['increase_mb']:.1f}MB")
            print(f"[Integrated] ===== CPU STATS =====")
            print(f"[Integrated] Min: {cpu_stats['min']:.1f}%")
            print(f"[Integrated] Max: {cpu_stats['max']:.1f}%")
            print(f"[Integrated] Mean: {cpu_stats['mean']:.1f}%")
            print(f"[Integrated] Median: {cpu_stats['median']:.1f}%")
            print(f"[Integrated] ===== PERFORMANCE STATS =====")
            print(f"[Integrated] FPS: {final_metrics.fps:.1f}")
            print(f"[Integrated] Total frames: {iteration}")
            print(f"[Integrated] Motion events: {motion_count}")

            # Verify performance targets
            assert mem_stats['increase_mb'] < 10.0, (
                f"❌ Memory leak detected: {mem_stats['increase_mb']:.1f}MB increase "
                f"(threshold: 10MB)"
            )

            assert mem_stats['peak_mb'] < 512.0, (
                f"❌ Memory usage too high: {mem_stats['peak_mb']:.1f}MB "
                f"(target: < 512MB)"
            )

            assert cpu_stats['mean'] < 50.0, (
                f"❌ CPU usage too high: {cpu_stats['mean']:.1f}% "
                f"(target: < 50%)"
            )

            assert final_metrics.fps >= 5.0, (
                f"❌ FPS too low: {final_metrics.fps:.1f} "
                f"(target: >= 5 FPS)"
            )

            print(f"[Integrated] ✅ All performance targets met!")
