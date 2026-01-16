"""Tests for LLM Vision Analyzer."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.config import LLMConfig
from src.llm_analyzer import (
    AnalysisResult,
    JSONParseError,
    LLMAnalyzer,
    LLMAnalyzerError,
    ScreenshotSet,
)


@pytest.fixture
def llm_config():
    """Create test LLM configuration."""
    return LLMConfig(
        api_key="test-api-key",
        model="gpt-4-vision-preview",
        max_tokens=1000,
        timeout=30
    )


@pytest.fixture
def sample_screenshot_set():
    """Create sample screenshot set for testing."""
    # Create simple test images (100x100 BGR)
    before = np.zeros((100, 100, 3), dtype=np.uint8)
    now = np.ones((100, 100, 3), dtype=np.uint8) * 128
    after = np.ones((100, 100, 3), dtype=np.uint8) * 255

    return ScreenshotSet(
        before=before,
        now=now,
        after=after,
        timestamp=datetime.now()
    )


@pytest.fixture
def valid_response_json():
    """Create valid JSON response from LLM."""
    return {
        "gercek_hareket": True,
        "guven_skoru": 0.85,
        "degisiklik_aciklamasi": "Bir insan görüntüye girdi",
        "tespit_edilen_nesneler": ["insan", "köpek"],
        "tehdit_seviyesi": "dusuk",
        "onerilen_aksiyon": "İzlemeye devam et",
        "detayli_analiz": "Bir kişi bahçeden geçiyor, yanında bir köpek var."
    }


class TestAnalysisResultDataclass:
    """Tests for AnalysisResult dataclass."""

    def test_analysis_result_creation(self, valid_response_json):
        """Test creating AnalysisResult with all fields."""
        result = AnalysisResult(
            gercek_hareket=valid_response_json["gercek_hareket"],
            guven_skoru=valid_response_json["guven_skoru"],
            degisiklik_aciklamasi=valid_response_json["degisiklik_aciklamasi"],
            tespit_edilen_nesneler=valid_response_json["tespit_edilen_nesneler"],
            tehdit_seviyesi=valid_response_json["tehdit_seviyesi"],
            onerilen_aksiyon=valid_response_json["onerilen_aksiyon"],
            detayli_analiz=valid_response_json["detayli_analiz"],
            raw_response=valid_response_json,
            processing_time=1.5
        )

        assert result.gercek_hareket is True
        assert result.guven_skoru == 0.85
        assert result.degisiklik_aciklamasi == "Bir insan görüntüye girdi"
        assert result.tespit_edilen_nesneler == ["insan", "köpek"]
        assert result.tehdit_seviyesi == "dusuk"
        assert result.onerilen_aksiyon == "İzlemeye devam et"
        assert "kişi" in result.detayli_analiz
        assert result.raw_response == valid_response_json
        assert result.processing_time == 1.5

    def test_analysis_result_with_no_motion(self):
        """Test AnalysisResult when no motion detected."""
        result = AnalysisResult(
            gercek_hareket=False,
            guven_skoru=0.95,
            degisiklik_aciklamasi="Değişiklik yok",
            tespit_edilen_nesneler=[],
            tehdit_seviyesi="yok",
            onerilen_aksiyon="İzlemeye devam et",
            detayli_analiz="Görüntülerde anlamlı bir değişiklik tespit edilmedi.",
            raw_response={},
            processing_time=0.8
        )

        assert result.gercek_hareket is False
        assert result.tespit_edilen_nesneler == []
        assert result.tehdit_seviyesi == "yok"


class TestScreenshotSet:
    """Tests for ScreenshotSet dataclass."""

    def test_screenshot_set_creation(self, sample_screenshot_set):
        """Test creating ScreenshotSet."""
        assert sample_screenshot_set.before is not None
        assert sample_screenshot_set.now is not None
        assert sample_screenshot_set.after is not None
        assert sample_screenshot_set.timestamp is not None

    def test_screenshot_set_without_after(self):
        """Test ScreenshotSet with after=None."""
        before = np.zeros((100, 100, 3), dtype=np.uint8)
        now = np.ones((100, 100, 3), dtype=np.uint8) * 128

        screenshot_set = ScreenshotSet(
            before=before,
            now=now,
            after=None,
            timestamp=datetime.now()
        )

        assert screenshot_set.before is not None
        assert screenshot_set.now is not None
        assert screenshot_set.after is None


class TestLLMAnalyzerInit:
    """Tests for LLMAnalyzer initialization."""

    @patch("src.llm_analyzer.AsyncOpenAI")
    def test_analyzer_initialization(self, mock_openai_class, llm_config):
        """Test LLMAnalyzer initialization."""
        analyzer = LLMAnalyzer(llm_config)

        assert analyzer.config == llm_config
        assert analyzer.system_prompt is not None
        assert "güvenlik kamerası" in analyzer.system_prompt
        assert analyzer.rate_limiter is not None
        mock_openai_class.assert_called_once_with(
            api_key="test-api-key",
            timeout=30
        )


class TestLLMAnalyzerAnalyze:
    """Tests for LLMAnalyzer.analyze method."""

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_successful_analysis(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set,
        valid_response_json
    ):
        """Test successful LLM analysis with valid response."""
        # Setup mocks
        mock_encode.return_value = "base64encodedimage"

        mock_message = MagicMock()
        mock_message.content = json.dumps(valid_response_json)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        # Create analyzer and run analysis
        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(sample_screenshot_set)

        # Verify result
        assert isinstance(result, AnalysisResult)
        assert result.gercek_hareket is True
        assert result.guven_skoru == 0.85
        assert "insan" in result.tespit_edilen_nesneler
        assert result.tehdit_seviyesi == "dusuk"
        assert result.processing_time > 0

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_analysis_without_after_screenshot(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        valid_response_json
    ):
        """Test analysis when after screenshot is None."""
        mock_encode.return_value = "base64encodedimage"

        mock_message = MagicMock()
        mock_message.content = json.dumps(valid_response_json)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        # Create screenshot set without after
        before = np.zeros((100, 100, 3), dtype=np.uint8)
        now = np.ones((100, 100, 3), dtype=np.uint8) * 128
        screenshot_set = ScreenshotSet(
            before=before,
            now=now,
            after=None,
            timestamp=datetime.now()
        )

        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(screenshot_set)

        assert isinstance(result, AnalysisResult)
        # encode_frame_to_base64 should be called only 2 times (before, now)
        assert mock_encode.call_count == 2

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_json_parsing_with_default_values(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test JSON parsing with missing fields uses defaults."""
        mock_encode.return_value = "base64encodedimage"

        # Response with only some fields
        partial_response = {
            "gercek_hareket": True,
            "guven_skoru": 0.9
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(partial_response)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(sample_screenshot_set)

        # Check defaults are applied
        assert result.gercek_hareket is True
        assert result.guven_skoru == 0.9
        assert result.degisiklik_aciklamasi == ""  # Default
        assert result.tespit_edilen_nesneler == []  # Default
        assert result.tehdit_seviyesi == "yok"  # Default
        assert result.onerilen_aksiyon == ""  # Default
        assert result.detayli_analiz == ""  # Default


class TestLLMAnalyzerErrorHandling:
    """Tests for LLMAnalyzer error handling."""

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_json_parse_error(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test JSONParseError is raised for invalid JSON."""
        mock_encode.return_value = "base64encodedimage"

        mock_message = MagicMock()
        mock_message.content = "This is not valid JSON"

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)

        with pytest.raises(JSONParseError) as exc_info:
            await analyzer.analyze(sample_screenshot_set)

        assert "This is not valid JSON" in exc_info.value.response_text

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_rate_limit_error(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test LLMAnalyzerError is raised for rate limit."""
        from openai import RateLimitError

        mock_encode.return_value = "base64encodedimage"

        mock_client = AsyncMock()
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                message="Rate limit exceeded",
                response=mock_response,
                body=None
            )
        )
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)

        with pytest.raises(LLMAnalyzerError) as exc_info:
            await analyzer.analyze(sample_screenshot_set)

        assert "Rate limit" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_api_timeout_error(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test LLMAnalyzerError is raised for API timeout."""
        from openai import APITimeoutError

        mock_encode.return_value = "base64encodedimage"

        mock_client = AsyncMock()
        mock_request = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError(request=mock_request)
        )
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)

        with pytest.raises(LLMAnalyzerError) as exc_info:
            await analyzer.analyze(sample_screenshot_set)

        assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_api_connection_error(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test LLMAnalyzerError is raised for connection error."""
        from openai import APIConnectionError

        mock_encode.return_value = "base64encodedimage"

        mock_client = AsyncMock()
        mock_request = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(request=mock_request)
        )
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)

        with pytest.raises(LLMAnalyzerError) as exc_info:
            await analyzer.analyze(sample_screenshot_set)

        assert "connection error" in str(exc_info.value)


