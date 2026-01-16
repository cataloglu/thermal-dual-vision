"""LLM Vision Analyzer for Smart Motion Detector."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from openai import AsyncOpenAI

from src.config import LLMConfig
from src.utils import RateLimiter

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray


# Turkish system prompt for security camera analysis
SYSTEM_PROMPT = """Sen bir güvenlik kamerası görüntü analiz uzmanısın. Sana 3 görüntü veriyorum:
1. ÖNCE: Hareket algılanmadan 3 saniye önce
2. ŞİMDİ: Hareket algılandığı an
3. SONRA: Hareket algılandıktan 3 saniye sonra

Bu 3 görüntüyü karşılaştırarak analiz et:

1. Gerçek bir hareket var mı? (Evet/Hayır)
2. Ne değişti? (Detaylı açıkla)
3. Tespit edilen nesneler neler?
4. Bu bir tehdit mi? (Yok/Düşük/Orta/Yüksek)
5. Önerilen aksiyon nedir?

Yanıtını şu JSON formatında ver:
{
  "gercek_hareket": true/false,
  "guven_skoru": 0.0-1.0,
  "degisiklik_aciklamasi": "...",
  "tespit_edilen_nesneler": ["insan", "araba", ...],
  "tehdit_seviyesi": "yok|dusuk|orta|yuksek",
  "onerilen_aksiyon": "...",
  "detayli_analiz": "..."
}"""


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


class LLMAnalyzer:
    """LLM Vision Analyzer for analyzing motion detection screenshots."""

    def __init__(self, config: LLMConfig) -> None:
        """
        Initialize LLM Analyzer.

        Args:
            config: LLM configuration with API key, model, and settings
        """
        self.config = config
        self.system_prompt = SYSTEM_PROMPT

        # Initialize AsyncOpenAI client
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            timeout=config.timeout
        )

        # Initialize rate limiter (1 request per second minimum)
        self.rate_limiter = RateLimiter(min_interval=1.0)
