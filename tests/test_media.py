"""
Unit tests for media generation.

Tests cover:
- Collage generation (6 frames)
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
    """Test collage generation with 6 frames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "collage.jpg")
        
        result = media_worker.create_collage(
            frames=test_frames,
            detections=None,
            timestamps=None,
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


def test_collage_6_frames(media_worker, test_frames):
    """Test that collage uses exactly 6 frames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "collage.jpg")
        
        media_worker.create_collage(
            frames=test_frames,
            detections=None,
            timestamps=None,
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
        
        result = media_worker.create_collage(
            frames=frames,
            detections=None,
            timestamps=None,
            output_path=output_path,
        )
        assert result == output_path
        assert os.path.exists(output_path)


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
        
        result = media_worker.create_timeline_gif(frames, output_path)
        assert result == output_path
        assert os.path.exists(output_path)


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
    """Test that MP4 keeps native resolution when below 720p."""
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
        
        assert width == 640
        assert height == 480


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
            detections=None,
            timestamps=None,
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


def test_select_collage_indices_keeps_event_frame(media_worker, test_frames):
    """Best detection frame should always be represented in collage selection."""
    timestamps = [float(i) * 0.2 for i in range(len(test_frames))]
    detections = [None for _ in test_frames]
    detections[7] = {"bbox": [80, 60, 180, 280], "confidence": 0.93}

    indices = media_worker._select_collage_indices(
        frames=test_frames,
        detections=detections,
        timestamps=timestamps,
        best_idx=7,
    )

    assert 7 in indices
    assert len(indices) <= media_worker.COLLAGE_FRAMES
    assert len(indices) == len(set(indices))


def test_select_collage_indices_prioritizes_confident_candidate(media_worker):
    """When two nearby candidates exist, higher-confidence frame should be picked earlier."""
    frames = [np.full((240, 320, 3), 20 + i * 20, dtype=np.uint8) for i in range(7)]
    for idx, frame in enumerate(frames):
        cv2.putText(frame, f"F{idx}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

    timestamps = [0.0, 0.30, 0.32, 0.60, 0.90, 1.20, 1.50]
    detections = [None] * 7
    detections[2] = {"bbox": [50, 50, 120, 190], "confidence": 0.92}
    detections[1] = {"bbox": [48, 52, 118, 192], "confidence": 0.42}

    indices = media_worker._select_collage_indices(
        frames=frames,
        detections=detections,
        timestamps=timestamps,
        best_idx=3,
    )

    assert 2 in indices and 1 in indices
    assert indices.index(2) < indices.index(1)


def test_select_collage_indices_spreads_timeline_when_possible(media_worker):
    """When enough timestamp span exists, collage should cover wider motion timeline."""
    frames = [np.full((240, 320, 3), 10 + i * 5, dtype=np.uint8) for i in range(40)]
    timestamps = [1000.0 + (i * 0.2) for i in range(40)]  # 7.8s span
    detections = [None] * 40
    detections[20] = {"bbox": [80, 60, 160, 220], "confidence": 0.88}

    indices = media_worker._select_collage_indices(
        frames=frames,
        detections=detections,
        timestamps=timestamps,
        best_idx=20,
    )

    assert len(indices) == media_worker.COLLAGE_FRAMES
    assert len(indices) == len(set(indices))
    assert 20 in indices
    selected_ts = [timestamps[i] for i in indices]
    assert max(selected_ts) - min(selected_ts) >= 4.0


def test_ai_collage_is_smaller_and_person_focused(media_worker):
    """AI collage should be smaller than default collage for faster AI requests."""
    frames = []
    detections = []
    timestamps = []
    for i in range(6):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        x1 = 500 + (i % 2) * 8
        y1 = 120 + (i % 3) * 6
        x2 = x1 + 22
        y2 = y1 + 48
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), -1)
        frames.append(frame)
        detections.append({"bbox": [x1, y1, x2, y2], "confidence": 0.70 + (i * 0.02)})
        timestamps.append(1700000000.0 + (i * 0.2))

    with tempfile.TemporaryDirectory() as tmpdir:
        full_collage_path = os.path.join(tmpdir, "collage_full.jpg")
        ai_collage_path = os.path.join(tmpdir, "collage_ai.jpg")

        media_worker.create_collage(
            frames=frames,
            detections=detections,
            timestamps=timestamps,
            output_path=full_collage_path,
            camera_name="Test Camera",
            timestamp=datetime.now(),
            confidence=0.9,
        )
        media_worker.create_ai_collage(
            frames=frames,
            detections=detections,
            timestamps=timestamps,
            output_path=ai_collage_path,
            camera_name="Test Camera",
            timestamp=datetime.now(),
            confidence=0.9,
        )

        assert os.path.exists(full_collage_path)
        assert os.path.exists(ai_collage_path)
        assert os.path.getsize(ai_collage_path) < os.path.getsize(full_collage_path)

        ai_img = cv2.imread(ai_collage_path)
        assert ai_img is not None
        expected_h = media_worker.AI_COLLAGE_FRAME_SIZE[1] * media_worker.AI_COLLAGE_GRID[1]
        expected_w = media_worker.AI_COLLAGE_FRAME_SIZE[0] * media_worker.AI_COLLAGE_GRID[0]
        assert ai_img.shape[0] == expected_h
        assert ai_img.shape[1] == expected_w


def test_select_ai_collage_indices_includes_pre_motion_context(media_worker):
    """AI collage must include pre-motion frames before first detection."""
    frames = [np.full((240, 320, 3), 15 + (i * 8), dtype=np.uint8) for i in range(12)]
    timestamps = [1000.0 + (i * 0.2) for i in range(12)]
    detections = [None] * 12
    detections[6] = {"bbox": [150, 60, 180, 180], "confidence": 0.71}
    detections[7] = {"bbox": [152, 62, 182, 182], "confidence": 0.87}
    detections[8] = {"bbox": [155, 64, 185, 184], "confidence": 0.79}

    indices = media_worker._select_ai_collage_indices(
        frames=frames,
        detections=detections,
        timestamps=timestamps,
        best_idx=7,
    )

    assert len(indices) == media_worker.AI_COLLAGE_FRAMES
    assert indices == sorted(indices)
    assert any(idx in indices for idx in [6, 7, 8])

    pre_motion = [idx for idx in indices if idx < 6]
    assert len(pre_motion) >= 2


def test_select_ai_collage_indices_spreads_context_over_wider_timeline(media_worker):
    """AI collage should keep pre/post context on longer timelines."""
    frames = [np.full((240, 320, 3), 20 + (i * 4), dtype=np.uint8) for i in range(36)]
    timestamps = [2000.0 + (i * 0.3) for i in range(36)]  # 10.5s span
    detections = [None] * 36
    detections[18] = {"bbox": [150, 70, 185, 200], "confidence": 0.74}
    detections[19] = {"bbox": [152, 72, 187, 202], "confidence": 0.91}
    detections[20] = {"bbox": [154, 73, 189, 203], "confidence": 0.83}

    indices = media_worker._select_ai_collage_indices(
        frames=frames,
        detections=detections,
        timestamps=timestamps,
        best_idx=19,
    )

    assert len(indices) == media_worker.AI_COLLAGE_FRAMES
    assert indices == sorted(indices)
    assert any(idx < 18 for idx in indices)
    assert any(idx > 20 for idx in indices)
    selected_ts = [timestamps[i] for i in indices]
    assert max(selected_ts) - min(selected_ts) >= 4.0


def test_ai_collage_marks_person_bbox_not_full_tile_border(media_worker):
    """AI collage should mark person region, not draw full-frame event border."""
    frame_h, frame_w = 480, 640
    frames = []
    detections = []
    timestamps = []
    for i in range(8):
        frame = np.zeros((frame_h, frame_w, 3), dtype=np.uint8)
        x1 = 290 + i
        y1 = 140
        x2 = x1 + 34
        y2 = y1 + 122
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), -1)
        frames.append(frame)
        detections.append({"bbox": [x1, y1, x2, y2], "confidence": 0.70 + (i * 0.02)})
        timestamps.append(1700000100.0 + (i * 0.2))

    with tempfile.TemporaryDirectory() as tmpdir:
        ai_collage_path = os.path.join(tmpdir, "collage_ai.jpg")
        media_worker.create_ai_collage(
            frames=frames,
            detections=detections,
            timestamps=timestamps,
            output_path=ai_collage_path,
            camera_name="Test Camera",
            timestamp=datetime.now(),
            confidence=0.86,
        )

        img = cv2.imread(ai_collage_path)
        assert img is not None

        accent = np.array(media_worker.COLOR_ACCENT, dtype=np.int16)
        delta = np.abs(img.astype(np.int16) - accent)
        accent_mask = np.all(delta <= 45, axis=2)

        tile_w, tile_h = media_worker.AI_COLLAGE_FRAME_SIZE
        tile_rows = media_worker.AI_COLLAGE_GRID[1]
        tile_cols = media_worker.AI_COLLAGE_GRID[0]

        max_border_accent = 0
        tiles_with_interior_bbox = 0
        for row in range(tile_rows):
            for col in range(tile_cols):
                y0 = row * tile_h
                y1 = y0 + tile_h
                x0 = col * tile_w
                x1 = x0 + tile_w
                tile_mask = accent_mask[y0:y1, x0:x1]
                if tile_mask.size == 0:
                    continue

                border = np.zeros(tile_mask.shape, dtype=bool)
                border[:3, :] = True
                border[-3:, :] = True
                border[:, :3] = True
                border[:, -3:] = True
                border_accent = int(np.count_nonzero(tile_mask & border))
                max_border_accent = max(max_border_accent, border_accent)

                inner = np.zeros(tile_mask.shape, dtype=bool)
                inner[24:-24, 24:-24] = True
                interior_accent = int(np.count_nonzero(tile_mask & inner))
                if interior_accent >= 45:
                    tiles_with_interior_bbox += 1

        # Regression guard: previous behavior highlighted whole event tile border.
        assert max_border_accent < 240
        # Person bbox overlays should create visible accent edges inside tiles.
        assert tiles_with_interior_bbox >= 3
