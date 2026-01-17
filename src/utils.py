"""Utility functions for Smart Motion Detector."""

import asyncio
import base64
import io
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

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


def mask_url(url: str) -> str:
    """
    Mask sensitive information in URLs (passwords, tokens).

    Args:
        url: URL string that may contain sensitive information

    Returns:
        URL with masked sensitive parts (e.g., rtsp://user:***@host/path)
    """
    if not url:
        return url
    
    if '@' in url:
        # Mask password in URL: rtsp://user:pass@host -> rtsp://user:***@host
        import re
        # Match pattern: scheme://user:password@host
        pattern = r'(://[^:]+:)([^@]+)(@)'
        masked_url = re.sub(pattern, r'\1***\3', url)
        return masked_url
    
    return url


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
                    await asyncio.sleep(self.min_interval - elapsed)

            self.last_time = asyncio.get_event_loop().time()

    async def __aenter__(self) -> "RateLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass
