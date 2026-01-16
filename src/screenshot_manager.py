"""Screenshot management for Smart Motion Detector."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ScreenshotSet:
    """A set of three screenshots captured around a motion event."""
    before: bytes
    current: bytes
    after: bytes
    timestamp: datetime
    before_base64: str
    current_base64: str
    after_base64: str
