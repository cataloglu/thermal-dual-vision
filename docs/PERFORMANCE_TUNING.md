# Performance Tuning Guide - Smart Motion Detector v2

Bu doküman, test sürecini hızlandırmak için **kanıtlanmış ayarlar** ve **best practices** içerir.

**Kaynak**: 2024-2025 araştırma makaleleri ve production deployments

---

## 🎯 Hızlı Başlangıç (Önerilen Ayarlar)

### YOLOv8 Model Seçimi

| Model | Kullanım Senaryosu | FPS (T4 GPU) | mAP | Parametre |
|-------|-------------------|--------------|-----|-----------|
| **yolov8n-person** | Edge devices, Raspberry Pi, çok kamera | ~680 FPS | 37.3 | 3.2M |
| **yolov8s-person** | Server, yüksek doğruluk gerekli | ~375 FPS | 44.9 | 11.2M |

**Öneri**: 
- **1-4 kamera**: `yolov8s-person` (daha yüksek doğruluk)
- **5+ kamera veya edge device**: `yolov8n-person` (daha hızlı)

---

## 🌡️ Thermal Camera Ayarları

### 1. Thermal Sensitivity (NETD)

**Kritik Metrik**: Kameranın algılayabileceği en küçük sıcaklık farkı

| NETD Değeri | Kalite | Önerilen Kullanım |
|-------------|--------|-------------------|
| <25mK | Mükemmel | Professional surveillance |
| <50mK | İyi | Genel güvenlik |
| <60mK | Kabul Edilebilir | Budget projeler |

**Öneri**: Minimum **<50mK** NETD değerine sahip kamera kullanın.

---

### 2. Resolution ve Frame Rate

**Önerilen Ayarlar**:
```python
# Thermal Camera
THERMAL_RESOLUTION = (320, 240)  # Minimum
THERMAL_RESOLUTION_OPTIMAL = (640, 480)  # Önerilen
THERMAL_FPS = 25  # Hz (minimum)
```

**Neden?**
- 320x240: Temel detection için yeterli
- 640x480: Person identification için ideal
- 25 Hz: Hareket eden kişileri yakalamak için minimum

---

### 3. Temperature Range

```python
# Person Detection
TEMP_RANGE_MIN = 30  # °C
TEMP_RANGE_MAX = 40  # °C

# Geniş Çevre (opsiyonel)
TEMP_RANGE_WIDE_MIN = -20  # °C
TEMP_RANGE_WIDE_MAX = 120  # °C
```

**Not**: İnsan vücut sıcaklığı 30-40°C arası, ama çevre faktörleri için geniş range kullanılabilir.

---

### 4. Image Pre-processing (Thermal için Kritik!)

**Problem**: Thermal görüntüler düşük kontrast ve gürültülü olabilir.

**Çözüm**: Histogram enhancement

```python
import cv2
import numpy as np

def enhance_thermal_image(thermal_frame):
    """
    Kurtosis-based histogram enhancement
    Kaynak: Springer 2025 research
    """
    # CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(thermal_frame)
    
    # Gaussian blur (noise reduction)
    enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0)
    
    return enhanced
```

**Performans İyileştirmesi**: mAP 0.93 → 0.99 (OSU thermal dataset)

---

## 🎥 RTSP Stream Ayarları

### 1. Resolution ve FPS

**Kamera Stream**:
```python
# Kameradan gelen stream
CAMERA_STREAM_RESOLUTION = (1280, 720)  # veya (1920, 1080)
CAMERA_STREAM_FPS = 25  # veya 30
```

**Inference için Downscale**:
```python
# YOLOv8'e gönderilen frame
INFERENCE_RESOLUTION = (640, 640)  # veya (640, 480)
INFERENCE_FPS = 5  # Her frame'i işlemeye gerek yok!
```

**Neden Downscale?**
- 1080p → 640x640: ~9x daha hızlı inference
- 5 FPS inference: Person detection için yeterli (sürekli hareket değil)

---

### 2. RTSP Protocol Ayarları

