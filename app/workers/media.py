"""
Media generation worker for Smart Motion Detector v2.

This worker handles creation of event media files:
- Collage (5 frame grid)
- Timeline GIF (preview)
- Timelapse MP4 (720p with detection boxes)

Better than Scrypted: More frames, higher quality, detection boxes!
"""
import logging
import os
import shutil
import subprocess
import sys
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
    MP4_MAX_SIZE = (1280, 720)
    MP4_FPS = 12
    MP4_MAX_OUTPUT_FPS = 20
    MP4_CODECS = ("mp4v", "avc1", "H264")
    MP4_CRF = 18
    MP4_PRESET = "medium"
    MP4_MIN_DURATION = 0.5
    MP4_MIN_OUTPUT_DURATION = 10.0
    MP4_MAX_DURATION = 12.0
    MP4_SPEED_FACTOR = 4.0
    MP4_MIN_OUTPUT_FPS = 3
    
    # Overlay colors (BGR format)
    COLOR_WHITE = (255, 255, 255)
    COLOR_ACCENT = (255, 140, 91)  # #5B8CFF in BGR
    
    def __init__(self):
        """Initialize media worker."""
        # Ensure media directory exists
        self.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("MediaWorker initialized")

    def _get_mp4_target_size(self, frame: np.ndarray) -> tuple[int, int]:
        height, width = frame.shape[:2]
        max_w, max_h = self.MP4_MAX_SIZE
        if width <= max_w and height <= max_h:
            target_w = max(2, width - (width % 2))
            target_h = max(2, height - (height % 2))
            return target_w, target_h
        scale = min(max_w / width, max_h / height)
        target_w = max(2, int(round(width * scale)))
        target_h = max(2, int(round(height * scale)))
        target_w -= target_w % 2
        target_h -= target_h % 2
        return target_w, target_h

    def _get_mp4_layout(
        self,
        frame: np.ndarray,
        target_size: tuple[int, int],
    ) -> tuple[float, int, int, int, int]:
        """Calculate scale and padding for MP4 frames."""
        height, width = frame.shape[:2]
        target_w, target_h = target_size
        scale = min(target_w / width, target_h / height)
        resized_w = max(2, int(round(width * scale)))
        resized_h = max(2, int(round(height * scale)))
        resized_w -= resized_w % 2
        resized_h -= resized_h % 2
        x_offset = max(0, (target_w - resized_w) // 2)
        y_offset = max(0, (target_h - resized_h) // 2)
        return scale, resized_w, resized_h, x_offset, y_offset

    def _resize_with_padding(
        self,
        frame: np.ndarray,
        resized_w: int,
        resized_h: int,
        x_offset: int,
        y_offset: int,
        scale: float,
        target_size: tuple[int, int],
    ) -> np.ndarray:
        """Resize a frame and pad to target size."""
        interpolation = cv2.INTER_LANCZOS4 if scale > 1 else cv2.INTER_AREA
        resized = cv2.resize(frame, (resized_w, resized_h), interpolation=interpolation)
        canvas = np.zeros((target_size[1], target_size[0], 3), dtype=np.uint8)
        canvas[y_offset:y_offset + resized_h, x_offset:x_offset + resized_w] = resized
        return canvas

    def _select_indices(self, frame_count: int, target_count: int) -> List[int]:
        if frame_count <= 1:
            return [0] if frame_count == 1 else []
        if target_count <= 1:
            return [0]
        if target_count <= frame_count:
            return [int(i * (frame_count - 1) / (target_count - 1)) for i in range(target_count)]
        ratio = target_count / frame_count
        indices: List[int] = []
        for i in range(target_count):
            idx = min(frame_count - 1, int(i / ratio))
            indices.append(idx)
        return indices

    def _open_video_writer(
        self,
        output_path: str,
        size: tuple[int, int],
        fps: int,
    ) -> Optional[cv2.VideoWriter]:
        """Open MP4 writer with codec fallback."""
        for codec in self.MP4_CODECS:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            writer = cv2.VideoWriter(output_path, fourcc, fps, size)
            if writer.isOpened():
                if codec != self.MP4_CODECS[-1]:
                    logger.info("MP4 codec selected: %s", codec)
                return writer
            writer.release()
        return None

    def _resolve_ffmpeg_candidates(self) -> List[str]:
        if hasattr(self, "_ffmpeg_candidates"):
            return list(self._ffmpeg_candidates)

        candidates: List[str] = []
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            candidates.append(system_ffmpeg)

        if "pytest" not in sys.modules:
            try:
                import imageio_ffmpeg

                imageio_ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                if imageio_ffmpeg_exe and imageio_ffmpeg_exe not in candidates:
                    candidates.append(imageio_ffmpeg_exe)
            except Exception as exc:
                logger.debug("imageio-ffmpeg unavailable: %s", exc)

        self._ffmpeg_candidates = candidates
        return candidates

    def _encode_mp4_ffmpeg(
        self,
        frames: List[np.ndarray],
        output_path: str,
        fps: int,
        size: tuple[int, int],
    ) -> bool:
        """Encode MP4 using ffmpeg for better quality."""
        ffmpeg_candidates = self._resolve_ffmpeg_candidates()
        if not ffmpeg_candidates:
            return False
        if not frames:
            return False

        width, height = size
        codec_candidates = (
            ("libx264", ["-preset", self.MP4_PRESET, "-crf", str(self.MP4_CRF), "-pix_fmt", "yuv420p"]),
            ("mpeg4", ["-q:v", "5", "-pix_fmt", "yuv420p"]),
        )

        for ffmpeg in ffmpeg_candidates:
            for codec, extra_args in codec_candidates:
                cmd = [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "bgr24",
                    "-s",
                    f"{width}x{height}",
                    "-r",
                    str(fps),
                    "-i",
                    "pipe:0",
                    "-c:v",
                    codec,
                    *extra_args,
                    "-movflags",
                    "+faststart",
                    output_path,
                ]
                try:
                    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    write_error: Optional[Exception] = None
                    written = 0
                    stdout = b""
                    stderr = b""
                    try:
                        for frame in frames:
                            if frame is None:
                                continue
                            if frame.shape[1] != width or frame.shape[0] != height:
                                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                            try:
                                proc.stdin.write(frame.tobytes())
                                written += 1
                            except (BrokenPipeError, ValueError) as exc:
                                write_error = exc
                                break
                        if proc.stdin and not proc.stdin.closed:
                            proc.stdin.close()
                        stdout, stderr = proc.communicate()
                    finally:
                        if proc.stdin and not proc.stdin.closed:
                            proc.stdin.close()

                    if written == 0:
                        logger.warning("FFmpeg encode skipped: no frames written")
                        return False

                    if write_error or proc.returncode != 0:
                        error_text = stderr.decode(errors="ignore").strip()
                        detail = error_text or str(write_error or "unknown error")
                        logger.warning("FFmpeg encode failed (%s): %s", codec, detail)
                        continue

                    return True
                except Exception as exc:
                    logger.warning("FFmpeg encode failed (%s): %s", codec, exc)
                    continue

        return False

    def _encode_mp4_opencv(
        self,
        frames: List[np.ndarray],
        output_path: str,
        fps: int,
        size: tuple[int, int],
    ) -> None:
        """Fallback MP4 encoder using OpenCV."""
        out = self._open_video_writer(output_path, size, fps)
        if out is None:
            logger.error("Failed to open MP4 writer: %s", output_path)
            return
        try:
            for frame in frames:
                out.write(frame)
        except Exception as exc:
            logger.warning("OpenCV MP4 encode failed: %s", exc)
        finally:
            out.release()

    def _encode_mp4_imageio(
        self,
        frames: List[np.ndarray],
        output_path: str,
        fps: int,
        size: tuple[int, int],
    ) -> bool:
        """Encode MP4 using imageio-ffmpeg (H.264 preferred)."""
        if not frames:
            return False

        width, height = size
        for codec in ("libx264", "mpeg4"):
            writer = None
            try:
                writer = imageio.get_writer(
                    output_path,
                    fps=fps,
                    codec=codec,
                    format="FFMPEG",
                    macro_block_size=None,
                    ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
                )
                for frame in frames:
                    if frame is None:
                        continue
                    if frame.shape[1] != width or frame.shape[0] != height:
                        frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                    writer.append_data(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                writer.close()
                writer = None
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info("MP4 encoded with imageio (%s)", codec)
                    return True
            except Exception as exc:
                logger.warning("imageio MP4 encode failed (%s): %s", codec, exc)
            finally:
                try:
                    if writer is not None:
                        writer.close()
                except Exception:
                    pass
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception:
                pass

        return False

    def _select_indices_by_time(
        self,
        timestamps: List[float],
        target_count: int,
    ) -> List[int]:
        if not timestamps:
            return []
        if target_count <= 1:
            return [0]
        start = timestamps[0]
        end = timestamps[-1]
        if end <= start:
            return [0 for _ in range(target_count)]
        step = (end - start) / (target_count - 1)
        targets = [start + (i * step) for i in range(target_count)]
        indices: List[int] = []
        idx = 0
        for target in targets:
            while idx + 1 < len(timestamps) and abs(timestamps[idx + 1] - target) <= abs(timestamps[idx] - target):
                idx += 1
            indices.append(idx)
        return indices
    
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

        if indices and len(indices) < self.COLLAGE_FRAMES:
            indices.extend([indices[-1]] * (self.COLLAGE_FRAMES - len(indices)))
        
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
        selected_indices = list(indices)
        selected = [frames[i] for i in selected_indices]
        
        # Resize all frames
        resized = []
        for idx, frame in enumerate(selected):
            img = cv2.resize(frame, self.COLLAGE_FRAME_SIZE)
            frame_idx = selected_indices[idx] if idx < len(selected_indices) else None

            if detections and frame_idx is not None and frame_idx < len(detections):
                detection = detections[frame_idx]
                if detection and detection.get("bbox"):
                    x1, y1, x2, y2 = detection["bbox"]
                    scale_x = self.COLLAGE_FRAME_SIZE[0] / frame.shape[1]
                    scale_y = self.COLLAGE_FRAME_SIZE[1] / frame.shape[0]
                    x1 = int(x1 * scale_x)
                    y1 = int(y1 * scale_y)
                    x2 = int(x2 * scale_x)
                    y2 = int(y2 * scale_y)
                    x1 = max(0, min(x1, self.COLLAGE_FRAME_SIZE[0] - 1))
                    y1 = max(0, min(y1, self.COLLAGE_FRAME_SIZE[1] - 1))
                    x2 = max(0, min(x2, self.COLLAGE_FRAME_SIZE[0] - 1))
                    y2 = max(0, min(y2, self.COLLAGE_FRAME_SIZE[1] - 1))
                    cv2.rectangle(img, (x1, y1), (x2, y2), self.COLOR_ACCENT, 2)
                    label = f"Person {float(detection.get('confidence', 0.0)):.0%}"
                    cv2.putText(
                        img,
                        label,
                        (x1, max(20, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        self.COLOR_ACCENT,
                        2,
                    )
            
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
        timestamps: Optional[List[float]] = None,
        real_time: bool = False,
    ) -> str:
        """
        Create timelapse MP4 with detection boxes.
        
        Balanced MP4 quality with detection overlays.
        
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
        
        target_size = self._get_mp4_target_size(frames[0])
        scale, resized_w, resized_h, x_offset, y_offset = self._get_mp4_layout(frames[0], target_size)
        frame_count = len(frames)
        actual_duration = None
        if timestamps and len(timestamps) == frame_count:
            actual_duration = max(0.0, timestamps[-1] - timestamps[0])
        if not actual_duration:
            actual_duration = frame_count / max(self.MP4_FPS, 1)

        min_duration = min(self.MP4_MIN_DURATION, actual_duration / 2) if actual_duration else self.MP4_MIN_DURATION
        speed_base = 1.0 if real_time else self.MP4_SPEED_FACTOR
        target_duration = max(
            min_duration,
            min(self.MP4_MAX_DURATION, actual_duration / speed_base),
        )
        if self.MP4_MIN_OUTPUT_DURATION:
            target_duration = max(target_duration, self.MP4_MIN_OUTPUT_DURATION)

        target_fps = min(self.MP4_MAX_OUTPUT_FPS, frame_count / max(target_duration, 0.1)) if frame_count > 0 else self.MP4_FPS
        target_fps = max(self.MP4_MIN_OUTPUT_FPS, target_fps)
        target_fps_int = max(1, int(round(target_fps)))
        target_frame_count = max(1, int(round(target_duration * target_fps_int)))
        if timestamps and len(timestamps) == frame_count:
            indices = self._select_indices_by_time(timestamps, target_frame_count)
        else:
            indices = self._select_indices(frame_count, target_frame_count)
        speed_factor = max(actual_duration / max(target_duration, 0.1), 1.0)
        scale_ref = min(target_size[0] / 1280, target_size[1] / 720)
        margin = max(8, int(16 * scale_ref))
        font_large = max(0.5, 1.0 * scale_ref)
        font_medium = max(0.45, 0.8 * scale_ref)
        font_small = max(0.45, 0.7 * scale_ref)
        text_thickness = max(1, int(2 * scale_ref))

        processed_frames: List[np.ndarray] = []
        for out_idx, frame_idx in enumerate(indices):
            frame = frames[frame_idx]
            img = self._resize_with_padding(
                frame,
                resized_w,
                resized_h,
                x_offset,
                y_offset,
                scale,
                target_size,
            )

            # Draw detection box if available
            if frame_idx < len(detections) and detections[frame_idx]:
                detection = detections[frame_idx]
                x1, y1, x2, y2 = detection['bbox']

                x1_scaled = int(x1 * scale) + x_offset
                y1_scaled = int(y1 * scale) + y_offset
                x2_scaled = int(x2 * scale) + x_offset
                y2_scaled = int(y2 * scale) + y_offset

                cv2.rectangle(
                    img,
                    (x1_scaled, y1_scaled),
                    (x2_scaled, y2_scaled),
                    self.COLOR_ACCENT,
                    max(2, text_thickness + 1),
                )

                label = f"Person {detection['confidence']:.0%}"
                cv2.putText(
                    img,
                    label,
                    (x1_scaled, max(0, y1_scaled - margin)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_medium,
                    self.COLOR_ACCENT,
                    text_thickness,
                )

            if timestamp:
                if timestamps and len(timestamps) == frame_count:
                    frame_time = datetime.fromtimestamp(timestamps[frame_idx])
                else:
                    frame_time = timestamp + timedelta(seconds=out_idx / target_fps_int)
                cv2.putText(
                    img,
                    frame_time.strftime("%H:%M:%S.%f")[:-3],
                    (margin, max(margin, int(40 * scale_ref))),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_large,
                    self.COLOR_WHITE,
                    text_thickness,
                )

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

            speed_text = f"{speed_factor:.1f}x"
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

            processed_frames.append(img)

        legacy_marker = f"{output_path}.legacy"
        encoded = self._encode_mp4_ffmpeg(processed_frames, output_path, target_fps_int, target_size)
        if not encoded:
            encoded = self._encode_mp4_imageio(processed_frames, output_path, target_fps_int, target_size)
        if encoded:
            try:
                if os.path.exists(legacy_marker):
                    os.remove(legacy_marker)
            except Exception:
                pass
        else:
            self._encode_mp4_opencv(processed_frames, output_path, target_fps_int, target_size)
            try:
                Path(legacy_marker).write_text("mp4v", encoding="utf-8")
            except Exception:
                pass

        logger.info(
            "Event MP4 created: %s size=%sx%s fps=%s duration=%.2fs speed=%.1fx",
            output_path,
            target_size[0],
            target_size[1],
            target_fps_int,
            target_duration,
            speed_factor,
        )
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
