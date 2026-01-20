"""
Unit tests for AI service.

Tests cover:
- OpenAI API integration
- Prompt hierarchy (camera > global > template > default)
- AI enabled/disabled graceful handling
- API key validation
- Image encoding
"""
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import pytest

from app.services.ai import AIService, get_ai_service


@pytest.fixture
def ai_service():
    """Create AI service instance."""
    return AIService()


@pytest.fixture
def mock_config():
    """Create mock config."""
    config = Mock()
    config.ai = Mock()
    config.ai.enabled = True
    config.ai.api_key = "sk-test-key"
    config.ai.model = "gpt-4o"
    config.ai.max_tokens = 200
    config.ai.temperature = 0.3
    config.ai.prompt_template = "security_focused"
    config.ai.custom_prompt = None
    return config


@pytest.fixture
def test_event():
    """Create test event."""
    return {
        "id": "test-event-1",
        "camera_id": "cam-1",
        "timestamp": "2026-01-20T14:30:00Z",
        "confidence": 0.85,
    }


@pytest.fixture
def test_camera():
    """Create test camera."""
    return {
        "id": "cam-1",
        "name": "Front Door",
        "use_custom_prompt": False,
        "ai_prompt_override": None,
    }


@pytest.fixture
def test_image():
    """Create test image file."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        # Write minimal JPEG header
        f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00')
        f.write(b'\xff\xd9')  # End of image
        path = Path(f.name)
    
    yield path
    
    # Cleanup
    if path.exists():
        path.unlink()


def test_ai_service_singleton():
    """Test that get_ai_service returns singleton instance."""
    service1 = get_ai_service()
    service2 = get_ai_service()
    
    assert service1 is service2


def test_prompt_hierarchy_camera_level(ai_service, test_event, mock_config):
    """Test that camera-level prompt has highest priority."""
    camera = {
        "name": "Front Door",
        "use_custom_prompt": True,
        "ai_prompt_override": "Custom camera prompt for front door"
    }
    
    with patch.object(ai_service.settings_service, 'load_config', return_value=mock_config):
        prompt = ai_service._get_prompt_for_event(test_event, camera)
        
        assert "Custom camera prompt for front door" in prompt


def test_prompt_hierarchy_global_custom(ai_service, test_event, mock_config):
    """Test that global custom prompt is used when camera prompt not set."""
    camera = {
        "name": "Front Door",
        "use_custom_prompt": False,
        "ai_prompt_override": None
    }
    
    mock_config.ai.custom_prompt = "Global custom prompt"
    
    with patch.object(ai_service.settings_service, 'load_config', return_value=mock_config):
        prompt = ai_service._get_prompt_for_event(test_event, camera)
        
        assert "Global custom prompt" in prompt


def test_prompt_hierarchy_template(ai_service, test_event, mock_config):
    """Test that template is used when no custom prompts."""
    camera = {
        "name": "Front Door",
        "use_custom_prompt": False,
        "ai_prompt_override": None
    }
    
    mock_config.ai.custom_prompt = None
    mock_config.ai.prompt_template = "security_focused"
    
    with patch.object(ai_service.settings_service, 'load_config', return_value=mock_config):
        prompt = ai_service._get_prompt_for_event(test_event, camera)
        
        assert "güvenlik sistemi" in prompt.lower()
        assert "Front Door" in prompt


def test_prompt_hierarchy_default(ai_service, test_event, mock_config):
    """Test that default simple template is used as fallback."""
    camera = {
        "name": "Front Door",
        "use_custom_prompt": False,
        "ai_prompt_override": None
    }
    
    mock_config.ai.custom_prompt = None
    mock_config.ai.prompt_template = "unknown"
    
    with patch.object(ai_service.settings_service, 'load_config', return_value=mock_config):
        prompt = ai_service._get_prompt_for_event(test_event, camera)
        
        assert "thermal kamera" in prompt.lower()


def test_ai_disabled_graceful(ai_service, test_event, test_camera, test_image, mock_config):
    """Test that AI disabled returns None gracefully."""
    mock_config.ai.enabled = False
    
    with patch.object(ai_service.settings_service, 'load_config', return_value=mock_config):
        result = ai_service.analyze_event(test_event, test_image, test_camera)
        
        assert result is None


def test_api_key_missing(ai_service, test_event, test_camera, test_image, mock_config):
    """Test that missing API key returns None gracefully."""
    mock_config.ai.api_key = None
    
    with patch.object(ai_service.settings_service, 'load_config', return_value=mock_config):
        result = ai_service.analyze_event(test_event, test_image, test_camera)
        
        assert result is None


def test_api_key_redacted(ai_service, test_event, test_camera, test_image, mock_config):
    """Test that redacted API key returns None gracefully."""
    mock_config.ai.api_key = "***REDACTED***"
    
    with patch.object(ai_service.settings_service, 'load_config', return_value=mock_config):
        result = ai_service.analyze_event(test_event, test_image, test_camera)
        
        assert result is None


def test_image_encoding(ai_service, test_image):
    """Test image encoding to base64."""
    encoded = ai_service._encode_image(test_image)
    
    assert encoded is not None
    assert isinstance(encoded, str)
    assert len(encoded) > 0


def test_image_not_found(ai_service):
    """Test image encoding with non-existent file."""
    fake_path = Path("/non/existent/image.jpg")
    encoded = ai_service._encode_image(fake_path)
    
    assert encoded is None


@patch('app.services.ai.OpenAI')
def test_openai_api_call(mock_openai_class, ai_service, test_event, test_camera, test_image, mock_config):
    """Test OpenAI API call with mocked response."""
    # Mock OpenAI client and response
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = "1 kişi tespit edildi. Ön kapıda bekliyor. Tehdit: Düşük"
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai_class.return_value = mock_client
    
    with patch.object(ai_service.settings_service, 'load_config', return_value=mock_config):
        result = ai_service.analyze_event(test_event, test_image, test_camera)
        
        assert result is not None
        assert "1 kişi" in result
        assert "Düşük" in result
        
        # Verify API was called
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        
        # Verify model
        assert call_args.kwargs['model'] == "gpt-4o"
        
        # Verify messages structure
        messages = call_args.kwargs['messages']
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        
        # Verify image in content
        user_content = messages[1]['content']
        assert any(item['type'] == 'image_url' for item in user_content)


@patch('app.services.ai.OpenAI')
def test_openai_api_error(mock_openai_class, ai_service, test_event, test_camera, test_image, mock_config):
    """Test OpenAI API error handling."""
    # Mock API error
    mock_client = Mock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")
    mock_openai_class.return_value = mock_client
    
    with patch.object(ai_service.settings_service, 'load_config', return_value=mock_config):
        result = ai_service.analyze_event(test_event, test_image, test_camera)
        
        # Should return None on error
        assert result is None


def test_is_enabled_true(ai_service, mock_config):
    """Test is_enabled returns True when properly configured."""
    with patch.object(ai_service.settings_service, 'load_config', return_value=mock_config):
        assert ai_service.is_enabled() is True


def test_is_enabled_false_disabled(ai_service, mock_config):
    """Test is_enabled returns False when AI disabled."""
    mock_config.ai.enabled = False
    
    with patch.object(ai_service.settings_service, 'load_config', return_value=mock_config):
        assert ai_service.is_enabled() is False


def test_is_enabled_false_no_key(ai_service, mock_config):
    """Test is_enabled returns False when API key missing."""
    mock_config.ai.api_key = None
    
    with patch.object(ai_service.settings_service, 'load_config', return_value=mock_config):
        assert ai_service.is_enabled() is False


def test_prompt_formatting(ai_service, test_event, mock_config):
    """Test that prompt is properly formatted with event context."""
    camera = {
        "name": "Test Camera",
        "use_custom_prompt": False,
        "ai_prompt_override": None
    }
    
    mock_config.ai.custom_prompt = None
    mock_config.ai.prompt_template = "security_focused"
    
    with patch.object(ai_service.settings_service, 'load_config', return_value=mock_config):
        prompt = ai_service._get_prompt_for_event(test_event, camera)
        
        # Verify context is included
        assert "Test Camera" in prompt
        assert "2026-01-20" in prompt
        assert "85%" in prompt
