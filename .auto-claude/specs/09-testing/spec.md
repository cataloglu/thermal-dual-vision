# 09 - Testing

## Overview
Pytest framework ile kapsamlı test suite. Unit testler, integration testler ve mock sistemleri.

## Workflow Type
**feature** - Test altyapısı geliştirme

## Task Scope
Test dosyaları, mock'lar ve pytest konfigürasyonu.

### Test Yapısı
```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_motion_detector.py
│   ├── test_yolo_detector.py
│   ├── test_screenshot_manager.py
│   ├── test_llm_analyzer.py
│   ├── test_mqtt_client.py
│   └── test_telegram_bot.py
├── integration/
│   ├── test_motion_to_yolo.py
│   ├── test_screenshot_to_llm.py
│   └── test_full_pipeline.py
└── mocks/
    ├── __init__.py
    ├── mock_camera.py
    └── mock_openai.py
```

### Mock Sınıfları
```python
class MockCamera:
    """Fake RTSP stream with test frames"""
    def read(self) -> Tuple[bool, np.ndarray]
    def generate_motion_frame(self) -> np.ndarray

class MockOpenAI:
    """Fake GPT-4V responses"""
    def set_response(self, response: dict) -> None
    async def chat_completions_create(self, **kwargs) -> dict

class MockMQTT:
    """Fake MQTT broker"""
    messages: List[Tuple[str, str]]
    async def publish(self, topic: str, payload: str) -> None
```

### pytest.ini
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
addopts = --cov=src --cov-report=html --cov-report=term-missing
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
```

## Requirements
1. pytest + pytest-asyncio + pytest-cov
2. Fixtures for common setup
3. Mock classes for external dependencies
4. Parametrized tests for edge cases
5. Coverage >= 80%

## Files to Modify
- Yok

## Files to Reference
- Tüm `src/` modülleri
- `.auto-claude/test_data/` örnek veriler

## Success Criteria
- [ ] Tüm modüller için unit test mevcut
- [ ] Mock sistemleri çalışıyor
- [ ] Integration testler geçiyor
- [ ] Coverage >= %80
- [ ] pytest çalıştırılabiliyor

## QA Acceptance Criteria
- `pytest` komutu tüm testleri geçmeli
- Coverage raporu oluşmalı
- CI/CD pipeline'da çalışmalı

## Dependencies
- 01-project-structure
- 02-07 arası tüm modüller

## Notes
- Test data `.auto-claude/test_data/` içinde
- Async testler için pytest-asyncio
- Mocking için unittest.mock
