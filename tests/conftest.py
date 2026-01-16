"""Shared pytest fixtures for all tests."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest

from src.config import LLMConfig, MQTTConfig, TelegramConfig
from src.llm_analyzer import ScreenshotSet


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
def mqtt_config():
    """Create test MQTT configuration."""
    return MQTTConfig(
        host="test-broker",
        port=1883,
        username="test_user",
        password="test_pass",
        topic_prefix="test_motion",
        discovery=True,
        discovery_prefix="homeassistant",
        qos=1
    )


@pytest.fixture
def telegram_config():
    """Create test Telegram configuration."""
    return TelegramConfig(
        bot_token="test_token_123",
        chat_ids=["123456789", "987654321"],
        rate_limit_seconds=5,
        send_images=True
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


@pytest.fixture
def mock_aiomqtt():
    """Mock asyncio_mqtt module."""
    with patch("src.mqtt_client.aiomqtt") as mock:
        # Create mock client
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.publish = AsyncMock()

        # Create mock Will class
        mock_will = Mock()
        mock.Will = Mock(return_value=mock_will)

        # Mock Client constructor
        mock.Client = Mock(return_value=mock_client)

        yield mock


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAI client for testing."""
    mock_client = AsyncMock()

    # Setup default successful response
    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "gercek_hareket": True,
        "guven_skoru": 0.85,
        "degisiklik_aciklamasi": "Test detection",
        "tespit_edilen_nesneler": ["test"],
        "tehdit_seviyesi": "dusuk",
        "onerilen_aksiyon": "Test action",
        "detayli_analiz": "Test analysis"
    })

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    return mock_client


@pytest.fixture
def mock_telegram_bot():
    """Create mock Telegram bot for testing."""
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()
    mock_bot.send_photo = AsyncMock()
    mock_bot.send_document = AsyncMock()
    return mock_bot


@pytest.fixture
def mock_camera_frame():
    """Create a simple test camera frame."""
    # Create a 640x480 BGR image (standard camera resolution)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add some simple pattern to make it non-uniform
    frame[100:380, 200:440] = [100, 100, 100]  # Gray rectangle
    return frame


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
