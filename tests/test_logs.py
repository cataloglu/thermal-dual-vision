"""
Unit tests for logs service.

Tests cover:
- Get logs
- Line limiting
- File not found handling
- File size calculation
"""
import tempfile
from pathlib import Path
import pytest

from app.services.logs import LogsService, get_logs_service


@pytest.fixture
def temp_log_file():
    """Create temporary log file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix=".log", delete=False, encoding='utf-8') as f:
        # Write test log lines
        for i in range(300):
            f.write(f"2026-01-20 10:00:{i:02d} - INFO - Test log line {i}\n")
        path = Path(f.name)
    
    yield path
    
    if path.exists():
        path.unlink()


@pytest.fixture
def logs_service(temp_log_file):
    """Create logs service with temp file."""
    return LogsService(log_file=temp_log_file)


def test_logs_service_singleton():
    """Test that get_logs_service returns singleton instance."""
    service1 = get_logs_service()
    service2 = get_logs_service()
    
    assert service1 is service2


def test_get_logs_default(logs_service):
    """Test get logs with default limit (200)."""
    logs = logs_service.get_logs()
    
    assert len(logs) == 200
    assert "Test log line 100" in logs[0]
    assert "Test log line 299" in logs[-1]


def test_get_logs_custom_limit(logs_service):
    """Test get logs with custom limit."""
    logs = logs_service.get_logs(lines=50)
    
    assert len(logs) == 50
    assert "Test log line 250" in logs[0]
    assert "Test log line 299" in logs[-1]


def test_get_logs_limit_exceeds_total(logs_service):
    """Test get logs when limit exceeds total lines."""
    logs = logs_service.get_logs(lines=500)
    
    # Should return all 300 lines
    assert len(logs) == 300
    assert "Test log line 0" in logs[0]
    assert "Test log line 299" in logs[-1]


def test_get_logs_file_not_found():
    """Test get logs when file doesn't exist."""
    service = LogsService(log_file=Path("/non/existent/file.log"))
    logs = service.get_logs()
    
    assert len(logs) == 1
    assert "not found" in logs[0].lower()


def test_get_log_file_size(logs_service):
    """Test log file size calculation."""
    size = logs_service.get_log_file_size()
    
    assert size > 0


def test_get_log_file_size_not_found():
    """Test log file size when file doesn't exist."""
    service = LogsService(log_file=Path("/non/existent/file.log"))
    size = service.get_log_file_size()
    
    assert size == 0


def test_logs_no_newlines(logs_service):
    """Test that log lines have newlines stripped."""
    logs = logs_service.get_logs(lines=10)
    
    for log in logs:
        assert not log.endswith('\n')
        assert not log.endswith('\r')
