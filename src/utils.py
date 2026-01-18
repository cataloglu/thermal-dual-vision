"""Utility functions for Smart Motion Detector."""

import asyncio
import base64
import io
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional, Sequence, TypeVar

import cv2
import numpy as np
from PIL import Image

T = TypeVar("T")


def encode_frame_to_base64(frame: np.ndarray, quality: int = 85) -> str:
    """
    Encode a numpy frame to base64 JPEG string.

    Args:
        frame: OpenCV frame (BGR format)
        quality: JPEG quality (1-100)

    Returns:
        Base64 encoded string
    """
    # Convert BGR to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Create PIL Image
    image = Image.fromarray(rgb_frame)

    # Encode to JPEG
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)

    # Convert to base64
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def encode_frame_to_bytes(frame: np.ndarray, quality: int = 85) -> bytes:
    """
    Encode a numpy frame to JPEG bytes.

    Args:
        frame: OpenCV frame (BGR format)
        quality: JPEG quality (1-100)

    Returns:
        JPEG bytes
    """
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    _, buffer = cv2.imencode(".jpg", frame, encode_param)
    return buffer.tobytes()


def build_event_collage(
    frames: Sequence[np.ndarray],
    labels: Sequence[str],
    camera_name: str,
    timestamp: datetime,
    is_thermal: bool = False,
) -> np.ndarray:
    """Build a left-to-right collage with overlays for event frames."""
    if not frames:
        raise ValueError("No frames provided for collage")
    if len(frames) != len(labels):
        raise ValueError("Frame and label counts must match")

    base_height, base_width = frames[0].shape[:2]
    timestamp_text = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    total = len(frames)
    output_frames = []

    for index, frame in enumerate(frames):
        resized = cv2.resize(frame, (base_width, base_height))
        overlay = resized.copy()

        label_text = f"{camera_name} | {timestamp_text} | {index + 1}/{total} {labels[index]}"
        cv2.putText(
            overlay,
            label_text,
            (10, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        if is_thermal:
            min_val = float(resized.min())
            max_val = float(resized.max())
            temp_text = f"Temp min/max: {min_val:.1f}/{max_val:.1f}"
            cv2.putText(
                overlay,
                temp_text,
                (10, base_height - 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

        output_frames.append(overlay)

    return cv2.hconcat(output_frames)


def decode_base64_to_frame(base64_string: str) -> np.ndarray:
    """
    Decode a base64 string to numpy frame.

    Args:
        base64_string: Base64 encoded JPEG string

    Returns:
        OpenCV frame (BGR format)
    """
    image_data = base64.b64decode(base64_string)
    nparr = np.frombuffer(image_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


def timestamp_now() -> str:
    """Get current timestamp as ISO format string."""
    return datetime.now().isoformat()


def timestamp_filename() -> str:
    """Get current timestamp formatted for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator for retrying async functions.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts
        backoff: Multiplier for delay after each attempt
        exceptions: Tuple of exceptions to catch

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff

            raise last_exception

        return wrapper
    return decorator


class RateLimiter:
    """Simple rate limiter for async operations."""

    def __init__(self, min_interval: float):
        """
        Initialize rate limiter.

        Args:
            min_interval: Minimum seconds between operations
        """
        self.min_interval = min_interval
        self.last_time: Optional[float] = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until rate limit allows next operation."""
        async with self._lock:
            if self.last_time is not None:
                elapsed = asyncio.get_event_loop().time() - self.last_time
                if elapsed < self.min_interval:
                    # Add a tiny buffer to avoid timing jitter in tests.
                    await asyncio.sleep(self.min_interval - elapsed + 0.005)
                    self.last_time = self.last_time + self.min_interval
                    return

            self.last_time = asyncio.get_event_loop().time()

    async def __aenter__(self) -> "RateLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass
