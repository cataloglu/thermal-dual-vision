# 06 - MQTT Integration

## Overview
Home Assistant MQTT entegrasyonu. Auto-discovery protokolü ile HA'da otomatik entity oluşturma ve motion event'lerini publish etme.

## Workflow Type
**feature** - Yeni modül geliştirme

## Task Scope
MQTT broker bağlantısı, auto-discovery mesajları ve state publish işlemleri.

### Teknik Detaylar
```python
class MQTTClient:
    def __init__(self, config: MQTTConfig)
    async def connect(self) -> None
    async def disconnect(self) -> None
    async def publish_discovery(self) -> None
    async def publish_motion(self, detected: bool, analysis: Optional[AnalysisResult] = None) -> None
    async def publish_state(self, state: dict) -> None
    def on_connect(self, callback: Callable) -> None
    def on_disconnect(self, callback: Callable) -> None
```

### HA Auto-Discovery Topics
```
homeassistant/binary_sensor/smart_motion/motion/config
homeassistant/sensor/smart_motion/threat_level/config
homeassistant/sensor/smart_motion/last_analysis/config
homeassistant/sensor/smart_motion/confidence/config
```

### Discovery Payload Örneği
```json
{
  "name": "Smart Motion",
  "unique_id": "smart_motion_detector_motion",
  "state_topic": "smart_motion/motion/state",
  "device_class": "motion",
  "device": {
    "identifiers": ["smart_motion_detector"],
    "name": "Smart Motion Detector",
    "model": "v1.0",
    "manufacturer": "Custom"
  }
}
```

### Konfigürasyon
```yaml
mqtt:
  broker: "core-mosquitto"
  port: 1883
  username: ""
  password: ""
  topic_prefix: "smart_motion"
  discovery: true
  discovery_prefix: "homeassistant"
  qos: 1
```

## Requirements
1. paho-mqtt async wrapper
2. Auto-discovery config mesajları
3. Binary sensor (motion on/off)
4. Sensors (threat_level, confidence, last_analysis)
5. Reconnect on disconnect
6. Last Will Testament (LWT)

## Files to Modify
- Yok

## Files to Reference
- `src/config.py` - MQTTConfig dataclass
- `src/llm_analyzer.py` - AnalysisResult

## Success Criteria
- [ ] MQTT broker bağlantısı çalışıyor
- [ ] Auto-discovery mesajları gönderiliyor
- [ ] HA'da entity'ler görünüyor
- [ ] Motion state publish çalışıyor
- [ ] Reconnect mekanizması aktif
- [ ] QoS ayarı çalışıyor

## QA Acceptance Criteria
- Unit test: Mock broker ile message verification
- Integration test: Mosquitto ile gerçek test
- HA test: Entity'lerin doğru görünmesi

## Dependencies
- 01-project-structure
- 05-llm-vision

## Notes
- asyncio-mqtt veya aiomqtt kullanılabilir
- LWT: Disconnect olunca "unavailable" state
- Retain flag discovery mesajlarında true