**OpenCV VideoCapture Ayarları**:
```python
import cv2

# TCP kullan (UDP yerine) - frame tearing önler
rtsp_url = "rtsp://user:pass@192.168.1.100:554/stream?tcp"

cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

# Buffer size ayarla (latency azaltır)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# Codec ayarla
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))
```

**Kritik**: `?tcp` parametresi ekleyin! UDP packet loss'tan kaynaklanan artifact'ları önler.

---

### 3. MJPEG vs WebRTC

| Özellik | MJPEG | WebRTC |
|---------|-------|--------|
| **Latency** | 1-3 saniye | <500ms |
| **Browser Support** | ✅ Native | ✅ Native (modern browsers) |
| **Bandwidth** | Yüksek | Düşük (H.264/H.265) |
| **Complexity** | Basit | Orta (STUN/TURN gerekli) |
| **Encryption** | Opsiyonel | ✅ Zorunlu (SRTP/DTLS) |

**Öneri**:
- **MVP için**: MJPEG (kolay implement)
- **Production için**: WebRTC (düşük latency + güvenlik)

**Hybrid Yaklaşım** (En İyi):
```
Camera → RTSP (H.264) → Backend → WebRTC (browser)
                       → MJPEG (fallback)
```

---

## 🤖 YOLOv8 Detection Ayarları

### 1. Confidence Threshold

**Thermal Camera için Önerilen**:
```python
# Standart ayar
CONFIDENCE_THRESHOLD = 0.25  # Default

# Thermal için optimize
CONFIDENCE_THERMAL_CLEAR = 0.4  # İyi hava koşulları
CONFIDENCE_THERMAL_CHALLENGING = 0.2  # Yağmur, sis, kar

# Color camera için
CONFIDENCE_COLOR = 0.5  # Daha yüksek threshold
```

**Neden Farklı?**
- Thermal: Düşük kontrast → daha düşük threshold
- Color: Yüksek detay → daha yüksek threshold (false positive azaltır)

---

### 2. NMS (Non-Maximum Suppression)

```python
NMS_IOU_THRESHOLD = 0.45  # Default (genelde değiştirmeye gerek yok)
```

---

### 3. Inference Optimization

**TensorRT (NVIDIA GPU)**:
```python
from ultralytics import YOLO

# Model export
model = YOLO('yolov8n-person.pt')
model.export(format='engine')  # TensorRT

# Inference
model = YOLO('yolov8n-person.engine')
results = model(frame)
```

**Performans**: 2-3x daha hızlı!

**ONNX (CPU/Cross-platform)**:
```python
model.export(format='onnx')
model = YOLO('yolov8n-person.onnx')
```

---

## 🎭 Zone/ROI Ayarları

### 1. Polygon Validation

```python
MIN_POLYGON_POINTS = 3
MAX_POLYGON_POINTS = 20
```

### 2. Motion Sensitivity

**Thermal Camera için**:
```python
MOTION_SENSITIVITY_THERMAL = 8  # (1-10 scale)
MOTION_MIN_AREA_THERMAL = 450  # pixels
MOTION_COOLDOWN_THERMAL = 4  # seconds
```

**Color Camera için**:
```python
MOTION_SENSITIVITY_COLOR = 7
MOTION_MIN_AREA_COLOR = 500  # pixels
MOTION_COOLDOWN_COLOR = 5  # seconds
```

**Kaynak**: API_CONTRACT.md presets

---

## 🔄 Event Generation Ayarları

### 1. Cooldown Period

```python
EVENT_COOLDOWN_SECONDS = 5  # Minimum süre iki event arasında
```

**Neden?**
- Aynı kişi için duplicate event'leri önler
- False positive'leri azaltır

### 2. Frame Buffer

```python
EVENT_FRAME_BUFFER_SIZE = 10  # Collage için frame sayısı
EVENT_FRAME_INTERVAL = 2  # Her 2 frame'de bir kaydet
```

**Sonuç**: 10 frame buffer, 5 FPS → 2 saniyelik event

---

## 📊 Performance Benchmarks (Referans)

### Hardware: NVIDIA T4 GPU

