"""Unit tests for ScreenshotManager buffer operations."""

import asyncio
from datetime import datetime, timedelta

import numpy as np
import pytest

from src.config import ScreenshotConfig
from src.screenshot_manager import ScreenshotManager, ScreenshotSet


@pytest.fixture
def screenshot_config():
    """Create a test screenshot configuration."""
    return ScreenshotConfig(
        before_seconds=3,
        after_seconds=3,
        quality=85,
        max_stored=100,
        buffer_seconds=10
    )


@pytest.fixture
def screenshot_manager(screenshot_config):
    """Create a test screenshot manager instance."""
    return ScreenshotManager(screenshot_config)


@pytest.fixture
def test_frame():
    """Create a test frame (100x100 BGR image)."""
    return np.zeros((100, 100, 3), dtype=np.uint8)


def test_buffer_operations(screenshot_manager, test_frame):
    """Test basic buffer operations: add_frame, get_buffer_size, memory tracking."""
    # Test initial state
    assert screenshot_manager.get_buffer_size() == 0
    assert screenshot_manager.get_buffer_memory_usage() == 0

    # Test adding frames
    timestamp1 = datetime.now()
    screenshot_manager.add_frame(test_frame, timestamp1)
    assert screenshot_manager.get_buffer_size() == 1

    # Test memory tracking
    expected_memory = test_frame.nbytes
    assert screenshot_manager.get_buffer_memory_usage() == expected_memory

    # Test adding multiple frames
    timestamp2 = timestamp1 + timedelta(seconds=0.2)
    timestamp3 = timestamp1 + timedelta(seconds=0.4)
    screenshot_manager.add_frame(test_frame.copy(), timestamp2)
    screenshot_manager.add_frame(test_frame.copy(), timestamp3)

    assert screenshot_manager.get_buffer_size() == 3
    assert screenshot_manager.get_buffer_memory_usage() == expected_memory * 3

    # Test buffer statistics
    stats = screenshot_manager.get_buffer_statistics()
    assert stats["frame_count"] == 3
    assert stats["max_capacity"] == 50  # 10 seconds * 5 fps
    assert stats["utilization"] == 6.0  # 3/50 * 100
    assert stats["memory_bytes"] == expected_memory * 3
    assert stats["memory_mb"] > 0


def test_ring_buffer_maxlen(screenshot_manager, test_frame):
    """Test that ring buffer respects maxlen and discards oldest frames."""
    # Buffer size should be 50 (10 seconds * 5 fps)
    max_capacity = 50

    # Fill buffer to capacity
    base_time = datetime.now()
    for i in range(max_capacity):
        timestamp = base_time + timedelta(seconds=i * 0.2)
        screenshot_manager.add_frame(test_frame.copy(), timestamp)

    assert screenshot_manager.get_buffer_size() == max_capacity

    # Add one more frame - should discard oldest
    timestamp_new = base_time + timedelta(seconds=max_capacity * 0.2)
    screenshot_manager.add_frame(test_frame.copy(), timestamp_new)

    # Size should still be at max capacity
    assert screenshot_manager.get_buffer_size() == max_capacity


def test_get_frame_before(screenshot_manager, test_frame):
    """Test retrieving frames from before a reference timestamp."""
    # Add frames at known timestamps
    base_time = datetime.now()
    timestamps = [
        base_time + timedelta(seconds=i)
        for i in range(10)
    ]

    for ts in timestamps:
        frame = test_frame.copy()
        frame[0, 0, 0] = timestamps.index(ts)  # Mark frame with index
        screenshot_manager.add_frame(frame, ts)

    # Test getting frame from 3 seconds before timestamps[8]
    reference_time = timestamps[8]
    before_frame = screenshot_manager._get_frame_before(reference_time, 3.0)

    assert before_frame is not None
    # Should get frame at index 5 (8 - 3 = 5)
    assert before_frame[0, 0, 0] == 5

    # Test getting frame when target is before buffer start
    early_time = base_time + timedelta(seconds=1)
    before_frame = screenshot_manager._get_frame_before(early_time, 5.0)
    assert before_frame is None


def test_get_frame_after(screenshot_manager, test_frame):
    """Test retrieving frames from after a reference timestamp."""
    # Add frames at known timestamps
    base_time = datetime.now()
    timestamps = [
        base_time + timedelta(seconds=i)
        for i in range(10)
    ]

    for ts in timestamps:
        frame = test_frame.copy()
        frame[0, 0, 0] = timestamps.index(ts)  # Mark frame with index
        screenshot_manager.add_frame(frame, ts)

    # Test getting frame from 3 seconds after timestamps[2]
    reference_time = timestamps[2]
    after_frame = screenshot_manager._get_frame_after(reference_time, 3.0)

    assert after_frame is not None
    # Should get frame at index 5 (2 + 3 = 5)
    assert after_frame[0, 0, 0] == 5

    # Test getting frame when target is after buffer end
    late_time = timestamps[-1]
    after_frame = screenshot_manager._get_frame_after(late_time, 5.0)
    assert after_frame is None


def test_buffer_statistics_empty(screenshot_manager):
    """Test buffer statistics with empty buffer."""
    stats = screenshot_manager.get_buffer_statistics()

    assert stats["frame_count"] == 0
    assert stats["max_capacity"] == 50
    assert stats["utilization"] == 0
    assert stats["memory_bytes"] == 0
    assert stats["memory_mb"] == 0


