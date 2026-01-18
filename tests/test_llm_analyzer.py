"""Tests for LLM Vision Analyzer."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

pytest.importorskip("openai")

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
    early = np.ones((100, 100, 3), dtype=np.uint8) * 64
    peak = np.ones((100, 100, 3), dtype=np.uint8) * 128
    late = np.ones((100, 100, 3), dtype=np.uint8) * 192
    after = np.ones((100, 100, 3), dtype=np.uint8) * 255

    return ScreenshotSet(
        before=before,
        early=early,
        peak=peak,
        late=late,
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
        assert sample_screenshot_set.early is not None
        assert sample_screenshot_set.peak is not None
        assert sample_screenshot_set.late is not None
        assert sample_screenshot_set.after is not None
        assert sample_screenshot_set.timestamp is not None

    def test_screenshot_set_full_sequence(self):
        """Test ScreenshotSet with all five frames."""
        before = np.zeros((100, 100, 3), dtype=np.uint8)
        early = np.ones((100, 100, 3), dtype=np.uint8) * 64
        peak = np.ones((100, 100, 3), dtype=np.uint8) * 128
        late = np.ones((100, 100, 3), dtype=np.uint8) * 192
        after = np.ones((100, 100, 3), dtype=np.uint8) * 255

        screenshot_set = ScreenshotSet(
            before=before,
            early=early,
            peak=peak,
            late=late,
            after=after,
            timestamp=datetime.now()
        )

        assert screenshot_set.before is not None
        assert screenshot_set.early is not None
        assert screenshot_set.peak is not None
        assert screenshot_set.late is not None
        assert screenshot_set.after is not None


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
    async def test_analysis_with_full_sequence(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        valid_response_json
    ):
        """Test analysis with all five screenshots."""
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

        # Create screenshot set with full sequence
        before = np.zeros((100, 100, 3), dtype=np.uint8)
        early = np.ones((100, 100, 3), dtype=np.uint8) * 64
        peak = np.ones((100, 100, 3), dtype=np.uint8) * 128
        late = np.ones((100, 100, 3), dtype=np.uint8) * 192
        after = np.ones((100, 100, 3), dtype=np.uint8) * 255
        screenshot_set = ScreenshotSet(
            before=before,
            early=early,
            peak=peak,
            late=late,
            after=after,
            timestamp=datetime.now()
        )

        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(screenshot_set)

        assert isinstance(result, AnalysisResult)
        # encode_frame_to_base64 should be called for all 5 frames
        assert mock_encode.call_count == 5

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


class TestLLMAnalyzerEdgeCases:
    """Tests for LLMAnalyzer edge cases."""

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_empty_response_content(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test handling of empty response content from LLM."""
        mock_encode.return_value = "base64encodedimage"

        mock_message = MagicMock()
        mock_message.content = ""  # Empty string response

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)

        # Empty string gets converted to "{}" in the code (line 244)
        # json.loads("{}") returns an empty dict, so defaults are used
        result = await analyzer.analyze(sample_screenshot_set)

        # All fields should have default values
        assert result.gercek_hareket is False
        assert result.guven_skoru == 0.0
        assert result.degisiklik_aciklamasi == ""
        assert result.tespit_edilen_nesneler == []
        assert result.tehdit_seviyesi == "yok"
        assert result.onerilen_aksiyon == ""
        assert result.detayli_analiz == ""

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_none_response_content(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test handling of None response content from LLM."""
        mock_encode.return_value = "base64encodedimage"

        mock_message = MagicMock()
        mock_message.content = None  # None response

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)

        # None gets converted to "{}" in the code (line 244)
        result = await analyzer.analyze(sample_screenshot_set)

        # All fields should have default values
        assert result.gercek_hareket is False
        assert result.guven_skoru == 0.0
        assert result.degisiklik_aciklamasi == ""
        assert result.tespit_edilen_nesneler == []

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_malformed_json_truncated(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test JSONParseError for truncated JSON response."""
        mock_encode.return_value = "base64encodedimage"

        mock_message = MagicMock()
        mock_message.content = '{"gercek_hareket": true, "guven_skoru":'  # Truncated

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

        assert "gercek_hareket" in exc_info.value.response_text

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_malformed_json_with_markdown(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test JSONParseError when LLM wraps JSON in markdown code block."""
        mock_encode.return_value = "base64encodedimage"

        mock_message = MagicMock()
        # Sometimes LLMs wrap JSON in markdown code blocks
        mock_message.content = '```json\n{"gercek_hareket": true}\n```'

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

        assert "```json" in exc_info.value.response_text

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_malformed_json_extra_text(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test JSONParseError when LLM adds extra text before JSON."""
        mock_encode.return_value = "base64encodedimage"

        mock_message = MagicMock()
        mock_message.content = 'Here is my analysis:\n{"gercek_hareket": true}'

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

        assert "Here is my analysis" in exc_info.value.response_text

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_missing_all_required_fields(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test handling when all required fields are missing."""
        mock_encode.return_value = "base64encodedimage"

        mock_message = MagicMock()
        mock_message.content = '{"extra_field": "unexpected"}'

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(sample_screenshot_set)

        # Should use defaults for all missing fields
        assert result.gercek_hareket is False
        assert result.guven_skoru == 0.0
        assert result.degisiklik_aciklamasi == ""
        assert result.tespit_edilen_nesneler == []
        assert result.tehdit_seviyesi == "yok"
        assert result.onerilen_aksiyon == ""
        assert result.detayli_analiz == ""
        assert result.raw_response == {"extra_field": "unexpected"}

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_missing_some_required_fields(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test handling when some required fields are missing."""
        mock_encode.return_value = "base64encodedimage"

        partial_response = {
            "gercek_hareket": True,
            "guven_skoru": 0.7,
            # Missing: degisiklik_aciklamasi, tespit_edilen_nesneler,
            # tehdit_seviyesi, onerilen_aksiyon, detayli_analiz
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

        # Provided fields should be used
        assert result.gercek_hareket is True
        assert result.guven_skoru == 0.7
        # Missing fields should use defaults
        assert result.degisiklik_aciklamasi == ""
        assert result.tespit_edilen_nesneler == []
        assert result.tehdit_seviyesi == "yok"
        assert result.onerilen_aksiyon == ""
        assert result.detayli_analiz == ""

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_wrong_field_types_guven_skoru_raises(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test ValueError is raised when guven_skoru has wrong type."""
        mock_encode.return_value = "base64encodedimage"

        # guven_skoru should be float but is string "high"
        wrong_types_response = {
            "gercek_hareket": True,
            "guven_skoru": "high",  # Should be float - this will raise ValueError
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(wrong_types_response)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)

        # float("high") raises ValueError
        with pytest.raises(ValueError):
            await analyzer.analyze(sample_screenshot_set)

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_wrong_field_types_string_for_bool(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test handling when gercek_hareket is string instead of bool."""
        mock_encode.return_value = "base64encodedimage"

        # gercek_hareket should be bool but is string "yes"
        wrong_types_response = {
            "gercek_hareket": "yes",  # Should be bool
            "guven_skoru": 0.8,
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(wrong_types_response)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)

        # The code doesn't validate types strictly - it just uses the values
        # "yes" is truthy string, assigned as-is
        result = await analyzer.analyze(sample_screenshot_set)
        assert result.gercek_hareket == "yes"

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_wrong_field_types_string_for_list(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test handling when tespit_edilen_nesneler is string instead of list."""
        mock_encode.return_value = "base64encodedimage"

        # tespit_edilen_nesneler should be list but is string
        wrong_types_response = {
            "gercek_hareket": True,
            "guven_skoru": 0.8,
            "tespit_edilen_nesneler": "insan, köpek",  # Should be list
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(wrong_types_response)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)

        # The code doesn't validate types - string is assigned as-is
        result = await analyzer.analyze(sample_screenshot_set)
        assert result.tespit_edilen_nesneler == "insan, köpek"

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_turkish_characters_in_response(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test handling of Turkish special characters in response."""
        mock_encode.return_value = "base64encodedimage"

        # Response with various Turkish special characters
        turkish_response = {
            "gercek_hareket": True,
            "guven_skoru": 0.95,
            "degisiklik_aciklamasi": "Şüpheli bir kişi görüntüye girdi",
            "tespit_edilen_nesneler": ["insan", "çanta", "şapka", "ğ", "ü", "ö", "ı"],
            "tehdit_seviyesi": "düşük",  # Note: using ü instead of u
            "onerilen_aksiyon": "İzlemeye devam edin, şüpheli aktiviteyi takip edin",
            "detayli_analiz": "Görüntülerde şüpheli bir şahıs tespit edildi. Üzerinde siyah çanta ve şapka var. İlerleyen görüntülerde şahsın bahçeden çıktığı görülmektedir."
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(turkish_response, ensure_ascii=False)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(sample_screenshot_set)

        # Verify Turkish characters are preserved correctly
        assert result.gercek_hareket is True
        assert result.guven_skoru == 0.95
        assert "Şüpheli" in result.degisiklik_aciklamasi
        assert "çanta" in result.tespit_edilen_nesneler
        assert "şapka" in result.tespit_edilen_nesneler
        assert "ğ" in result.tespit_edilen_nesneler
        assert "ü" in result.tespit_edilen_nesneler
        assert "ö" in result.tespit_edilen_nesneler
        assert "ı" in result.tespit_edilen_nesneler
        assert "İzleme" in result.onerilen_aksiyon
        assert "şüpheli" in result.onerilen_aksiyon
        assert "şahıs" in result.detayli_analiz
        assert "Üzerinde" in result.detayli_analiz

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_turkish_characters_unicode_escaped(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test handling of unicode-escaped Turkish characters."""
        mock_encode.return_value = "base64encodedimage"

        # Response with Turkish characters as unicode escapes
        turkish_response = {
            "gercek_hareket": True,
            "guven_skoru": 0.8,
            "degisiklik_aciklamasi": "Bir ki\u015fi g\u00f6r\u00fcnt\u00fcye girdi",  # kişi görüntüye
            "tespit_edilen_nesneler": ["insan", "\u00e7anta"],  # çanta
            "tehdit_seviyesi": "d\u00fc\u015f\u00fck",  # düşük
            "onerilen_aksiyon": "\u0130zlemeye devam et",  # İzlemeye
            "detayli_analiz": "G\u00f6r\u00fcnt\u00fclerde de\u011fi\u015fiklik var"  # Görüntülerde değişiklik
        }

        mock_message = MagicMock()
        # Use ensure_ascii=True to keep unicode escapes
        mock_message.content = json.dumps(turkish_response, ensure_ascii=True)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(sample_screenshot_set)

        # JSON parsing should correctly decode unicode escapes
        assert "kişi" in result.degisiklik_aciklamasi
        assert "görüntüye" in result.degisiklik_aciklamasi
        assert "çanta" in result.tespit_edilen_nesneler
        assert result.tehdit_seviyesi == "düşük"
        assert "İzleme" in result.onerilen_aksiyon
        assert "Görüntülerde" in result.detayli_analiz
        assert "değişiklik" in result.detayli_analiz

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_empty_objects_list(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test handling when tespit_edilen_nesneler is empty list."""
        mock_encode.return_value = "base64encodedimage"

        response_with_empty_list = {
            "gercek_hareket": False,
            "guven_skoru": 0.99,
            "degisiklik_aciklamasi": "Hiçbir değişiklik yok",
            "tespit_edilen_nesneler": [],
            "tehdit_seviyesi": "yok",
            "onerilen_aksiyon": "Bekle",
            "detayli_analiz": "Sahnede herhangi bir hareket tespit edilmedi."
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(response_with_empty_list)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(sample_screenshot_set)

        assert result.gercek_hareket is False
        assert result.tespit_edilen_nesneler == []
        assert len(result.tespit_edilen_nesneler) == 0

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_guven_skoru_boundary_values(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test guven_skoru with boundary values 0.0 and 1.0."""
        mock_encode.return_value = "base64encodedimage"

        # Test with exactly 0.0
        response_zero = {
            "gercek_hareket": False,
            "guven_skoru": 0.0,
            "degisiklik_aciklamasi": "",
            "tespit_edilen_nesneler": [],
            "tehdit_seviyesi": "yok",
            "onerilen_aksiyon": "",
            "detayli_analiz": ""
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(response_zero)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(sample_screenshot_set)

        assert result.guven_skoru == 0.0

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.encode_frame_to_base64")
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_guven_skoru_max_value(
        self,
        mock_openai_class,
        mock_encode,
        llm_config,
        sample_screenshot_set
    ):
        """Test guven_skoru with maximum value 1.0."""
        mock_encode.return_value = "base64encodedimage"

        response_max = {
            "gercek_hareket": True,
            "guven_skoru": 1.0,
            "degisiklik_aciklamasi": "Kesin hareket",
            "tespit_edilen_nesneler": ["insan"],
            "tehdit_seviyesi": "yuksek",
            "onerilen_aksiyon": "Alarm ver",
            "detayli_analiz": "Çok net bir hareket tespit edildi."
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(response_max)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        result = await analyzer.analyze(sample_screenshot_set)

        assert result.guven_skoru == 1.0