| Model | Resolution | FPS | Latency |
|-------|-----------|-----|---------|
| YOLOv8n | 640x640 | ~680 | 1.47ms |
| YOLOv8s | 640x640 | ~375 | 2.66ms |

### Hardware: Raspberry Pi 4 (CPU)

| Model | Resolution | FPS | Latency |
|-------|-----------|-----|---------|
| YOLOv8n | 640x640 | ~12 | 80ms |
| YOLOv8s | 640x640 | ~8 | 128ms |

**Öneri**: Raspberry Pi için sadece YOLOv8n kullanın!

---

## 🧪 Test Stratejisi

### Phase 1: Baseline Test (1 gün)

1. **YOLOv8n ile başla**
   - Confidence: 0.25
   - Resolution: 640x640
   - FPS: 5

2. **Thermal enhancement test et**
   - CLAHE ile/without karşılaştır
   - mAP ölç

3. **Latency ölç**
   - RTSP → Detection → Event generation

### Phase 2: Optimization (2-3 gün)

1. **Confidence threshold sweep**
   - 0.2, 0.25, 0.3, 0.4, 0.5
   - False positive/negative oranı

2. **Model comparison**
   - YOLOv8n vs YOLOv8s
   - FPS vs Accuracy trade-off

3. **Stream optimization**
   - MJPEG vs WebRTC latency
   - Bandwidth kullanımı

### Phase 3: Fine-tuning (1-2 gün)

1. **Zone/ROI testing**
   - Polygon accuracy
   - Motion sensitivity

2. **Cooldown optimization**
   - Event frequency
   - Duplicate detection

3. **Multi-camera test**
   - Concurrent stream handling
   - Resource usage

---

## 📝 Önerilen Config Template

```json
{
  "detection": {
    "model": "yolov8n-person",
    "confidence_threshold": 0.25,
    "nms_iou_threshold": 0.45,
    "inference_resolution": [640, 640],
    "inference_fps": 5
  },
  "thermal": {
    "enable_enhancement": true,
    "enhancement_method": "clahe",
    "sensitivity": 8,
    "min_area": 450,
    "cooldown": 4
  },
  "stream": {
    "mode": "mjpeg",
    "protocol": "tcp",
    "buffer_size": 1,
    "downscale_resolution": [640, 480]
  },
  "event": {
    "cooldown_seconds": 5,
    "frame_buffer_size": 10,
    "frame_interval": 2
  }
}
```

---

## 🔗 Referanslar

1. **YOLOv8 Thermal**: Springer 2025 - "Person detection in thermal images using kurtosis based histogram enhancement and YOLOv8"
2. **YOLOv8n vs YOLOv8s**: Ultralytics Official Benchmarks 2024
3. **RTSP Optimization**: Roboflow Blog - "How to Run Computer Vision Models on RTSP Streams"
4. **Thermal Camera Best Practices**: FLIR - "The Importance of Thermal Sensitivity (NETD) for Detection Accuracy"
5. **WebRTC vs RTSP**: Wowza Media Systems 2024

---

## 🚀 Implementation Checklist

- [ ] YOLOv8n model indir ve test et
- [ ] Thermal enhancement pipeline implement et
- [ ] RTSP TCP connection test et
- [ ] Confidence threshold sweep yap
- [ ] Multi-camera concurrent test
- [ ] Event cooldown optimize et
- [ ] WebRTC integration (opsiyonel)

---

## 💡 Pro Tips

1. **Her zaman TCP kullan**: UDP packet loss → frame tearing
2. **Thermal için enhancement zorunlu**: mAP %6-10 artış
3. **Inference FPS ≠ Camera FPS**: 5 FPS inference yeterli
4. **TensorRT kullan**: NVIDIA GPU varsa 2-3x hızlanma
5. **Cooldown period kritik**: Duplicate event'leri önler
6. **Zone testing**: Gerçek senaryoda test et, simülasyonda değil

---

**Son Güncelleme**: 2026-01-20  
**Kaynak**: 2024-2025 production deployments ve research papers