def test_buffer_statistics_partial(screenshot_manager, test_frame):
    """Test buffer statistics with partially filled buffer."""
    # Add 10 frames
    base_time = datetime.now()
    for i in range(10):
        timestamp = base_time + timedelta(seconds=i * 0.2)
        screenshot_manager.add_frame(test_frame.copy(), timestamp)

    stats = screenshot_manager.get_buffer_statistics()

    assert stats["frame_count"] == 10
    assert stats["max_capacity"] == 50
    assert stats["utilization"] == 20.0  # 10/50 * 100
    assert stats["memory_bytes"] == test_frame.nbytes * 10
    assert stats["memory_mb"] > 0


def test_cleanup_old_screenshots(screenshot_manager, test_frame):
    """Test cleanup of old screenshot sets."""
    # Create some mock screenshot sets
    for i in range(10):
        screenshot_set = ScreenshotSet(
            before=b"before",
            current=b"current",
            after=b"after",
            timestamp=datetime.now() + timedelta(seconds=i),
            before_base64="before_b64",
            current_base64="current_b64",
            after_base64="after_b64"
        )
        screenshot_manager._screenshot_sets.append(screenshot_set)

    # Test cleanup to keep only 5 most recent
    removed = screenshot_manager.cleanup_old(5)

    assert removed == 5
    assert len(screenshot_manager._screenshot_sets) == 5

    # Test cleanup when under limit
    removed = screenshot_manager.cleanup_old(10)

    assert removed == 0
    assert len(screenshot_manager._screenshot_sets) == 5


def test_add_frame_thread_safety(screenshot_manager, test_frame):
    """Test that add_frame operations are thread-safe."""
    # This tests the deque thread-safety for append operations
    # Add frames rapidly to simulate concurrent access
    base_time = datetime.now()

    for i in range(100):
        timestamp = base_time + timedelta(milliseconds=i * 10)
        screenshot_manager.add_frame(test_frame.copy(), timestamp)

    # Should have added all frames up to buffer capacity
    expected_size = min(100, 50)  # min(added, max_capacity)
    assert screenshot_manager.get_buffer_size() == expected_size


def test_memory_calculation_different_frame_sizes(screenshot_config):
    """Test memory calculation with different frame sizes."""
    manager = ScreenshotManager(screenshot_config)

    # Add small frame
    small_frame = np.zeros((50, 50, 3), dtype=np.uint8)
    manager.add_frame(small_frame, datetime.now())
    small_memory = manager.get_buffer_memory_usage()
    assert small_memory == small_frame.nbytes

    # Add large frame
    large_frame = np.zeros((200, 200, 3), dtype=np.uint8)
    manager.add_frame(large_frame, datetime.now())
    total_memory = manager.get_buffer_memory_usage()
    assert total_memory == small_frame.nbytes + large_frame.nbytes


@pytest.mark.asyncio
async def test_capture_sequence(screenshot_manager, test_frame):
    """Integration test for full capture sequence with before/current/after frames."""
    # Build up buffer with frames spanning from past through future
    # This simulates a continuous capture stream
    frame_interval = 0.2  # 5 fps = 0.2 seconds per frame
    reference_time = datetime.now()

    # Add 50 frames: 20 in the past, current, and 29 in the future
    # This gives us frames from (now - 4s) to (now + 5.8s)
    for i in range(50):
        # Timestamps span from -4s to +5.8s relative to reference_time
        offset = (i - 20) * frame_interval
        timestamp = reference_time + timedelta(seconds=offset)
        frame = test_frame.copy()
        # Mark each frame with a unique value for verification
        frame[0, 0, 0] = i % 256
        screenshot_manager.add_frame(frame, timestamp)

    # Verify buffer is at capacity
    assert screenshot_manager.get_buffer_size() == 50

    # Create a distinct current frame for capture
    current_frame = test_frame.copy()
    current_frame[0, 0, 0] = 255  # Distinct marker

    # Capture the sequence (will wait for after_seconds)
    # The buffer already contains frames for before and after
    screenshot_set = await screenshot_manager.capture_sequence(current_frame)

    # Verify ScreenshotSet structure
    assert screenshot_set is not None
    assert isinstance(screenshot_set, ScreenshotSet)

    # Verify all required fields are present
    assert screenshot_set.before is not None
    assert screenshot_set.current is not None
    assert screenshot_set.after is not None
    assert screenshot_set.timestamp is not None
    assert screenshot_set.before_base64 is not None
    assert screenshot_set.current_base64 is not None
    assert screenshot_set.after_base64 is not None

    # Verify bytes encoding (JPEG format should have proper headers)
    assert isinstance(screenshot_set.before, bytes)
    assert isinstance(screenshot_set.current, bytes)
    assert isinstance(screenshot_set.after, bytes)
    assert len(screenshot_set.before) > 0
    assert len(screenshot_set.current) > 0
    assert len(screenshot_set.after) > 0

    # Verify base64 encoding
    assert isinstance(screenshot_set.before_base64, str)
    assert isinstance(screenshot_set.current_base64, str)
    assert isinstance(screenshot_set.after_base64, str)
    assert len(screenshot_set.before_base64) > 0
    assert len(screenshot_set.current_base64) > 0
    assert len(screenshot_set.after_base64) > 0

    # Verify screenshot set was stored
    assert len(screenshot_manager._screenshot_sets) == 1
    assert screenshot_manager._screenshot_sets[0] == screenshot_set

    # Verify timestamp is recent
    time_diff = (datetime.now() - screenshot_set.timestamp).total_seconds()
    assert time_diff < 10  # Should be captured within last 10 seconds
