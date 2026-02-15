"""
Video frame-by-frame analyzer service.
Detects duplicate frames, dropped frames, timing issues.
Used by API and can be called from analyze_video.py CLI.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def analyze_video(video_path: str) -> Optional[Dict[str, Any]]:
    """
    Analyze video frame by frame.
    Returns JSON-serializable dict with analysis results, or None if video cannot be opened.
    """
    path = Path(video_path)
    if not path.exists():
        logger.error("Video file not found: %s", video_path)
        return None

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        logger.error("Cannot open video: %s", video_path)
        return None

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps > 0 else 0.0

    frames: List[Dict[str, Any]] = []
    prev_frame = None
    duplicate_count = 0
    current_duplicate_seq: List[int] = []
    duplicate_sequences: List[List[int]] = []
    timestamp_jumps: List[Dict[str, Any]] = []

    frame_idx = 0
    prev_timestamp_ms = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        expected_timestamp_ms = (frame_idx / fps) * 1000 if fps > 0 else 0
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        is_duplicate = False
        diff_score = 0.0

        if prev_frame is not None:
            diff = cv2.absdiff(gray, prev_frame)
            mse = float(np.mean(diff ** 2))
            diff_score = mse

            if mse < 1.0:
                is_duplicate = True
                duplicate_count += 1
                current_duplicate_seq.append(frame_idx)
            else:
                if current_duplicate_seq:
                    duplicate_sequences.append(current_duplicate_seq.copy())
                    current_duplicate_seq = []

        timestamp_jump_data: Optional[Dict[str, Any]] = None
        if frame_idx > 0 and fps > 0:
            expected_gap = 1000 / fps
            actual_gap = timestamp_ms - prev_timestamp_ms
            if actual_gap > expected_gap * 2:
                timestamp_jump_data = {
                    "frame": frame_idx,
                    "from_ms": prev_timestamp_ms,
                    "to_ms": timestamp_ms,
                    "gap_ms": actual_gap,
                    "gap_seconds": actual_gap / 1000,
                    "expected_gap_ms": expected_gap,
                    "missing_frames_estimate": max(0, int(actual_gap / expected_gap) - 1),
                }
                timestamp_jumps.append(timestamp_jump_data)

        frames.append({
            "index": frame_idx,
            "timestamp_ms": timestamp_ms,
            "expected_timestamp_ms": expected_timestamp_ms,
            "timestamp_diff": timestamp_ms - expected_timestamp_ms,
            "is_duplicate": is_duplicate,
            "diff_score": diff_score,
        })

        prev_frame = gray.copy()
        prev_timestamp_ms = timestamp_ms
        frame_idx += 1

    if current_duplicate_seq:
        duplicate_sequences.append(current_duplicate_seq)

    cap.release()

    actual_duration = frames[-1]["timestamp_ms"] / 1000 if frames else 0.0

    non_dup_diffs = [
        f["diff_score"]
        for f in frames
        if not f["is_duplicate"] and f["diff_score"] > 0
    ]
    diff_stats: Dict[str, float] = {}
    if non_dup_diffs:
        diff_stats = {
            "average": float(np.mean(non_dup_diffs)),
            "std_dev": float(np.std(non_dup_diffs)),
            "min": float(min(non_dup_diffs)),
            "max": float(max(non_dup_diffs)),
        }

    total_missing = sum(j["missing_frames_estimate"] for j in timestamp_jumps)
    issues: List[str] = []
    if timestamp_jumps:
        issues.append(
            f"TIMESTAMP JUMPS: {len(timestamp_jumps)} jumps (missing frames: ~{total_missing})"
        )
    if duplicate_count > 0:
        pct = 100.0 * duplicate_count / frame_idx if frame_idx > 0 else 0
        issues.append(f"DUPLICATE FRAMES: {duplicate_count}/{frame_idx} ({pct:.1f}%)")

    return {
        "video_properties": {
            "width": width,
            "height": height,
            "fps": round(fps, 2),
            "frame_count": frame_count,
            "duration": round(duration, 2),
        },
        "analysis": {
            "total_frames": frame_idx,
            "calculated_duration": round(duration, 2),
            "actual_duration": round(actual_duration, 2),
            "duration_mismatch": round(abs(actual_duration - duration), 2),
            "duplicate_frames": duplicate_count,
            "duplicate_percentage": round(
                100.0 * duplicate_count / frame_idx, 1
            ) if frame_idx > 0 else 0,
            "duplicate_sequences": len(duplicate_sequences),
            "timestamp_jumps": len(timestamp_jumps),
            "estimated_missing_frames": total_missing,
        },
        "diff_stats": diff_stats,
        "timestamp_jumps_detail": timestamp_jumps[:20],
        "duplicate_sequences_preview": [
            {"start": s[0], "end": s[-1], "length": len(s)}
            for s in duplicate_sequences[:15]
        ],
        "ok": len(issues) == 0,
        "issues": issues,
    }
