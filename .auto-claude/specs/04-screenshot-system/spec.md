# 04 - Screenshot System

## Overview
Hareket algılandığında 3 ekran görüntüsü yakalama sistemi. Ring buffer kullanarak geçmiş frame'leri saklayacak ve hareket anında önce/şimdi/sonra şeklinde 3'lü set oluşturacak.

## Workflow Type
**feature** - Yeni modül geliştirme

## Task Scope
Frame buffering ve screenshot capture işlemlerini yöneten modül.

### Teknik Detaylar
```python
@dataclass
class ScreenshotSet:
    before: bytes       # JPEG bytes
    current: bytes      # JPEG bytes
    after: bytes        # JPEG bytes
    timestamp: datetime
    before_base64: str
    current_base64: str
    after_base64: str

class ScreenshotManager:
    def __init__(self, config: ScreenshotConfig)
    def add_frame(self, frame: np.ndarray, timestamp: datetime) -> None
    async def capture_sequence(self, current_frame: np.ndarray) -> ScreenshotSet
    def get_buffer_size(self) -> int
    def cleanup_old(self, max_count: int) -> int
```

### Konfigürasyon
```yaml
screenshots:
  before_seconds: 3
  after_seconds: 3
  quality: 85           # JPEG quality
  max_stored: 100
  buffer_seconds: 10    # Ring buffer size
```

## Requirements
1. collections.deque ile ring buffer
2. Frame + timestamp tuple saklama
3. before_seconds kadar geriye git
4. after_seconds kadar bekle ve yakala
5. JPEG encoding with quality setting
6. Base64 encoding for LLM API

## Files to Modify
- Yok

## Files to Reference
- `src/config.py` - ScreenshotConfig dataclass
- `src/utils.py` - encode_frame_to_base64, encode_frame_to_bytes
- `src/motion_detector.py` - Frame source

## Success Criteria
- [ ] Ring buffer doğru çalışıyor
- [ ] before frame doğru zamandan alınıyor
- [ ] after frame için bekleme çalışıyor
- [ ] JPEG encoding kaliteli
- [ ] Base64 encoding LLM için uygun
- [ ] Memory leak yok

## QA Acceptance Criteria
- Unit test: Buffer operations
- Integration test: Full capture sequence
- Memory test: 1 saat continuous buffering

## Dependencies
- 01-project-structure
- 02-motion-detection

## Notes
- deque(maxlen=buffer_size) kullanılacak
- asyncio.sleep() for after delay
- Thread-safe deque access
