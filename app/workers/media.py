"""
Media generation worker for Smart Motion Detector v2.

This worker handles creation of event media files:
- Collage (5 frame grid)
- Timeline GIF (10 frames with progress bar)
- Timelapse MP4 (720p with detection boxes)

Better than Scrypted: More frames, higher quality, detection boxes!
"""
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

import cv2
import imageio
import numpy as np

from app.utils.paths import DATA_DIR

logger = logging.getLogger(__name__)


class MediaWorker:
    """Worker for event media generation."""
    
    # Media configuration
    MEDIA_DIR = DATA_DIR / "media"
    
    # Collage settings
    COLLAGE_FRAMES = 5
    COLLAGE_FRAME_SIZE = (640, 480)
    COLLAGE_GRID = (3, 2)  # 3 columns, 2 rows
    COLLAGE_QUALITY = 90
    
    # GIF settings
    GIF_FRAMES = 10  # Scrypted: 5-8, ours: 10 (smoother!)
    GIF_SIZE = (640, 480)
    GIF_DURATION = 0.5  # seconds per frame
    GIF_MAX_SIZE_MB = 2.0  # Telegram limit
    GIF_QUALITY = 85
    
    # MP4 settings
    MP4_SIZE = (1280, 720)  # Scrypted: 480p, ours: 720p!
    MP4_FPS = 15
    MP4_CODEC = 'mp4v'
    
    # Overlay colors (BGR format)
    COLOR_WHITE = (255, 255, 255)
    COLOR_ACCENT = (255, 140, 91)  # #5B8CFF in BGR
    
    def __init__(self):
        """Initialize media worker."""
        # Ensure media directory exists
        self.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("MediaWorker initialized")
    
    def create_collage(
        self,
        frames: List[np.ndarray],
        detections: Optional[List[Optional[Dict]]],
        timestamps: Optional[List[float]],
        output_path: str,
        camera_name: str = "Camera",
        timestamp: Optional[datetime] = None,
        confidence: float = 0.0,
    ) -> str:
        """
        Create 5-frame collage grid.
        
        Layout: 3x2 grid (5 frames + 1 empty)
        Resolution: 1920x960 (640x480 per frame)
        
        Args:
            frames: List of frames
            detections: Optional list of detections per frame
            timestamps: Optional list of timestamps per frame (epoch seconds)
            output_path: Output JPEG path
            camera_name: Camera name for overlay
            timestamp: Event timestamp
            confidence: Detection confidence
            
        Returns:
            Output path
            
        Raises:
            ValueError: If less than 5 frames provided
        """
        if len(frames) == 0:
            raise ValueError("Need at least 1 frame for collage")

        def _unique_preserve(items: List[int]) -> List[int]:
            seen = set()
            unique = []
            for item in items:
                if item in seen:
                    continue
                seen.add(item)
                unique.append(item)
            return unique

        def _pick_closest_index(unused: set, target_idx: int) -> Optional[int]:
            if not unused:
                return None
            return min(unused, key=lambda i: abs(i - target_idx))

        total = len(frames)
        best_idx = total // 2
        if detections:
            best_conf = -1.0
            for idx, det in enumerate(detections):
                if not det:
                    continue
                conf = float(det.get("confidence", 0.0))
                if conf >= best_conf:
                    best_conf = conf
                    best_idx = idx

        if timestamps and len(timestamps) == total:
            center_ts = timestamps[best_idx]
            target_times = [
                center_ts - 2.0,
                center_ts - 1.0,
                center_ts,
                center_ts + 1.0,
                center_ts + 2.0,
            ]
            unused = set(range(total))
            indices = []
            for slot, target in enumerate(target_times):
                if not unused:
                    break
                if slot == 2 and best_idx in unused:
                    closest = best_idx
                else:
                    closest = min(unused, key=lambda i: abs(timestamps[i] - target))
                indices.append(closest)
                unused.remove(closest)
        else:
            unused = set(range(total))
            target_indices = [best_idx - 2, best_idx - 1, best_idx, best_idx + 1, best_idx + 2]
            indices = []
            for slot, target in enumerate(target_indices):
                if not unused:
                    break
                if slot == 2 and best_idx in unused:
                    closest = best_idx
                else:
                    closest = _pick_closest_index(unused, target)
                if closest is None:
                    break
                indices.append(closest)
                unused.remove(closest)
        
        def _draw_badge(img: np.ndarray, text: str) -> None:
            (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
            pad = 10
            x, y = 10, 10
            cv2.rectangle(
                img,
                (x, y),
                (x + w + pad * 2, y + h + pad * 2),
                self.COLOR_ACCENT,
                -1,
            )
            cv2.putText(
                img,
                text,
                (x + pad, y + h + pad),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                self.COLOR_WHITE,
                2,
            )

        # Select 5 evenly distributed frames
        selected = [frames[i] for i in indices]
        
        # Resize all frames
        resized = []
        for idx, frame in enumerate(selected):
            img = cv2.resize(frame, self.COLLAGE_FRAME_SIZE)
            
            # Add frame number badge (1-5)
            _draw_badge(img, str(idx + 1))
            
            # Add timestamp on first frame
            if idx == 0 and timestamp:
                cv2.putText(
                    img,
                    timestamp.strftime("%H:%M:%S"),
                    (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    self.COLOR_WHITE,
                    2
                )
            
            # Add confidence on event frame (middle frame #3)
            if idx == 2:
                cv2.putText(
                    img,
                    f"{confidence:.0%}",
                    (10, 460),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    self.COLOR_ACCENT,
                    2
                )
            
            resized.append(img)
        
        # Create grid
        rows = []
        for row_idx in range(self.COLLAGE_GRID[1]):
            row_frames = []
            for col_idx in range(self.COLLAGE_GRID[0]):
                frame_idx = row_idx * self.COLLAGE_GRID[0] + col_idx
                if frame_idx < len(resized):
                    row_frames.append(resized[frame_idx])
                else:
                    # Empty frame (black)
                    row_frames.append(np.zeros((*self.COLLAGE_FRAME_SIZE[::-1], 3), dtype=np.uint8))
            rows.append(np.hstack(row_frames))
        
        collage = np.vstack(rows)
        
        # Add camera name (top right)
        cv2.putText(
            collage,
            camera_name,
            (1700, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            self.COLOR_WHITE,
            2
        )
        
        # Save with high quality
        cv2.imwrite(output_path, collage, [cv2.IMWRITE_JPEG_QUALITY, self.COLLAGE_QUALITY])
        
        logger.info(f"Collage created: {output_path}")
        return output_path
    
    def create_timeline_gif(
        self,
        frames: List[np.ndarray],
        output_path: str,
        camera_name: str = "Camera",
        timestamp: Optional[datetime] = None,
    ) -> str:
        """
        Create timeline animation GIF with progress bar.
        
        Better than Scrypted: 10 frames (vs 5-8), progress bar!
        
        Args:
            frames: List of frames
            output_path: Output GIF path
            camera_name: Camera name for overlay
            timestamp: Event start timestamp
            
        Returns:
            Output path
            
        Raises:
            ValueError: If less than 10 frames provided
        """
        if len(frames) == 0:
            raise ValueError("Need at least 1 frame for GIF")

        frame_count = min(self.GIF_FRAMES, len(frames))
        
        # Select 10 evenly distributed frames
        total = len(frames)
        if frame_count == 1:
            indices = [0]
        else:
            indices = [int(i * (total - 1) / (frame_count - 1)) for i in range(frame_count)]
        selected = [frames[i] for i in indices]
        
        # Process frames
        processed = []
        for idx, frame in enumerate(selected):
            # Resize
            img = cv2.resize(frame, self.GIF_SIZE)

            # Add frame number badge
            badge_text = str(idx + 1)
            (w, h), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            pad = 8
            x, y = 10, 10
            cv2.rectangle(
                img,
                (x, y),
                (x + w + pad * 2, y + h + pad * 2),
                self.COLOR_ACCENT,
                -1,
            )
            cv2.putText(
                img,
                badge_text,
                (x + pad, y + h + pad),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                self.COLOR_WHITE,
                2,
            )
            
            # Add timestamp
            if timestamp:
                frame_time = timestamp + timedelta(seconds=idx * self.GIF_DURATION)
                cv2.putText(
                    img,
                    frame_time.strftime("%H:%M:%S"),
                    (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    self.COLOR_WHITE,
                    2
                )
            
            # Add camera name
            cv2.putText(
                img,
                camera_name,
                (480, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                self.COLOR_WHITE,
                2
            )
            
            # Add progress bar (timeline indicator) - Scrypted doesn't have this!
            progress = idx / max(frame_count - 1, 1)
            bar_width = int(self.GIF_SIZE[0] * progress)
            cv2.rectangle(
                img,
                (0, self.GIF_SIZE[1] - 10),
                (bar_width, self.GIF_SIZE[1]),
                self.COLOR_ACCENT,
                -1
            )
            
            # Convert BGR to RGB for imageio
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            processed.append(img_rgb)
        
        # Create GIF with optimization
        imageio.mimsave(
            output_path,
            processed,
            duration=self.GIF_DURATION,
            loop=0,  # Infinite loop
        )
        
        # Check size and reduce quality if needed
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        if size_mb > self.GIF_MAX_SIZE_MB:
            logger.warning(f"GIF size {size_mb:.2f}MB > {self.GIF_MAX_SIZE_MB}MB, reducing quality")
            # Re-create with lower quality (resize to smaller)
            processed_small = [cv2.resize(img, (480, 360)) for img in processed]
            imageio.mimsave(
                output_path,
                processed_small,
                duration=self.GIF_DURATION,
                loop=0,
            )
        
        logger.info(f"Timeline GIF created: {output_path} ({size_mb:.2f}MB)")
        return output_path
    
    def create_timelapse_mp4(
        self,
        frames: List[np.ndarray],
        detections: List[Optional[Dict]],
        output_path: str,
        camera_name: str = "Camera",
        timestamp: Optional[datetime] = None,
    ) -> str:
        """
        Create timelapse MP4 with detection boxes.
        
        Better than Scrypted: 720p (vs 480p), detection boxes!
        
        Args:
            frames: List of frames
            detections: List of detection dicts (one per frame)
            output_path: Output MP4 path
            camera_name: Camera name for overlay
            timestamp: Event start timestamp
            
        Returns:
            Output path
        """
        if len(frames) == 0:
            raise ValueError("Need at least 1 frame for MP4")
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*self.MP4_CODEC)
        out = cv2.VideoWriter(output_path, fourcc, self.MP4_FPS, self.MP4_SIZE)
        
        try:
            for idx, frame in enumerate(frames):
                # Resize to 720p
                img = cv2.resize(frame, self.MP4_SIZE)
                
                # Draw detection box if available
                if idx < len(detections) and detections[idx]:
                    detection = detections[idx]
                    x1, y1, x2, y2 = detection['bbox']
                    
                    # Scale bbox to 720p
                    scale_x = self.MP4_SIZE[0] / frame.shape[1]
                    scale_y = self.MP4_SIZE[1] / frame.shape[0]
                    x1_scaled = int(x1 * scale_x)
                    y1_scaled = int(y1 * scale_y)
                    x2_scaled = int(x2 * scale_x)
                    y2_scaled = int(y2 * scale_y)
                    
                    # Draw box
                    cv2.rectangle(
                        img,
                        (x1_scaled, y1_scaled),
                        (x2_scaled, y2_scaled),
                        self.COLOR_ACCENT,
                        3
                    )
                    
                    # Confidence label
                    label = f"Person {detection['confidence']:.0%}"
                    cv2.putText(
                        img,
                        label,
                        (x1_scaled, y1_scaled - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        self.COLOR_ACCENT,
                        2
                    )
                
                # Timestamp overlay
                if timestamp:
                    frame_time = timestamp + timedelta(seconds=idx / self.MP4_FPS)
                    cv2.putText(
                        img,
                        frame_time.strftime("%H:%M:%S.%f")[:-3],
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        self.COLOR_WHITE,
                        2
                    )
                
                # Camera name
                cv2.putText(
                    img,
                    camera_name,
                    (1000, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    self.COLOR_WHITE,
                    2
                )
                
                # Speed indicator
                cv2.putText(
                    img,
                    "4x",
                    (1220, 700),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    self.COLOR_WHITE,
                    2
                )
                
                out.write(img)
            
        finally:
            out.release()
        
        logger.info(f"Timelapse MP4 created: {output_path}")
        return output_path


# Global singleton instance
_media_worker: Optional[MediaWorker] = None


def get_media_worker() -> MediaWorker:
    """
    Get or create the global media worker instance.
    
    Returns:
        MediaWorker: Global media worker instance
    """
    global _media_worker
    if _media_worker is None:
        _media_worker = MediaWorker()
    return _media_worker
