# 08 - Main Application

## Overview
Tüm modülleri birleştiren ana uygulama. Async event loop ile modülleri orkestre edecek, signal handling ile graceful shutdown sağlayacak.

## Workflow Type
**feature** - Ana uygulama geliştirme

## Task Scope
Modül orkestrasyonu, event flow yönetimi ve lifecycle management.

### Teknik Detaylar
```python
class SmartMotionDetector:
    def __init__(self, config: Config)
    async def start(self) -> None
    async def stop(self) -> None
    async def health_check(self) -> dict
    def arm(self) -> None
    def disarm(self) -> None
    def is_armed(self) -> bool

async def main():
    config = Config.from_env()
    app = SmartMotionDetector(config)
    await app.start()
```

### Event Flow
```
Motion Detected (callback)
    ↓
YOLO Detection
    ↓
Screenshot Capture (before + current)
    ↓
Wait for after_seconds
    ↓
Screenshot Capture (after)
    ↓
LLM Analysis
    ↓
MQTT Publish + Telegram Send (parallel)
```

### Health Check Response
```json
{
  "status": "healthy",
  "uptime": 3600,
  "armed": true,
  "last_detection": "2024-01-15T14:30:25",
  "camera_connected": true,
  "mqtt_connected": true,
  "components": {
    "motion_detector": "running",
    "yolo": "ready",
    "mqtt": "connected",
    "telegram": "connected"
  }
}
```

## Requirements
1. asyncio event loop
2. Signal handlers (SIGTERM, SIGINT)
3. Module initialization sequence
4. Motion callback -> full pipeline
5. Health check HTTP endpoint (port 8099)
6. Arm/disarm state management

## Files to Modify
- Yok

## Files to Reference
- Tüm src/ modülleri

## Success Criteria
- [ ] Tüm modüller başarıyla başlatılıyor
- [ ] Event flow doğru çalışıyor
- [ ] Graceful shutdown çalışıyor
- [ ] Error recovery aktif
- [ ] Health check endpoint çalışıyor
- [ ] Arm/disarm işlevi çalışıyor

## QA Acceptance Criteria
- Integration test: Full pipeline test
- Stress test: Continuous motion events
- Shutdown test: Clean resource release

## Dependencies
- 01-project-structure
- 02-motion-detection
- 03-yolo-integration
- 04-screenshot-system
- 05-llm-vision
- 06-mqtt-integration
- 07-telegram-bot

## Notes
- aiohttp ile basit HTTP server (health check)
- Context manager pattern kullanılabilir
- Logging her adımda
