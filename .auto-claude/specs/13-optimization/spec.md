# 13 - Optimization

## Overview
Performans optimizasyonu ve kaynak yönetimi. Memory leak önleme, CPU kullanımı azaltma, inference hızlandırma.

## Workflow Type
**refactor** - Performans iyileştirme

## Task Scope
Tüm modüllerde performans optimizasyonu ve monitoring.

### Optimizasyon Alanları

#### Memory
- Ring buffer boyut optimizasyonu
- JPEG compression ayarları
- Frame resize (processing için küçült)
- Garbage collection tuning
- Numpy array reuse

#### CPU
- Multi-threading (camera, processing)
- Frame skip (high load durumunda)
- Lazy initialization
- Connection pooling

#### Network
- MQTT message batching
- Telegram rate limiting
- OpenAI request caching
- Connection keep-alive

### Performance Metrics
```python
@dataclass
class PerformanceMetrics:
    fps: float
    memory_mb: float
    cpu_percent: float
    inference_ms: float
    queue_size: int
    uptime_seconds: float
```

### Hedefler
| Metric | Target |
|--------|--------|
| FPS | >= 5 |
| Memory | < 512MB |
| CPU | < 50% (single core) |
| YOLO inference | < 500ms |
| LLM response | < 10s |

## Requirements
1. Performance monitoring modülü
2. Memory profiling ve optimization
3. CPU profiling ve optimization
4. Frame skip mekanizması
5. Caching layer
6. Health metrics endpoint

## Files to Modify
- `src/motion_detector.py` - Frame skip, buffer optimization
- `src/yolo_detector.py` - Batch inference, model optimization
- `src/screenshot_manager.py` - Memory management
- `src/llm_analyzer.py` - Response caching

## Files to Reference
- Tüm `src/` modülleri

## Success Criteria
- [ ] Memory leak yok (24h test)
- [ ] CPU kullanımı hedef altında
- [ ] FPS stabil
- [ ] Metrics endpoint aktif
- [ ] Long-running test geçiyor

## QA Acceptance Criteria
- 24 saat continuous run testi
- Memory profiling (tracemalloc)
- CPU profiling (cProfile)
- Load testing

## Dependencies
- 08-main-app
- 09-testing

## Notes
- Profiling: py-spy, memory_profiler
- Monitoring: prometheus_client opsiyonel
- Grafana dashboard opsiyonel