class TestLLMAnalyzerRetry:
    """Tests for LLMAnalyzer.analyze_with_retry method."""

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_retry_success_on_first_attempt(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set,
        valid_response_json
    ):
        """Test analyze_with_retry succeeds on first attempt."""
        mock_encode.return_value = "base64encodedimage"

        mock_message = MagicMock()
        mock_message.content = json.dumps(valid_response_json)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze_with_retry(sample_screenshot_set, max_retries=3)

        assert isinstance(result, AnalysisResult)
        assert mock_client.chat.completions.create.call_count == 1

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.asyncio.sleep", new_callable=AsyncMock)
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_retry_success_after_failures(
        self,
        mock_openai_class,
        mock_encode,
        mock_sleep,
        llm_config,
        sample_screenshot_set,
        valid_response_json
    ):
        """Test analyze_with_retry succeeds after transient failures."""
        from openai import APIConnectionError

        mock_encode.return_value = "base64encodedimage"

        mock_message = MagicMock()
        mock_message.content = json.dumps(valid_response_json)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_request = MagicMock()
        # Fail twice, then succeed
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                APIConnectionError(request=mock_request),
                APIConnectionError(request=mock_request),
                mock_response
            ]
        )
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze_with_retry(sample_screenshot_set, max_retries=3)

        assert isinstance(result, AnalysisResult)
        assert mock_client.chat.completions.create.call_count == 3
        # Sleep should be called for exponential backoff (at least 2 times for retries)
        # Note: may be called more times due to rate limiter
        assert mock_sleep.call_count >= 2

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.asyncio.sleep", new_callable=AsyncMock)
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_retry_exhausted(
        self,
        mock_openai_class,
        mock_encode,
        mock_sleep,
        llm_config,
        sample_screenshot_set
    ):
        """Test analyze_with_retry raises after all retries exhausted."""
        from openai import APIConnectionError

        mock_encode.return_value = "base64encodedimage"

        mock_client = AsyncMock()
        mock_request = MagicMock()
        # Always fail
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(request=mock_request)
        )
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)

        with pytest.raises(LLMAnalyzerError):
            await analyzer.analyze_with_retry(sample_screenshot_set, max_retries=3)

        assert mock_client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_retry_does_not_retry_json_parse_error(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test analyze_with_retry does not retry JSONParseError."""
        mock_encode.return_value = "base64encodedimage"

        mock_message = MagicMock()
        mock_message.content = "invalid json"

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)

        with pytest.raises(JSONParseError):
            await analyzer.analyze_with_retry(sample_screenshot_set, max_retries=3)

        # Should only be called once (no retries)
        assert mock_client.chat.completions.create.call_count == 1
