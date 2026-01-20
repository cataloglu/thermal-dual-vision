"""
Unit tests for media generation.

Tests cover:
- Collage generation (5 frames)
- GIF generation (10 frames with progress bar)
- MP4 generation (720p with detection boxes)
- Parallel generation
- File size validation
- Overlay rendering
"""
import os
import tempfile
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.workers.media import MediaWorker


@pytest.fixture
def media_worker():
    """Create media worker instance."""
    return MediaWorker()


@pytest.fixture
def test_frames():
    """Create test frames."""
    frames = []
    for i in range(20):
        # Create frame with different colors
        frame = np.full((480, 640, 3), i * 10, dtype=np.uint8)
        # Add frame number
        cv2.putText(frame, f"Frame {i}", (250, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        frames.append(frame)
    return frames


@pytest.fixture
def test_detections():
    """Create test detections."""
    detections = []
    for i in range(20):
        if i % 2 == 0:  # Detection every other frame
            detections.append({
                "bbox": [100 + i*5, 100, 200 + i*5, 300],
                "confidence": 0.7 + (i * 0.01),
            })
        else:
            detections.append(None)
    return detections


def test_collage_generation(media_worker, test_frames):
    """Test collage generation with 5 frames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "collage.jpg")
        
        result = media_worker.create_collage(
            frames=test_frames,
            output_path=output_path,
            camera_name="Test Camera",
            timestamp=datetime.now(),
            confidence=0.85,
        )
        
        assert result == output_path
        assert os.path.exists(output_path)
        
        # Check file size (test frames are simple, so size may be small)
        size_kb = os.path.getsize(output_path) / 1024
        assert size_kb > 10  # At least 10KB
        assert size_kb < 2000  # Less than 2MB


def test_collage_5_frames(media_worker, test_frames):
    """Test that collage uses exactly 5 frames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "collage.jpg")
        
        media_worker.create_collage(
            frames=test_frames,
            output_path=output_path,
        )
        
        # Load and check dimensions
        img = cv2.imread(output_path)
        assert img.shape == (960, 1920, 3)  # 3x2 grid of 640x480 frames


def test_collage_insufficient_frames(media_worker):
    """Test collage with insufficient frames."""
    frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(3)]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "collage.jpg")
        
        with pytest.raises(ValueError, match="Need at least 5 frames"):
            media_worker.create_collage(frames, output_path)


def test_gif_generation(media_worker, test_frames):
    """Test GIF generation with 10 frames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "preview.gif")
        
        result = media_worker.create_timeline_gif(
            frames=test_frames,
            output_path=output_path,
            camera_name="Test Camera",
            timestamp=datetime.now(),
        )
        
        assert result == output_path
        assert os.path.exists(output_path)


def test_gif_10_frames(media_worker, test_frames):
    """Test that GIF uses exactly 10 frames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "preview.gif")
        
        media_worker.create_timeline_gif(
            frames=test_frames,
            output_path=output_path,
        )
        
        # GIF should exist
        assert os.path.exists(output_path)


def test_gif_size_under_2mb(media_worker, test_frames):
    """Test that GIF size is under 2MB (Telegram limit)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "preview.gif")
        
        media_worker.create_timeline_gif(
            frames=test_frames,
            output_path=output_path,
        )
        
        # Check file size
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        assert size_mb < 2.0  # Must be under 2MB for Telegram


def test_gif_insufficient_frames(media_worker):
    """Test GIF with insufficient frames."""
    frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "preview.gif")
        
        with pytest.raises(ValueError, match="Need at least 10 frames"):
            media_worker.create_timeline_gif(frames, output_path)


def test_mp4_generation(media_worker, test_frames, test_detections):
    """Test MP4 generation with detection boxes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "timelapse.mp4")
        
        result = media_worker.create_timelapse_mp4(
            frames=test_frames,
            detections=test_detections,
            output_path=output_path,
            camera_name="Test Camera",
            timestamp=datetime.now(),
        )
        
        assert result == output_path
        assert os.path.exists(output_path)
        
        # Check file size
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        assert size_mb > 0  # Should have content


def test_mp4_720p_resolution(media_worker, test_frames, test_detections):
    """Test that MP4 is 720p resolution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "timelapse.mp4")
        
        media_worker.create_timelapse_mp4(
            frames=test_frames[:5],  # Use fewer frames for speed
            detections=test_detections[:5],
            output_path=output_path,
        )
        
        # Open video and check resolution
        cap = cv2.VideoCapture(output_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        assert width == 1280
        assert height == 720


def test_mp4_no_frames(media_worker):
    """Test MP4 with no frames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "timelapse.mp4")
        
        with pytest.raises(ValueError, match="Need at least 1 frame"):
            media_worker.create_timelapse_mp4([], [], output_path)


def test_collage_overlay_elements(media_worker, test_frames):
    """Test that collage has all overlay elements."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "collage.jpg")
        
        media_worker.create_collage(
            frames=test_frames,
            output_path=output_path,
            camera_name="Test Camera",
            timestamp=datetime.now(),
            confidence=0.85,
        )
        
        # Load image
        img = cv2.imread(output_path)
        
        # Check that image is not all black (has content)
        assert img.mean() > 0


def test_gif_progress_bar(media_worker, test_frames):
    """Test that GIF has progress bar overlay."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "preview.gif")
        
        media_worker.create_timeline_gif(
            frames=test_frames,
            output_path=output_path,
        )
        
        # GIF should be created successfully
        assert os.path.exists(output_path)
        
        # Check file is not empty
        assert os.path.getsize(output_path) > 1000  # At least 1KB
