# 03 - YOLO Integration

## Overview
YOLOv8 Nano model kullanarak nesne tespiti modülü. Hareket algılanan frame'lerde insan, araba, hayvan gibi nesneleri tespit edecek. Ultralytics kütüphanesi kullanılacak.

## Workflow Type
**feature** - Yeni modül geliştirme

## Task Scope
YOLO model yükleme, inference ve sonuç filtreleme işlemlerini yapan modül.

### Teknik Detaylar
```python
@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    class_id: int

class YoloDetector:
    def __init__(self, config: YoloConfig)
    def detect(self, frame: np.ndarray) -> List[Detection]
    def detect_async(self, frame: np.ndarray) -> Future[List[Detection]]
    def set_classes(self, classes: List[str]) -> None
    def draw_detections(self, frame: np.ndarray, detections: List[Detection]) -> np.ndarray
```

### Konfigürasyon
```yaml
yolo:
  model: "yolov8n"
  confidence: 0.5
  classes:
    - person
    - car
    - dog
    - cat
```

## Requirements
1. ultralytics kütüphanesi ile YOLOv8 entegrasyonu
2. Model lazy loading (ilk kullanımda yükle)
3. Confidence threshold filtreleme
4. Sınıf bazlı filtreleme
5. Detection sonuçlarını dataclass olarak döndür

## Files to Modify
- Yok

## Files to Reference
- `src/config.py` - YoloConfig dataclass
- `src/logger.py` - Loglama

## Success Criteria
- [ ] Model başarıyla yükleniyor
- [ ] Frame'de nesne tespiti çalışıyor
- [ ] Confidence filtreleme doğru çalışıyor
- [ ] Sınıf filtreleme çalışıyor
- [ ] Detection sonuçları doğru formatta
- [ ] Inference süresi < 500ms (CPU)

## QA Acceptance Criteria
- Unit test: Test görüntüsü ile detection
- Benchmark: 100 frame inference süresi ortalaması
- Memory test: Ardışık 1000 inference sonrası memory

## Dependencies
- 01-project-structure
- 02-motion-detection

## Notes
- yolov8n.pt otomatik indirilecek (ilk çalışmada)
- GPU varsa otomatik kullanılacak (CUDA)
- Batch inference opsiyonel
