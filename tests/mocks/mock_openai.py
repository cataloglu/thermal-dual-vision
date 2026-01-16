"""Mock OpenAI client for testing LLM functionality."""

import json
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock


class MockOpenAI:
    """
    Mock OpenAI client that simulates AsyncOpenAI API for testing.

    Provides controllable fake LLM responses with options for generating
    valid JSON responses, different error conditions, and various response scenarios.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        response_json: Optional[Dict[str, Any]] = None,
        response_text: Optional[str] = None,
        raise_rate_limit: bool = False,
        raise_timeout: bool = False,
        raise_connection_error: bool = False,
        raise_api_error: bool = False
    ):
        """
        Initialize mock OpenAI client.

        Args:
            api_key: API key (stored but not used)
            timeout: Timeout value (stored but not used)
            response_json: JSON dict to return as response content
            response_text: Raw text to return as response content (overrides response_json)
            raise_rate_limit: If True, raise RateLimitError
            raise_timeout: If True, raise APITimeoutError
            raise_connection_error: If True, raise APIConnectionError
            raise_api_error: If True, raise APIError
        """
        self.api_key = api_key
        self.timeout = timeout
        self.response_json = response_json or self._default_response()
        self.response_text = response_text
        self.raise_rate_limit = raise_rate_limit
        self.raise_timeout = raise_timeout
        self.raise_connection_error = raise_connection_error
        self.raise_api_error = raise_api_error

        # Create mock chat completions interface
        self.chat = MagicMock()
        self.chat.completions = MagicMock()
        self.chat.completions.create = AsyncMock(side_effect=self._create_completion)

    def _default_response(self) -> Dict[str, Any]:
        """
        Generate default LLM analysis response.

        Returns:
            Default JSON response dict for motion analysis
        """
        return {
            "gercek_hareket": True,
            "guven_skoru": 0.85,
            "degisiklik_aciklamasi": "Test motion detected",
            "tespit_edilen_nesneler": ["test_object"],
            "tehdit_seviyesi": "dusuk",
            "onerilen_aksiyon": "İzlemeye devam et",
            "detayli_analiz": "This is a test analysis"
        }

    async def _create_completion(self, **kwargs: Any) -> MagicMock:
        """
        Mock the chat.completions.create() method.

        Args:
            **kwargs: Arguments passed to create() (stored but not used)

        Returns:
            Mock response object with choices and message structure

        Raises:
            Various OpenAI exceptions based on configuration
        """
        # Simulate errors if configured
        if self.raise_rate_limit:
            from openai import RateLimitError
            raise RateLimitError(
                "Rate limit exceeded",
                response=MagicMock(status_code=429),
                body=None
            )

        if self.raise_timeout:
            from openai import APITimeoutError
            raise APITimeoutError(request=MagicMock())

        if self.raise_connection_error:
            from openai import APIConnectionError
            raise APIConnectionError(message="Connection failed", request=MagicMock())

        if self.raise_api_error:
            from openai import APIError
            raise APIError(
                "API error occurred",
                request=MagicMock(),
                body=None
            )

        # Build response content
        if self.response_text is not None:
            content = self.response_text
        else:
            content = json.dumps(self.response_json)

        # Create mock message structure
        mock_message = MagicMock()
        mock_message.content = content

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        return mock_response

    def set_response_json(self, response_json: Dict[str, Any]) -> None:
        """
        Update the JSON response to return.

        Args:
            response_json: New JSON dict to return as response content
        """
        self.response_json = response_json
        self.response_text = None

    def set_response_text(self, response_text: str) -> None:
        """
        Update the raw text response to return.

        Args:
            response_text: New raw text to return as response content
        """
        self.response_text = response_text

    def set_error_mode(
        self,
        rate_limit: bool = False,
        timeout: bool = False,
        connection_error: bool = False,
        api_error: bool = False
    ) -> None:
        """
        Configure which errors to raise.

        Args:
            rate_limit: If True, raise RateLimitError
            timeout: If True, raise APITimeoutError
            connection_error: If True, raise APIConnectionError
            api_error: If True, raise APIError
        """
        self.raise_rate_limit = rate_limit
        self.raise_timeout = timeout
        self.raise_connection_error = connection_error
        self.raise_api_error = api_error

    @staticmethod
    def create_valid_motion_response(
        gercek_hareket: bool = True,
        guven_skoru: float = 0.85,
        nesneler: Optional[list] = None,
        tehdit: str = "dusuk"
    ) -> Dict[str, Any]:
        """
        Create a valid motion analysis response with custom values.

        Args:
            gercek_hareket: Whether real motion was detected
            guven_skoru: Confidence score (0.0-1.0)
            nesneler: List of detected objects
            tehdit: Threat level (yok|dusuk|orta|yuksek)

        Returns:
            Valid JSON response dict for motion analysis
        """
        if nesneler is None:
            nesneler = ["insan"] if gercek_hareket else []

        return {
            "gercek_hareket": gercek_hareket,
            "guven_skoru": guven_skoru,
            "degisiklik_aciklamasi": "Test motion analysis",
            "tespit_edilen_nesneler": nesneler,
            "tehdit_seviyesi": tehdit,
            "onerilen_aksiyon": "İzlemeye devam et",
            "detayli_analiz": "Detailed test analysis"
        }

    @staticmethod
    def create_no_motion_response() -> Dict[str, Any]:
        """
        Create a response indicating no motion detected.

        Returns:
            JSON response dict for no motion scenario
        """
        return {
            "gercek_hareket": False,
            "guven_skoru": 0.95,
            "degisiklik_aciklamasi": "Değişiklik yok",
            "tespit_edilen_nesneler": [],
            "tehdit_seviyesi": "yok",
            "onerilen_aksiyon": "İzlemeye devam et",
            "detayli_analiz": "Görüntülerde anlamlı bir değişiklik tespit edilmedi."
        }
