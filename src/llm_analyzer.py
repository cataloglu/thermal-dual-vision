"""LLM Vision Analyzer for Smart Motion Detector."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray


@dataclass
class ScreenshotSet:
    """Set of screenshots captured around a motion event."""
    before: Any  # NDArray[np.uint8] - Screenshot before motion
    now: Any  # NDArray[np.uint8] - Screenshot at motion detection
    after: Optional[Any]  # NDArray[np.uint8] - Screenshot after motion (may be None initially)
    timestamp: datetime  # When motion was detected


@dataclass
class AnalysisResult:
    """Result of LLM vision analysis of motion screenshots."""
    gercek_hareket: bool
    guven_skoru: float  # 0.0-1.0
    degisiklik_aciklamasi: str
    tespit_edilen_nesneler: List[str]
    tehdit_seviyesi: str  # yok|dusuk|orta|yuksek
    onerilen_aksiyon: str
    detayli_analiz: str
    raw_response: Dict[str, Any]
    processing_time: float
