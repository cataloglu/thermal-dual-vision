"""LLM Vision Analyzer for Smart Motion Detector."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


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
