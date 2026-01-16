"""LLM Vision Analyzer for Smart Motion Detector."""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from openai import (
    AsyncOpenAI,
    APIError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)

from src.config import LLMConfig
from src.logger import get_logger
from src.metrics import MetricsCollector
from src.utils import RateLimiter, encode_frame_to_base64

# Initialize logger
logger = get_logger("llm_analyzer")

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


class LLMAnalyzerError(Exception):
    """Base exception for LLM Analyzer errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        """
        Initialize LLM Analyzer error.

        Args:
            message: Error message
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error


class JSONParseError(LLMAnalyzerError):
    """Exception raised when JSON parsing fails."""

    def __init__(
        self,
        message: str,
        response_text: str,
        original_error: Optional[Exception] = None
    ) -> None:
        """
        Initialize JSON parse error.

        Args:
            message: Error message
            response_text: The raw response text that failed to parse
            original_error: Original JSON decode exception
        """
        super().__init__(message, original_error)
        self.response_text = response_text


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

    def __init__(
        self,
        config: LLMConfig,
        metrics_collector: Optional[MetricsCollector] = None
    ) -> None:
        """
        Initialize LLM Analyzer.

        Args:
            config: LLM configuration with API key, model, and settings
            metrics_collector: Optional metrics collector for performance tracking
        """
        self.config = config
        self.system_prompt = SYSTEM_PROMPT
        self.metrics_collector = metrics_collector

        # Initialize AsyncOpenAI client
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            timeout=config.timeout
        )

        # Initialize rate limiter (1 request per second minimum)
        self.rate_limiter = RateLimiter(min_interval=1.0)

    async def analyze(self, screenshots: ScreenshotSet) -> AnalysisResult:
        """
        Analyze motion screenshots using LLM vision.

        Args:
            screenshots: Set of before, now, and after screenshots

        Returns:
            AnalysisResult with LLM analysis

        Raises:
            LLMAnalyzerError: If API call fails (rate limit, timeout, connection error)
            JSONParseError: If response JSON parsing fails
        """
        start_time = time.time()

        # Encode images to base64
        before_b64 = encode_frame_to_base64(screenshots.before)
        now_b64 = encode_frame_to_base64(screenshots.now)

        # Build image content list
        image_content: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": "ÖNCE (Hareket algılanmadan önce):"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{before_b64}",
                    "detail": "low"
                }
            },
            {
                "type": "text",
                "text": "ŞİMDİ (Hareket algılandığı an):"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{now_b64}",
                    "detail": "low"
                }
            }
        ]

        # Add after screenshot if available
        if screenshots.after is not None:
            after_b64 = encode_frame_to_base64(screenshots.after)
            image_content.extend([
                {
                    "type": "text",
                    "text": "SONRA (Hareket algılandıktan sonra):"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{after_b64}",
                        "detail": "low"
                    }
                }
            ])

        # Wait for rate limiter and call OpenAI API with error handling
        try:
            async with self.rate_limiter:
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {
                            "role": "system",
                            "content": self.system_prompt
                        },
                        {
                            "role": "user",
                            "content": image_content
                        }
                    ],
                    max_tokens=self.config.max_tokens,
                    response_format={"type": "json_object"}
                )
        except RateLimitError as e:
            logger.error("OpenAI rate limit exceeded: %s", str(e))
            raise LLMAnalyzerError(
                f"Rate limit exceeded: {e}",
                original_error=e
            ) from e
        except APITimeoutError as e:
            logger.error("OpenAI API timeout: %s", str(e))
            raise LLMAnalyzerError(
                f"API request timed out: {e}",
                original_error=e
            ) from e
        except APIConnectionError as e:
            logger.error("OpenAI API connection error: %s", str(e))
            raise LLMAnalyzerError(
                f"API connection error: {e}",
                original_error=e
            ) from e
        except APIError as e:
            logger.error("OpenAI API error: %s", str(e))
            raise LLMAnalyzerError(
                f"API error: {e}",
                original_error=e
            ) from e

        # Parse response with error handling
        response_text = response.choices[0].message.content or "{}"
        try:
            raw_response = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse LLM response as JSON: %s. Response: %s",
                str(e),
                response_text[:200]
            )
            raise JSONParseError(
                f"Failed to parse response as JSON: {e}",
                response_text=response_text,
                original_error=e
            ) from e

        processing_time = time.time() - start_time
        logger.debug(
            "LLM analysis completed in %.2f seconds",
            processing_time
        )

        # Record metrics if collector is available
        if self.metrics_collector:
            self.metrics_collector.record_inference_time(processing_time * 1000)  # Convert to milliseconds

        # Create AnalysisResult from parsed response
        return AnalysisResult(
            gercek_hareket=raw_response.get("gercek_hareket", False),
            guven_skoru=float(raw_response.get("guven_skoru", 0.0)),
            degisiklik_aciklamasi=raw_response.get("degisiklik_aciklamasi", ""),
            tespit_edilen_nesneler=raw_response.get("tespit_edilen_nesneler", []),
            tehdit_seviyesi=raw_response.get("tehdit_seviyesi", "yok"),
            onerilen_aksiyon=raw_response.get("onerilen_aksiyon", ""),
            detayli_analiz=raw_response.get("detayli_analiz", ""),
            raw_response=raw_response,
            processing_time=processing_time
        )

    async def analyze_with_retry(
        self,
        screenshots: ScreenshotSet,
        max_retries: int = 3
    ) -> AnalysisResult:
        """
        Analyze motion screenshots with retry logic and exponential backoff.

        Args:
            screenshots: Set of before, now, and after screenshots
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            AnalysisResult with LLM analysis

        Raises:
            LLMAnalyzerError: If all retry attempts fail due to API errors
            JSONParseError: If response JSON parsing fails (not retried)
        """
        delay = 1.0  # Initial delay in seconds
        backoff = 2.0  # Exponential backoff multiplier
        last_exception: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                return await self.analyze(screenshots)
            except JSONParseError:
                # JSON parsing errors should not be retried
                logger.error("JSON parsing failed, not retrying")
                raise
            except LLMAnalyzerError as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(
                        "LLM analysis attempt %d/%d failed: %s. Retrying in %.1f seconds...",
                        attempt + 1,
                        max_retries,
                        str(e),
                        delay
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff
                else:
                    logger.error(
                        "LLM analysis failed after %d attempts: %s",
                        max_retries,
                        str(e)
                    )
            except Exception as e:
                # Catch any unexpected exceptions
                last_exception = LLMAnalyzerError(
                    f"Unexpected error during analysis: {e}",
                    original_error=e
                )
                logger.error("Unexpected error in LLM analysis: %s", str(e))
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= backoff

        # All retries exhausted, raise the last exception
        raise last_exception  # type: ignore[misc]
