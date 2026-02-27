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
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import cv2
import imageio
import numpy as np

from app.utils.paths import DATA_DIR

logger = logging.getLogger(__name__)


def _ascii_safe(text: str) -> str:
    """Replace Turkish/Unicode chars with ASCII for cv2.putText (HERSHEY fonts are ASCII-only)."""
    table = str.maketrans(
        "öşçığüÖŞÇİĞÜ",
        "osciguOSCIGU",
    )
    return text.translate(table)


def _local_time_str(utc_dt: datetime) -> str:
    """Convert a UTC datetime to local wall-clock time string (HH:MM:SS)."""
    return datetime.fromtimestamp(utc_dt.timestamp()).strftime("%H:%M:%S")

def _local_time_ms_from_epoch(epoch_s: float) -> str:
    """Convert epoch seconds to local wall-clock time string with milliseconds."""
    dt = datetime.fromtimestamp(epoch_s)
    return dt.strftime("%H:%M:%S.") + f"{int(dt.microsecond / 1000):03d}"


class MediaWorker:
    """Worker for event media generation."""
    
    # Media configuration
    MEDIA_DIR = DATA_DIR / "media"
    
    # Collage settings
    COLLAGE_FRAMES = 6
    COLLAGE_FRAME_SIZE = (640, 480)
    COLLAGE_GRID = (3, 2)  # 3 columns, 2 rows
    COLLAGE_QUALITY = 90

    # AI collage settings (smaller + person-focused for faster/more reliable vision checks)
    AI_COLLAGE_FRAMES = 6
    AI_COLLAGE_FRAME_SIZE = (384, 288)
    AI_COLLAGE_GRID = (3, 2)
    AI_COLLAGE_QUALITY = 82
    AI_CROP_PADDING = 2.2
    
    # GIF settings
    GIF_FRAMES = 10  # Scrypted: 5-8, ours: 10 (smoother!)
    GIF_SIZE = (640, 480)
    GIF_DURATION = 0.5  # seconds per frame
    GIF_MAX_SIZE_MB = 2.0  # Telegram limit
    GIF_QUALITY = 85
    
    # MP4 settings
    MP4_MAX_SIZE = (1280, 720)
    MP4_FPS = 30  # Fast playback
    MP4_MAX_OUTPUT_FPS = 60  # Allow faster playback
    MP4_CODECS = ("mp4v", "avc1", "H264")
    MP4_CRF = 15  # High quality
    MP4_PRESET = "slow"  # Better compression
    MP4_MIN_DURATION = 0.5
    MP4_MIN_OUTPUT_DURATION = 5.0  # Min 5s output (20s raw @ 4x = 5s)
    MP4_MAX_DURATION = 30.0
    MP4_SPEED_FACTOR = 4.0  # 4x speedup (matches recorder extract_clip)
    MP4_MIN_OUTPUT_FPS = 3
    
    # Overlay colors (BGR format)
    COLOR_WHITE = (255, 255, 255)
    COLOR_ACCENT = (255, 140, 91)  # #5B8CFF in BGR
    
    def __init__(self):
        """Initialize media worker."""
        # Ensure media directory exists
        self.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        self._ffmpeg_blacklist: set[str] = set()
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
        """Select indices evenly - never repeat frames."""
        if frame_count <= 1:
            return [0] if frame_count == 1 else []
        if target_count <= 1:
            return [0]
        # Cap to frame_count to avoid repetition
        target_count = min(target_count, frame_count)
        return [int(i * (frame_count - 1) / (target_count - 1)) for i in range(target_count)]

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
            return [c for c in self._ffmpeg_candidates if c not in self._ffmpeg_blacklist]

        candidates: List[str] = []

        if "pytest" not in sys.modules:
            try:
                import imageio_ffmpeg

                imageio_ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                if imageio_ffmpeg_exe:
                    candidates.append(imageio_ffmpeg_exe)
            except Exception as exc:
                logger.debug("imageio-ffmpeg unavailable: %s", exc)

        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg and system_ffmpeg not in candidates:
            candidates.append(system_ffmpeg)

        self._ffmpeg_candidates = candidates
        return [c for c in candidates if c not in self._ffmpeg_blacklist]

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
            ("libx264", ["-preset", self.MP4_PRESET, "-crf", str(self.MP4_CRF), "-profile:v", "baseline", "-level", "3.0", "-pix_fmt", "yuv420p"]),
            ("mpeg4", ["-q:v", "5", "-pix_fmt", "yuv420p"]),
        )

        # Resize and collect frame bytes once; feed FFmpeg from temp file to avoid pipe flush errors
        resized: List[np.ndarray] = []
        for frame in frames:
            if frame is None:
                continue
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            resized.append(frame)
        if not resized:
            logger.warning("FFmpeg encode skipped: no frames")
            return False

        raw_path: Optional[str] = None
        try:
            fd, raw_path = tempfile.mkstemp(suffix=".raw")
            os.close(fd)
            with open(raw_path, "wb") as f:
                for frame in resized:
                    f.write(frame.tobytes())
        except Exception as exc:
            logger.warning("FFmpeg encode: failed to write temp raw file: %s", exc)
            if raw_path and os.path.exists(raw_path):
                try:
                    os.unlink(raw_path)
                except OSError:
                    pass
            return False

        try:
            for ffmpeg in ffmpeg_candidates:
                candidate_ok = False
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
                        raw_path,
                        "-c:v",
                        codec,
                        *extra_args,
                        "-movflags",
                        "+faststart",
                        output_path,
                    ]
                    try:
                        proc = subprocess.run(
                            cmd,
                            capture_output=True,
                            timeout=120,
                        )
                        if proc.returncode != 0:
                            error_text = proc.stderr.decode(errors="ignore").strip()
                            logger.warning("FFmpeg encode failed (%s): %s", codec, error_text or "unknown")
                            continue
                        candidate_ok = True
                        return True
                    except subprocess.TimeoutExpired:
                        logger.warning("FFmpeg encode timed out (%s)", codec)
                        continue
                    except Exception as exc:
                        logger.warning("FFmpeg encode failed (%s): %s", codec, exc)
                        continue
                if not candidate_ok:
                    self._ffmpeg_blacklist.add(ffmpeg)
                    logger.warning("FFmpeg binary disabled after failures: %s", ffmpeg)
            return False
        finally:
            if raw_path and os.path.exists(raw_path):
                try:
                    os.unlink(raw_path)
                except OSError:
                    pass

    def _remux_mp4_faststart(self, mp4_path: str) -> None:
        """Remux MP4 with moov atom at start for web streaming (Range requests)."""
        ffmpeg_candidates = self._resolve_ffmpeg_candidates()
        if not ffmpeg_candidates or not os.path.exists(mp4_path):
            return
        tmp_path = f"{mp4_path}.faststart.tmp"
        try:
            for ffmpeg in ffmpeg_candidates:
                cmd = [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    mp4_path,
                    "-c",
                    "copy",
                    "-movflags",
                    "+faststart",
                    tmp_path,
                ]
                try:
                    proc = subprocess.run(cmd, capture_output=True, timeout=60)
                    if proc.returncode == 0 and os.path.exists(tmp_path):
                        os.replace(tmp_path, mp4_path)
                        logger.debug("MP4 remuxed with faststart: %s", mp4_path)
                        return
                except (subprocess.TimeoutExpired, OSError):
                    continue
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

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

    def create_minimal_mp4(
        self,
        frames: List[np.ndarray],
        output_path: str,
        camera_name: str = "Camera",
        timestamp: Optional[datetime] = None,
    ) -> str:
        """Create minimal MP4 from frames when main encode fails (fallback)."""
        if not frames or frames[0] is None:
            raise ValueError("No frames for minimal MP4")
        target_size = self._get_mp4_target_size(frames[0])
        scale, resized_w, resized_h, x_offset, y_offset = self._get_mp4_layout(frames[0], target_size)
        size = (target_size[0], target_size[1])
        fps = min(15, max(5, len(frames) // 2))
        processed: List[np.ndarray] = []
        for frame in frames:
            img = self._resize_with_padding(frame, resized_w, resized_h, x_offset, y_offset, scale, target_size)
            if timestamp:
                margin = 8
                tstr = (timestamp + timedelta(seconds=len(processed) / max(1, fps))).strftime("%H:%M:%S")
                cv2.putText(img, tstr, (margin, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.COLOR_WHITE, 1)
            processed.append(img)
        encoded = self._encode_mp4_ffmpeg(processed, output_path, fps, size)
        if not encoded:
            self._encode_mp4_opencv(processed, output_path, fps, size)
        self._remux_mp4_faststart(output_path)
        return output_path

    def _blur_score(self, frame: np.ndarray) -> float:
        """Laplacian variance: higher = sharper, lower = blurrier."""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            return float(laplacian.var())
        except Exception:
            return 0.0

    def _select_indices_by_time(
        self,
        timestamps: List[float],
        target_count: int,
    ) -> List[int]:
        """Select indices by time - never repeat frames."""
        if not timestamps:
            return []
        if target_count <= 1:
            return [0]
        target_count = min(target_count, len(timestamps))
        start = timestamps[0]
        end = timestamps[-1]
        if end <= start:
            return [0]
        step = (end - start) / (target_count - 1)
        targets = [start + (i * step) for i in range(target_count)]
        indices: List[int] = []
        idx = 0
        for target in targets:
            while idx + 1 < len(timestamps) and abs(timestamps[idx + 1] - target) <= abs(timestamps[idx] - target):
                idx += 1
            indices.append(idx)
        return indices

    def _select_indices_by_time_and_sharpness(
        self,
        frames: List[np.ndarray],
        timestamps: List[float],
        target_count: int,
    ) -> List[int]:
        """Select indices by time, preferring sharper frames when multiple candidates exist."""
        if not timestamps or not frames or len(frames) != len(timestamps):
            return self._select_indices_by_time(timestamps, target_count) if timestamps else []

        n = len(timestamps)
        if target_count <= 1:
            return [0]
        target_count = min(target_count, n)
        start = timestamps[0]
        end = timestamps[-1]
        if end <= start:
            return [0]

        indices: List[int] = []
        used: set[int] = set()
        step = (end - start) / (target_count - 1)
        for i in range(target_count):
            target = start + (i * step)
            window = max(0.15, step * 0.8)
            best_idx = -1
            best_score = -1.0
            for j in range(n):
                if j in used:
                    continue
                if abs(timestamps[j] - target) <= window:
                    score = self._blur_score(frames[j])
                    if best_idx < 0 or score > best_score:
                        best_idx = j
                        best_score = score
            if best_idx >= 0:
                indices.append(best_idx)
                used.add(best_idx)
            else:
                best_dist = float("inf")
                fallback = 0
                for j in range(n):
                    if j in used:
                        continue
                    d = abs(timestamps[j] - target)
                    if d < best_dist:
                        best_dist = d
                        fallback = j
                indices.append(fallback)
                used.add(fallback)
        return indices

    def _select_collage_indices(
        self,
        frames: List[np.ndarray],
        detections: Optional[List[Optional[Dict]]],
        timestamps: Optional[List[float]],
        best_idx: int,
    ) -> List[int]:
        """Select collage indices around best frame using time + quality scoring."""
        total = len(frames)
        if total == 0:
            return []

        best_idx = max(0, min(best_idx, total - 1))

        def _pick_closest_index(unused: set[int], target_idx: int) -> Optional[int]:
            if not unused:
                return None
            return min(unused, key=lambda i: abs(i - target_idx))

        if not timestamps or len(timestamps) != total:
            unused = set(range(total))
            target_indices = [best_idx - 3, best_idx - 2, best_idx - 1, best_idx, best_idx + 1, best_idx + 2]
            selected: List[int] = []
            for target in target_indices:
                if not unused:
                    break
                closest = _pick_closest_index(unused, target)
                if closest is None:
                    break
                selected.append(closest)
                unused.remove(closest)
            return selected[: self.COLLAGE_FRAMES]

        center_ts = float(timestamps[best_idx])
        target_offsets = [-0.90, -0.45, -0.15, 0.0, 0.30, 0.75]
        target_windows = [0.50, 0.38, 0.28, 0.0, 0.32, 0.48]
        selected: List[int] = []
        unused: set[int] = set(range(total))
        blur_cache: Dict[int, float] = {}

        def _det_conf(idx: int) -> float:
            if not detections or idx >= len(detections):
                return 0.0
            det = detections[idx]
            if not det:
                return 0.0
            return float(det.get("confidence", 0.0))

        def _blur_cached(idx: int) -> float:
            if idx not in blur_cache:
                blur_cache[idx] = self._blur_score(frames[idx])
            return blur_cache[idx]

        for slot, offset in enumerate(target_offsets):
            if not unused:
                break

            # Guarantee the event-centric frame is represented in collage.
            if offset == 0.0 and best_idx in unused:
                selected.append(best_idx)
                unused.remove(best_idx)
                continue

            target_ts = center_ts + offset
            window = max(0.15, target_windows[slot])
            candidates = [i for i in unused if abs(float(timestamps[i]) - target_ts) <= window]
            if not candidates:
                candidates = sorted(unused, key=lambda i: abs(float(timestamps[i]) - target_ts))[:4]
            if not candidates:
                break

            def _score(idx: int) -> float:
                time_dist = abs(float(timestamps[idx]) - target_ts)
                time_score = max(0.0, 1.0 - (time_dist / window))
                sharpness_score = min(_blur_cached(idx) / 120.0, 2.5)
                score = (_det_conf(idx) * 3.0) + sharpness_score + time_score
                if idx == best_idx:
                    score += 0.8
                return score

            chosen = max(candidates, key=_score)
            selected.append(chosen)
            unused.remove(chosen)

        target_len = min(self.COLLAGE_FRAMES, total)
        if len(selected) < target_len:
            fillers = sorted(unused, key=lambda i: abs(i - best_idx))
            for idx in fillers:
                selected.append(idx)
                if len(selected) >= target_len:
                    break

        return selected[: self.COLLAGE_FRAMES]

    @staticmethod
    def _bbox_or_none(det: Optional[Dict]) -> Optional[Tuple[float, float, float, float]]:
        if not isinstance(det, dict):
            return None
        bbox = det.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            return None
        try:
            x1, y1, x2, y2 = map(float, bbox)
            if x2 <= x1 or y2 <= y1:
                return None
            return x1, y1, x2, y2
        except Exception:
            return None

    @staticmethod
    def _bbox_to_frame_pixels(
        frame: np.ndarray,
        bbox: Tuple[float, float, float, float],
    ) -> Optional[Tuple[float, float, float, float]]:
        """Normalize bbox to frame pixel coordinates and clamp safely."""
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = bbox

        # Accept normalized bboxes (0..1) from alternative pipelines.
        if (
            0.0 <= x1 <= 1.0
            and 0.0 <= y1 <= 1.0
            and 0.0 <= x2 <= 1.0
            and 0.0 <= y2 <= 1.0
        ):
            scale_x = float(max(w - 1, 1))
            scale_y = float(max(h - 1, 1))
            x1, x2 = x1 * scale_x, x2 * scale_x
            y1, y2 = y1 * scale_y, y2 * scale_y

        x1 = max(0.0, min(float(x1), float(w - 1)))
        y1 = max(0.0, min(float(y1), float(h - 1)))
        x2 = max(0.0, min(float(x2), float(w - 1)))
        y2 = max(0.0, min(float(y2), float(h - 1)))
        if x2 <= x1 or y2 <= y1:
            return None
        return x1, y1, x2, y2

    def _crop_focus_on_bbox_with_meta(
        self,
        frame: np.ndarray,
        bbox: Tuple[float, float, float, float],
        target_size: Tuple[int, int],
        padding: float,
    ) -> Tuple[np.ndarray, Optional[Tuple[int, int, int, int]]]:
        """
        Crop around detection bbox while preserving aspect ratio.

        Returns:
            crop image and bbox coordinates mapped into crop-space.
        """
        h, w = frame.shape[:2]
        normalized = self._bbox_to_frame_pixels(frame, bbox)
        if normalized is None:
            return frame, None
        x1, y1, x2, y2 = normalized

        bw = max(8.0, x2 - x1)
        bh = max(8.0, y2 - y1)
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0

        crop_w = min(float(w), max(96.0, bw * padding))
        crop_h = min(float(h), max(96.0, bh * padding))

        target_ratio = float(target_size[0]) / float(target_size[1])
        cur_ratio = crop_w / max(1.0, crop_h)
        if cur_ratio < target_ratio:
            crop_w = min(float(w), crop_h * target_ratio)
        elif cur_ratio > target_ratio:
            crop_h = min(float(h), crop_w / target_ratio)

        xa = int(round(cx - (crop_w / 2.0)))
        ya = int(round(cy - (crop_h / 2.0)))
        xb = xa + int(round(crop_w))
        yb = ya + int(round(crop_h))

        if xa < 0:
            xb -= xa
            xa = 0
        if ya < 0:
            yb -= ya
            ya = 0
        if xb > w:
            shift = xb - w
            xa = max(0, xa - shift)
            xb = w
        if yb > h:
            shift = yb - h
            ya = max(0, ya - shift)
            yb = h

        if xb <= xa or yb <= ya:
            return frame, None

        crop = frame[ya:yb, xa:xb]
        crop_h_px, crop_w_px = crop.shape[:2]
        bx1 = int(round(x1)) - xa
        by1 = int(round(y1)) - ya
        bx2 = int(round(x2)) - xa
        by2 = int(round(y2)) - ya

        bx1 = max(0, min(bx1, crop_w_px - 1))
        by1 = max(0, min(by1, crop_h_px - 1))
        bx2 = max(0, min(bx2, crop_w_px - 1))
        by2 = max(0, min(by2, crop_h_px - 1))

        if bx2 <= bx1 or by2 <= by1:
            return crop, None
        return crop, (bx1, by1, bx2, by2)

    def _crop_focus_on_bbox(
        self,
        frame: np.ndarray,
        bbox: Tuple[float, float, float, float],
        target_size: Tuple[int, int],
        padding: float,
    ) -> np.ndarray:
        """Crop around detection bbox while preserving target aspect ratio."""
        crop, _ = self._crop_focus_on_bbox_with_meta(
            frame=frame,
            bbox=bbox,
            target_size=target_size,
            padding=padding,
        )
        return crop

    def _select_ai_collage_indices(
        self,
        frames: List[np.ndarray],
        detections: Optional[List[Optional[Dict]]],
        timestamps: Optional[List[float]],
        best_idx: int,
    ) -> List[int]:
        total = len(frames)
        if total == 0:
            return []

        baseline = self._select_collage_indices(frames, detections, timestamps, best_idx)
        if not detections:
            return baseline

        det_indices = [
            i for i in range(min(total, len(detections)))
            if self._bbox_or_none(detections[i]) is not None
        ]
        if not det_indices:
            return baseline

        target_len = min(total, self.AI_COLLAGE_FRAMES)
        first_det = min(det_indices)
        last_det = max(det_indices)
        has_valid_ts = bool(timestamps) and len(timestamps) == total

        blur_cache: Dict[int, float] = {}

        def _blur_cached(idx: int) -> float:
            if idx not in blur_cache:
                blur_cache[idx] = self._blur_score(frames[idx])
            return blur_cache[idx]

        def _det_conf(idx: int) -> float:
            det = detections[idx] if idx < len(detections) else None
            if not isinstance(det, dict):
                return 0.0
            return float(det.get("confidence", 0.0) or 0.0)

        if best_idx not in det_indices:
            best_det_idx = max(det_indices, key=lambda i: (_det_conf(i), _blur_cached(i)))
        else:
            best_det_idx = best_idx

        selected: List[int] = []
        used: set[int] = set()

        def _append(idx: Optional[int]) -> None:
            if idx is None:
                return
            if idx in used:
                return
            selected.append(idx)
            used.add(idx)

        def _pick_nearest(
            candidates: List[int],
            *,
            target_idx: Optional[int] = None,
            target_ts: Optional[float] = None,
            prefer_bbox: Optional[bool] = None,
        ) -> Optional[int]:
            if not candidates:
                return None
            shortlist = candidates
            if has_valid_ts and target_ts is not None:
                shortlist = sorted(shortlist, key=lambda i: abs(float(timestamps[i]) - target_ts))[:10]
            elif target_idx is not None:
                shortlist = sorted(shortlist, key=lambda i: abs(i - target_idx))[:10]

            def _score(idx: int) -> float:
                score = min(_blur_cached(idx) / 140.0, 2.0) + (_det_conf(idx) * 1.8)
                has_bbox = self._bbox_or_none(detections[idx] if idx < len(detections) else None) is not None
                if prefer_bbox is True:
                    score += 1.0 if has_bbox else -0.8
                elif prefer_bbox is False:
                    score += 0.8 if not has_bbox else -0.4
                if has_valid_ts and target_ts is not None:
                    dist = abs(float(timestamps[idx]) - target_ts)
                    score += max(0.0, 1.2 - (dist / 0.8))
                elif target_idx is not None:
                    score += max(0.0, 1.0 - (abs(idx - target_idx) / 6.0))
                return score

            return max(shortlist, key=_score)

        # 1) Force at least two pre-motion context frames so AI sees "before movement".
        pre_candidates = [i for i in range(0, first_det) if i not in used]
        if has_valid_ts:
            first_ts = float(timestamps[first_det])
            pre_targets = [first_ts - 1.0, first_ts - 0.45]
            for target_ts in pre_targets:
                pool = [i for i in pre_candidates if i not in used]
                if not pool:
                    break
                _append(_pick_nearest(pool, target_ts=target_ts, prefer_bbox=False))
        else:
            for target_idx in [max(0, first_det - 5), max(0, first_det - 2)]:
                pool = [i for i in pre_candidates if i not in used]
                if not pool:
                    break
                _append(_pick_nearest(pool, target_idx=target_idx, prefer_bbox=False))

        # 2) Core motion frames: onset, best detection, last detection.
        for key_idx in (first_det, best_det_idx, last_det):
            if key_idx not in used:
                _append(key_idx)
            else:
                neighbor_pool = [i for i in det_indices if i not in used]
                _append(_pick_nearest(neighbor_pool, target_idx=key_idx, prefer_bbox=True))

        # 3) Add one post-motion frame when available.
        post_candidates = [i for i in range(last_det + 1, total) if i not in used]
        if post_candidates:
            if has_valid_ts:
                post_target_ts = float(timestamps[last_det]) + 0.45
                _append(_pick_nearest(post_candidates, target_ts=post_target_ts, prefer_bbox=False))
            else:
                _append(_pick_nearest(post_candidates, target_idx=min(total - 1, last_det + 2), prefer_bbox=False))

        # 4) Fill remaining from baseline, then nearest unused.
        for idx in baseline:
            if len(selected) >= target_len:
                break
            _append(idx)
        if len(selected) < target_len:
            fillers = [i for i in range(total) if i not in used]
            fillers = sorted(fillers, key=lambda i: abs(i - best_det_idx))
            for idx in fillers:
                _append(idx)
                if len(selected) >= target_len:
                    break

        if has_valid_ts:
            selected.sort(key=lambda i: float(timestamps[i]))
        else:
            selected.sort()
        return selected[:target_len]

    def create_ai_collage(
        self,
        frames: List[np.ndarray],
        detections: Optional[List[Optional[Dict]]],
        timestamps: Optional[List[float]],
        output_path: str,
        camera_name: str = "Camera",
        timestamp: Optional[datetime] = None,
        confidence: float = 0.0,
    ) -> str:
        """Create an AI-focused collage with detection-centric crops and lighter payload."""
        if len(frames) == 0:
            raise ValueError("Need at least 1 frame for AI collage")

        total = len(frames)
        best_idx = total // 2
        if detections:
            best_conf = -1.0
            for idx, det in enumerate(detections):
                bbox = self._bbox_or_none(det)
                if bbox is None:
                    continue
                conf = float(det.get("confidence", 0.0) or 0.0) if isinstance(det, dict) else 0.0
                if conf >= best_conf:
                    best_conf = conf
                    best_idx = idx

        selected_indices = self._select_ai_collage_indices(
            frames=frames,
            detections=detections,
            timestamps=timestamps,
            best_idx=best_idx,
        )
        if selected_indices and len(selected_indices) < self.AI_COLLAGE_FRAMES:
            selected_indices.extend([selected_indices[-1]] * (self.AI_COLLAGE_FRAMES - len(selected_indices)))

        event_slot = min(
            range(len(selected_indices)),
            key=lambda i: abs(selected_indices[i] - best_idx),
        )

        tiles: List[np.ndarray] = []
        for tile_idx, frame_idx in enumerate(selected_indices):
            src = frames[frame_idx]
            focused = src
            bbox_on_tile: Optional[Tuple[int, int, int, int]] = None
            if detections and frame_idx < len(detections):
                bbox = self._bbox_or_none(detections[frame_idx])
                if bbox is not None:
                    focused, bbox_in_focus = self._crop_focus_on_bbox_with_meta(
                        frame=src,
                        bbox=bbox,
                        target_size=self.AI_COLLAGE_FRAME_SIZE,
                        padding=self.AI_CROP_PADDING,
                    )
                    if bbox_in_focus is not None:
                        fx1, fy1, fx2, fy2 = bbox_in_focus
                        scale_x = self.AI_COLLAGE_FRAME_SIZE[0] / float(max(focused.shape[1], 1))
                        scale_y = self.AI_COLLAGE_FRAME_SIZE[1] / float(max(focused.shape[0], 1))
                        tx1 = int(round(fx1 * scale_x))
                        ty1 = int(round(fy1 * scale_y))
                        tx2 = int(round(fx2 * scale_x))
                        ty2 = int(round(fy2 * scale_y))
                        tx1 = max(0, min(tx1, self.AI_COLLAGE_FRAME_SIZE[0] - 1))
                        ty1 = max(0, min(ty1, self.AI_COLLAGE_FRAME_SIZE[1] - 1))
                        tx2 = max(0, min(tx2, self.AI_COLLAGE_FRAME_SIZE[0] - 1))
                        ty2 = max(0, min(ty2, self.AI_COLLAGE_FRAME_SIZE[1] - 1))
                        if tx2 > tx1 and ty2 > ty1:
                            bbox_on_tile = (tx1, ty1, tx2, ty2)

            img = cv2.resize(focused, self.AI_COLLAGE_FRAME_SIZE, interpolation=cv2.INTER_AREA)
            if bbox_on_tile is not None:
                cv2.rectangle(
                    img,
                    (bbox_on_tile[0], bbox_on_tile[1]),
                    (bbox_on_tile[2], bbox_on_tile[3]),
                    self.COLOR_ACCENT,
                    2,
                )

            cv2.putText(
                img,
                str(tile_idx + 1),
                (8, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                self.COLOR_WHITE,
                2,
            )
            if timestamps and frame_idx < len(timestamps):
                cv2.putText(
                    img,
                    _local_time_ms_from_epoch(float(timestamps[frame_idx])),
                    (8, self.AI_COLLAGE_FRAME_SIZE[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    self.COLOR_WHITE,
                    1,
                )
            elif tile_idx == 0 and timestamp:
                cv2.putText(
                    img,
                    _local_time_str(timestamp),
                    (8, self.AI_COLLAGE_FRAME_SIZE[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    self.COLOR_WHITE,
                    1,
                )

            if tile_idx == event_slot:
                label_x = self.AI_COLLAGE_FRAME_SIZE[0] - 70
                label_y = 22
                if bbox_on_tile is not None:
                    cv2.rectangle(
                        img,
                        (bbox_on_tile[0], bbox_on_tile[1]),
                        (bbox_on_tile[2], bbox_on_tile[3]),
                        self.COLOR_ACCENT,
                        3,
                    )
                    label_x = max(4, bbox_on_tile[0])
                    label_y = max(20, bbox_on_tile[1] - 8)
                else:
                    cv2.circle(
                        img,
                        (self.AI_COLLAGE_FRAME_SIZE[0] - 16, 16),
                        6,
                        self.COLOR_ACCENT,
                        -1,
                    )
                cv2.putText(
                    img,
                    f"{confidence:.0%}",
                    (label_x, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    self.COLOR_ACCENT,
                    2,
                )
            tiles.append(img)

        rows = []
        for row_idx in range(self.AI_COLLAGE_GRID[1]):
            row_frames = []
            for col_idx in range(self.AI_COLLAGE_GRID[0]):
                idx = row_idx * self.AI_COLLAGE_GRID[0] + col_idx
                if idx < len(tiles):
                    row_frames.append(tiles[idx])
                else:
                    row_frames.append(np.zeros((*self.AI_COLLAGE_FRAME_SIZE[::-1], 3), dtype=np.uint8))
            rows.append(np.hstack(row_frames))
        collage = np.vstack(rows)

        cv2.putText(
            collage,
            _ascii_safe(camera_name),
            (collage.shape[1] - 240, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            self.COLOR_WHITE,
            1,
        )

        cv2.imwrite(output_path, collage, [cv2.IMWRITE_JPEG_QUALITY, self.AI_COLLAGE_QUALITY])
        logger.info("AI collage created: %s", output_path)
        return output_path
    
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
        Create 6-frame collage grid.
        
        Layout: 3x2 grid (6 frames)
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

        indices = self._select_collage_indices(
            frames=frames,
            detections=detections,
            timestamps=timestamps,
            best_idx=best_idx,
        )

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

        # Select 6 dense timeline frames
        selected_indices = list(indices)
        selected = [frames[i] for i in selected_indices]
        event_slot = min(
            range(len(selected_indices)),
            key=lambda i: abs(selected_indices[i] - best_idx),
        )
        
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
            
            # Add frame timestamp with millisecond precision.
            if timestamps and frame_idx is not None and frame_idx < len(timestamps):
                frame_time_text = _local_time_ms_from_epoch(float(timestamps[frame_idx]))
                cv2.putText(
                    img,
                    frame_time_text,
                    (10, 72),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.56,
                    self.COLOR_WHITE,
                    2
                )
            elif idx == 0 and timestamp:
                cv2.putText(
                    img,
                    _local_time_str(timestamp),
                    (10, 72),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.56,
                    self.COLOR_WHITE,
                    2
                )
            
            # Add confidence and explicit event highlight on best-match frame.
            if idx == event_slot:
                cv2.putText(
                    img,
                    f"{confidence:.0%}",
                    (10, 460),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    self.COLOR_ACCENT,
                    2
                )
                cv2.putText(
                    img,
                    "EVENT",
                    (10, 432),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.62,
                    self.COLOR_ACCENT,
                    2,
                )
                # Important: never highlight the whole frame.
                # Event marker should point to the detected person area only.
                if detections and frame_idx is not None and frame_idx < len(detections):
                    event_det = detections[frame_idx]
                    if event_det and event_det.get("bbox"):
                        x1, y1, x2, y2 = event_det["bbox"]
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
                        cv2.rectangle(img, (x1, y1), (x2, y2), self.COLOR_ACCENT, 3)
            
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
        
        # Add camera name (top right) — ASCII-safe for cv2 HERSHEY font
        cv2.putText(
            collage,
            _ascii_safe(camera_name),
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
                _ascii_safe(camera_name),
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
        
        # imageio v3 expects duration in milliseconds; v2 expected seconds.
        # Using ms avoids the 2000 fps bug introduced by v3's changed convention.
        gif_duration_ms = int(self.GIF_DURATION * 1000)

        def _write_gif(path: str, frames_list) -> None:
            """Write GIF atomically via a temp file."""
            parent = os.path.dirname(os.path.abspath(path))
            fd, tmp_path = tempfile.mkstemp(suffix=".gif", dir=parent)
            os.close(fd)
            try:
                imageio.mimsave(tmp_path, frames_list, duration=gif_duration_ms, loop=0)
                os.replace(tmp_path, path)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

        _write_gif(output_path, processed)
        
        # Check size and reduce quality if needed
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        if size_mb > self.GIF_MAX_SIZE_MB:
            logger.warning(f"GIF size {size_mb:.2f}MB > {self.GIF_MAX_SIZE_MB}MB, reducing quality")
            processed_small = [cv2.resize(img, (480, 360)) for img in processed]
            _write_gif(output_path, processed_small)
        
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
        speed_factor: Optional[float] = None,
        overlay_use_utc: bool = False,
    ) -> str:
        """
        Create timelapse MP4 with detection boxes.
        
        Overlay time = server time (UTC or local per settings). Never camera OSD.
        
        Args:
            frames: List of frames
            detections: List of detection dicts (one per frame)
            output_path: Output MP4 path
            camera_name: Camera name for overlay
            timestamp: Event start timestamp
            overlay_use_utc: If True show UTC, else local (server time only)
            
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
        if real_time:
            target_duration = max(actual_duration, self.MP4_MIN_OUTPUT_DURATION)
            if timestamps and len(timestamps) == frame_count and actual_duration > 0:
                target_fps = frame_count / actual_duration
            else:
                target_fps = self.MP4_FPS
            target_fps = min(self.MP4_MAX_OUTPUT_FPS, target_fps)
            target_fps = max(self.MP4_MIN_OUTPUT_FPS, target_fps)
            target_fps_int = max(1, int(round(target_fps)))
            # DON'T pad with duplicate frames! Use actual frame count!
            target_frame_count = frame_count  # Use all available frames
            indices = list(range(frame_count))
            speed_factor = 1.0
        else:
            sf = float(speed_factor) if speed_factor is not None else self.MP4_SPEED_FACTOR
            sf = max(1.0, min(10.0, sf))
            target_duration = max(
                min_duration,
                min(self.MP4_MAX_DURATION, actual_duration / sf),
            )
            if self.MP4_MIN_OUTPUT_DURATION:
                target_duration = max(target_duration, self.MP4_MIN_OUTPUT_DURATION)

            target_fps = min(self.MP4_MAX_OUTPUT_FPS, frame_count / max(target_duration, 0.1)) if frame_count > 0 else self.MP4_FPS
            target_fps = max(self.MP4_MIN_OUTPUT_FPS, target_fps)
            target_fps_int = max(1, int(round(target_fps)))
            target_frame_count = max(1, int(round(target_duration * target_fps_int)))
            # Never repeat frames: cap to available frame count
            target_frame_count = min(target_frame_count, frame_count)
            if timestamps and len(timestamps) == frame_count:
                indices = self._select_indices_by_time_and_sharpness(frames, timestamps, target_frame_count)
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
                    # Server time when frame was captured. UTC or local per settings.
                    if overlay_use_utc:
                        frame_time = datetime.fromtimestamp(timestamps[frame_idx], tz=timezone.utc).replace(tzinfo=None)
                    else:
                        frame_time = datetime.fromtimestamp(timestamps[frame_idx]).replace(tzinfo=None)
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
                safe_name = _ascii_safe(camera_name)
                (name_w, name_h), _ = cv2.getTextSize(
                    safe_name,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_medium,
                    text_thickness,
                )
                cv2.putText(
                    img,
                    safe_name,
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
            self._encode_mp4_opencv(processed_frames, output_path, target_fps_int, target_size)
            self._remux_mp4_faststart(output_path)
            try:
                Path(legacy_marker).write_text("mp4v", encoding="utf-8")
            except Exception:
                pass
        if encoded:
            try:
                if os.path.exists(legacy_marker):
                    os.remove(legacy_marker)
            except Exception:
                pass
        else:
            pass  # OpenCV already run above when FFmpeg failed

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
