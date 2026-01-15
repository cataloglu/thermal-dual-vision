# 02 - Motion Detection

## Overview
RTSP kamera stream'inden hareket algılama modülü. OpenCV kullanarak video akışını yakalayacak ve background subtraction algoritması ile hareket tespiti yapacak.

## Workflow Type
**feature** - Yeni modül geliştirme

## Task Scope
Kamera bağlantısı ve hareket algılama mantığını içeren core modül.

### Teknik Detaylar
```python
class MotionDetector:
    def __init__(self, config: MotionConfig)
    def start(self) -> None
    def stop(self) -> None
    def on_motion(self, callback: Callable[[np.ndarray, List[Contour]], None]) -> None
    def get_frame(self) -> Optional[np.ndarray]
    def is_running(self) -> bool
```

### Konfigürasyon
```yaml
camera:
  url: "rtsp://192.168.1.100:554/stream"
  fps: 5
  resolution: [1280, 720]

motion:
  sensitivity: 7        # 1-10
  min_area: 500         # piksel
  cooldown_seconds: 5
```

## Requirements
1. OpenCV VideoCapture ile RTSP bağlantısı
2. cv2.createBackgroundSubtractorMOG2 kullanımı
3. Contour detection ile hareket alanı hesaplama
4. Thread-safe callback mekanizması
5. Reconnection logic

## Files to Modify
- Yok

## Files to Reference
- `src/config.py` - MotionConfig dataclass
- `src/logger.py` - Loglama
- `src/utils.py` - Yardımcı fonksiyonlar

## Success Criteria
- [ ] RTSP stream bağlantısı çalışıyor
- [ ] Hareket algılandığında callback tetikleniyor
- [ ] Sensitivity ayarı hareket eşiğini değiştiriyor
- [ ] Cooldown süresi içinde tekrar tetiklenmiyor
- [ ] Frame capture >= 5 FPS
- [ ] Graceful shutdown çalışıyor

## QA Acceptance Criteria
- Unit test: Mock camera ile hareket simülasyonu
- Integration test: Gerçek RTSP stream ile test
- Memory leak kontrolü (1 saat çalışma)

## Dependencies
- 01-project-structure

## Notes
- Threading kullanılacak (asyncio değil, OpenCV uyumu için)
- Connection timeout ve retry mekanizması
- Frame buffer için deque kullanılabilir
