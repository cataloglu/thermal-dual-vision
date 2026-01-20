"""
Unit tests for Telegram service.

Tests cover:
- Send event notification
- Rate limiting
- Cooldown mechanism
- Connection testing
- Message formatting
"""
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
import pytest

from app.services.telegram import TelegramService, get_telegram_service


@pytest.fixture
def telegram_service():
    """Create Telegram service instance."""
    return TelegramService()


@pytest.fixture
def mock_config():
    """Create mock config."""
    config = Mock()
    config.telegram = Mock()
    config.telegram.enabled = True
    config.telegram.bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    config.telegram.chat_ids = ["123456789"]
    config.telegram.rate_limit_seconds = 5
    config.telegram.cooldown_seconds = 5
    config.telegram.send_images = True
    return config


@pytest.fixture
def test_event():
    """Create test event."""
    return {
        "id": "test-event-1",
        "camera_id": "cam-1",
        "timestamp": "2026-01-20T14:30:00Z",
        "confidence": 0.85,
        "summary": "Person detected near entrance",
    }


@pytest.fixture
def test_camera():
    """Create test camera."""
    return {
        "id": "cam-1",
        "name": "Front Door",
    }


@pytest.fixture
def test_image():
    """Create test image file."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00')
        f.write(b'\xff\xd9')
        path = Path(f.name)
    
    yield path
    
    if path.exists():
        path.unlink()


def test_telegram_service_singleton():
    """Test that get_telegram_service returns singleton instance."""
    service1 = get_telegram_service()
    service2 = get_telegram_service()
    
    assert service1 is service2


@pytest.mark.asyncio
async def test_send_notification_disabled(telegram_service, test_event, test_camera, mock_config):
    """Test that notification is not sent when disabled."""
    mock_config.telegram.enabled = False
    
    with patch.object(telegram_service.settings_service, 'load_config', return_value=mock_config):
        result = await telegram_service.send_event_notification(test_event, test_camera)
        
        assert result is False


@pytest.mark.asyncio
async def test_send_notification_no_token(telegram_service, test_event, test_camera, mock_config):
    """Test that notification is not sent when token missing."""
    mock_config.telegram.bot_token = None
    
    with patch.object(telegram_service.settings_service, 'load_config', return_value=mock_config):
        result = await telegram_service.send_event_notification(test_event, test_camera)
        
        assert result is False


@pytest.mark.asyncio
async def test_send_notification_no_chat_ids(telegram_service, test_event, test_camera, mock_config):
    """Test that notification is not sent when no chat IDs."""
    mock_config.telegram.chat_ids = []
    
    with patch.object(telegram_service.settings_service, 'load_config', return_value=mock_config):
        result = await telegram_service.send_event_notification(test_event, test_camera)
        
        assert result is False


@pytest.mark.asyncio
@patch('app.services.telegram.Bot')
async def test_send_notification_success(mock_bot_class, telegram_service, test_event, test_camera, test_image, mock_config):
    """Test successful notification send."""
    # Mock bot
    mock_bot = AsyncMock()
    mock_bot.send_photo = AsyncMock()
    mock_bot_class.return_value = mock_bot
    
    with patch.object(telegram_service.settings_service, 'load_config', return_value=mock_config):
        result = await telegram_service.send_event_notification(
            test_event, 
            test_camera, 
            collage_path=test_image
        )
        
        assert result is True
        mock_bot.send_photo.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limiting(telegram_service, test_event, test_camera, mock_config):
    """Test rate limiting prevents rapid messages."""
    with patch.object(telegram_service.settings_service, 'load_config', return_value=mock_config):
        with patch('app.services.telegram.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            # First send should succeed
            result1 = await telegram_service.send_event_notification(test_event, test_camera)
            assert result1 is True
            
            # Second send immediately should be rate limited
            result2 = await telegram_service.send_event_notification(test_event, test_camera)
            assert result2 is False


def test_check_rate_limit(telegram_service):
    """Test rate limit checking."""
    camera_id = "cam-1"
    
    # First check should pass
    assert telegram_service._check_rate_limit(camera_id, 5) is True
    
    # Update rate limit
    telegram_service._update_rate_limit(camera_id)
    
    # Immediate check should fail
    assert telegram_service._check_rate_limit(camera_id, 5) is False


def test_check_cooldown(telegram_service):
    """Test cooldown checking."""
    camera_id = "cam-1"
    
    # First check should pass
    assert telegram_service._check_cooldown(camera_id, 5) is True
    
    # Set cooldown
    telegram_service._set_cooldown(camera_id, 5)
    
    # Immediate check should fail
    assert telegram_service._check_cooldown(camera_id, 5) is False


def test_message_formatting(telegram_service, test_event, test_camera):
    """Test message formatting."""
    message = telegram_service._format_message(test_event, test_camera)
    
    assert "Front Door" in message
    assert "85%" in message
    assert "Person detected" in message
    assert "🚨" in message


@pytest.mark.asyncio
@patch('app.services.telegram.Bot')
async def test_connection_test_success(mock_bot_class, telegram_service):
    """Test successful connection test."""
    # Mock bot
    mock_bot = AsyncMock()
    mock_me = Mock()
    mock_me.username = "test_bot"
    mock_bot.get_me = AsyncMock(return_value=mock_me)
    mock_bot.send_message = AsyncMock()
    mock_bot_class.return_value = mock_bot
    
    result = await telegram_service.test_connection("123456:ABC-DEF", ["123456789"])
    
    assert result["success"] is True
    assert result["bot_username"] == "test_bot"
    assert result["latency_ms"] is not None
    assert result["error_reason"] is None


@pytest.mark.asyncio
@patch('app.services.telegram.Bot')
async def test_connection_test_failure(mock_bot_class, telegram_service):
    """Test connection test with error."""
    # Mock bot to raise error
    mock_bot = AsyncMock()
    mock_bot.get_me = AsyncMock(side_effect=Exception("Invalid token"))
    mock_bot_class.return_value = mock_bot
    
    result = await telegram_service.test_connection("invalid", ["123456789"])
    
    assert result["success"] is False
    assert result["error_reason"] is not None


def test_is_enabled_true(telegram_service, mock_config):
    """Test is_enabled returns True when properly configured."""
    with patch.object(telegram_service.settings_service, 'load_config', return_value=mock_config):
        assert telegram_service.is_enabled() is True


def test_is_enabled_false_disabled(telegram_service, mock_config):
    """Test is_enabled returns False when disabled."""
    mock_config.telegram.enabled = False
    
    with patch.object(telegram_service.settings_service, 'load_config', return_value=mock_config):
        assert telegram_service.is_enabled() is False


def test_is_enabled_false_no_token(telegram_service, mock_config):
    """Test is_enabled returns False when token missing."""
    mock_config.telegram.bot_token = None
    
    with patch.object(telegram_service.settings_service, 'load_config', return_value=mock_config):
        assert telegram_service.is_enabled() is False


def test_is_enabled_false_no_chat_ids(telegram_service, mock_config):
    """Test is_enabled returns False when no chat IDs."""
    mock_config.telegram.chat_ids = []
    
    with patch.object(telegram_service.settings_service, 'load_config', return_value=mock_config):
        assert telegram_service.is_enabled() is False
