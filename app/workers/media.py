"""
Media generation worker for Smart Motion Detector v2.

This worker handles creation of event media files:
- Collage (5 frame grid)
- Timeline GIF (deprecated)
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
    MP4_MAX_SIZE = (1280, 720)  # Avoid upscaling above 720p
    MP4_FPS = 15
    MP4_CODECS = ("avc1", "H264", "mp4v")
    
    # Overlay colors (BGR format)
    COLOR_WHITE = (255, 255, 255)
    COLOR_ACCENT = (255, 140, 91)  # #5B8CFF in BGR
    
    def __init__(self):
        """Initialize media worker."""
        # Ensure media directory exists
        self.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("MediaWorker initialized")

    def _get_mp4_target_size(self, frame: np.ndarray) -> tuple[tuple[int, int], float]:
        """Get MP4 target size without upscaling."""
        height, width = frame.shape[:2]
        max_w, max_h = self.MP4_MAX_SIZE
        scale = min(max_w / width, max_h / height, 1.0)
        target_w = max(2, int(width * scale))
        target_h = max(2, int(height * scale))
        # Ensure even dimensions for video codecs
        target_w -= target_w % 2
        target_h -= target_h % 2
        return (target_w, target_h), scale

    def _open_video_writer(self, output_path: str, size: tuple[int, int]) -> Optional[cv2.VideoWriter]:
        """Open MP4 writer with codec fallback."""
        for codec in self.MP4_CODECS:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            writer = cv2.VideoWriter(output_path, fourcc, self.MP4_FPS, size)
            if writer.isOpened():
                if codec != self.MP4_CODECS[-1]:
                    logger.info("MP4 codec selected: %s", codec)
                return writer
            writer.release()
        return None
    
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
        
        Better than Scrypted: up to 720p (no upscale), detection boxes!
        
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
        
        target_size, _ = self._get_mp4_target_size(frames[0])
        out = self._open_video_writer(output_path, target_size)
        if out is None:
            logger.error("Failed to open MP4 writer: %s", output_path)
            return output_path

        scale_ref = min(
            target_size[0] / self.MP4_MAX_SIZE[0],
            target_size[1] / self.MP4_MAX_SIZE[1],
            1.0,
        )
        margin = max(10, int(20 * scale_ref))
        font_large = max(0.6, 1.0 * scale_ref)
        font_medium = max(0.5, 0.8 * scale_ref)
        font_small = max(0.5, 0.7 * scale_ref)
        text_thickness = max(1, int(2 * scale_ref))
        
        try:
            for idx, frame in enumerate(frames):
                src_h, src_w = frame.shape[:2]
                scale_x = target_size[0] / src_w
                scale_y = target_size[1] / src_h
                interpolation = cv2.INTER_AREA if scale_x < 1 or scale_y < 1 else cv2.INTER_LINEAR
                img = cv2.resize(frame, target_size, interpolation=interpolation)
                
                # Draw detection box if available
                if idx < len(detections) and detections[idx]:
                    detection = detections[idx]
                    x1, y1, x2, y2 = detection['bbox']
                    
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
                        max(2, text_thickness + 1)
                    )
                    
                    # Confidence label
                    label = f"Person {detection['confidence']:.0%}"
                    cv2.putText(
                        img,
                        label,
                        (x1_scaled, max(0, y1_scaled - margin)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        font_medium,
                        self.COLOR_ACCENT,
                        text_thickness
                    )
                
                # Timestamp overlay
                if timestamp:
                    frame_time = timestamp + timedelta(seconds=idx / self.MP4_FPS)
                    cv2.putText(
                        img,
                        frame_time.strftime("%H:%M:%S.%f")[:-3],
                        (margin, max(margin, int(40 * scale_ref))),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        font_large,
                        self.COLOR_WHITE,
                        text_thickness
                    )
                
                # Camera name
                if camera_name:
                    (name_w, name_h), _ = cv2.getTextSize(
                        camera_name,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        font_medium,
                        text_thickness,
                    )
                    cv2.putText(
                        img,
                        camera_name,
                        (target_size[0] - name_w - margin, max(margin, name_h + margin // 2)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        font_medium,
                        self.COLOR_WHITE,
                        text_thickness,
                    )
                
                # Speed indicator
                speed_text = "4x"
                (speed_w, speed_h), _ = cv2.getTextSize(
                    speed_text,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_small,
                    text_thickness,
                )
                cv2.putText(
                    img,
                    speed_text,
                    (target_size[0] - speed_w - margin, target_size[1] - margin),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_small,
                    self.COLOR_WHITE,
                    text_thickness,
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
