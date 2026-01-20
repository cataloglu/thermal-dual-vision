# Configuration Reference - Smart Motion Detector v2

Bu doküman `/api/settings` endpoint'indeki tüm config alanlarını açıklar.

---

## 📋 Config Sections

### 1. `detection` (YOLOv8 Person Detection)

**Amaç**: YOLOv8 model ve inference ayarları

| Alan | Tip | Default | Açıklama |
|------|-----|---------|----------|
| `model` | string | `"yolov8n-person"` | Model seçimi: `yolov8n-person` veya `yolov8s-person` |
| `confidence_threshold` | float | `0.25` | Minimum confidence (0.0-1.0) |
| `nms_iou_threshold` | float | `0.45` | Non-Maximum Suppression IoU threshold |
| `inference_resolution` | [int, int] | `[640, 640]` | Inference için frame resolution |
| `inference_fps` | int | `5` | Saniyede kaç frame işlenecek |
| `enable_tracking` | bool | `false` | Object tracking (gelecek özellik) |

**Not**: Bu **primary model seçimi**dir. Tüm kameralar için geçerlidir.

---

### 2. `motion` (Motion Detection)

**Amaç**: Frame-diff based motion detection (person detection öncesi pre-filter)

| Alan | Tip | Default | Açıklama |
|------|-----|---------|----------|
| `sensitivity` | int | `7` | Motion sensitivity (1-10 scale) |
| `min_area` | int | `500` | Minimum pixel area for motion |
| `cooldown_seconds` | int | `5` | Minimum süre iki motion arasında |
| `presets` | object | - | Hazır preset'ler (thermal_recommended) |

**Not**: `motion.detector_model` kaldırıldı. Model seçimi `detection.model` ile yapılır.

---

### 3. `thermal` (Thermal Image Enhancement)

**Amaç**: Thermal kamera görüntü iyileştirme (preprocessing)

| Alan | Tip | Default | Açıklama |
|------|-----|---------|----------|
| `enable_enhancement` | bool | `true` | Enhancement aktif/pasif |
| `enhancement_method` | string | `"clahe"` | Method: `clahe`, `histogram`, `none` |
| `clahe_clip_limit` | float | `2.0` | CLAHE clip limit |
| `clahe_tile_size` | [int, int] | `[8, 8]` | CLAHE tile grid size |
| `gaussian_blur_kernel` | [int, int] | `[3, 3]` | Gaussian blur kernel (noise reduction) |

**Kaynak**: `docs/PERFORMANCE_TUNING.md` (mAP %6-10 artış)

---

### 4. `stream` (RTSP Stream Ingestion)

**Amaç**: Kameradan gelen RTSP stream ayarları (input)

| Alan | Tip | Default | Açıklama |
|------|-----|---------|----------|
| `protocol` | string | `"tcp"` | RTSP protocol: `tcp` (önerilen) veya `udp` |
| `buffer_size` | int | `1` | OpenCV VideoCapture buffer size |
| `reconnect_delay_seconds` | int | `5` | Reconnect denemesi arasındaki süre |
| `max_reconnect_attempts` | int | `10` | Maksimum reconnect deneme sayısı |

**Not**: Bu **kameradan backend'e** gelen stream için. Browser'a giden stream `live` section'da.

---

### 5. `live` (Live View Output)

**Amaç**: Browser'a giden live stream ayarları (output)

| Alan | Tip | Default | Açıklama |
|------|-----|---------|----------|
| `output_mode` | string | `"mjpeg"` | Output mode: `mjpeg` veya `webrtc` |
| `webrtc.enabled` | bool | `false` | WebRTC aktif/pasif |
| `webrtc.go2rtc_url` | string | `""` | go2rtc server URL (WebRTC için gerekli) |

**Not**: 
- `stream` = **kameradan backend'e** (input)
- `live` = **backend'den browser'a** (output)

---

### 6. `record` (Recording & Retention)

**Amaç**: Event-based recording ve disk yönetimi

| Alan | Tip | Default | Açıklama |
|------|-----|---------|----------|
| `enabled` | bool | `false` | Recording aktif/pasif |
| `retention_days` | int | `7` | Kayıtları kaç gün sakla |
| `record_segments_seconds` | int | `10` | Segment uzunluğu (saniye) |
| `disk_limit_percent` | int | `80` | Maksimum disk kullanımı (%) |
| `cleanup_policy` | string | `"oldest_first"` | Temizleme stratejisi |
| `delete_order` | array | `["mp4", "gif", "collage"]` | Silme sırası |

---

### 7. `event` (Event Generation)

**Amaç**: Person detection event oluşturma ayarları

| Alan | Tip | Default | Açıklama |
|------|-----|---------|----------|
| `cooldown_seconds` | int | `5` | Minimum süre iki event arasında |
| `frame_buffer_size` | int | `10` | Collage için frame buffer |
| `frame_interval` | int | `2` | Her kaç frame'de bir kaydet |
| `min_event_duration` | float | `1.0` | Minimum event süresi (saniye) |

---

### 8. `media` (Media Cleanup)

**Amaç**: Event medya dosyaları temizleme

| Alan | Tip | Default | Açıklama |
|------|-----|---------|----------|
| `retention_days` | int | `7` | Medya dosyalarını kaç gün sakla |
| `cleanup_interval_hours` | int | `24` | Cleanup job çalışma sıklığı |
| `disk_limit_percent` | int | `80` | Maksimum disk kullanımı (%) |

---

### 9. `ai` (OpenAI Integration)

**Amaç**: Event summary için AI entegrasyonu (opsiyonel)

| Alan | Tip | Default | Açıklama |
|------|-----|---------|----------|
| `enabled` | bool | `false` | AI aktif/pasif |
| `api_key` | string | `""` | OpenAI API key (masked) |
| `model` | string | `"gpt-4"` | OpenAI model |
| `max_tokens` | int | `1000` | Maksimum token sayısı |
| `timeout` | int | `30` | API timeout (saniye) |

---

### 10. `telegram` (Telegram Notifications)

**Amaç**: Event bildirimleri (opsiyonel)

| Alan | Tip | Default | Açıklama |
|------|-----|---------|----------|
| `enabled` | bool | `false` | Telegram aktif/pasif |
| `bot_token` | string | `""` | Telegram bot token (masked) |
| `chat_ids` | array | `[]` | Chat ID'ler |
| `rate_limit_seconds` | int | `5` | Minimum süre iki mesaj arasında |
| `send_images` | bool | `true` | Collage gönder |
| `video_speed` | int | `4` | Video hızlandırma faktörü |
| `event_types` | array | `["person"]` | Hangi event tipleri gönderilecek |
| `cooldown_seconds` | int | `5` | Cooldown süresi |
| `max_messages_per_min` | int | `20` | Rate limit |
| `snapshot_quality` | int | `85` | JPEG kalitesi (0-100) |

---

## 🔄 Config Hierarchy

```
detection.model          → PRIMARY model seçimi (global)
  ↓
motion.*                 → Pre-filter (frame-diff)
  ↓
thermal.*                → Preprocessing (thermal kameralar için)
  ↓
stream.*                 → RTSP input (kameradan backend)
  ↓
live.*                   → Stream output (backend'den browser)
  ↓
event.*                  → Event generation
  ↓
record.* / media.*       → Storage & cleanup
  ↓
ai.* / telegram.*        → Notifications (opsiyonel)
```

---

## 🎯 Common Patterns

### Thermal Kamera için Optimal Ayarlar
```json
{
  "detection": {
    "model": "yolov8n-person",
    "confidence_threshold": 0.25,
    "inference_fps": 5
  },
  "thermal": {
    "enable_enhancement": true,
    "enhancement_method": "clahe"
  },
  "stream": {
    "protocol": "tcp"
  },
  "motion": {
    "sensitivity": 8,
    "min_area": 450,
    "cooldown_seconds": 4
  }
}
```

### Color Kamera için Optimal Ayarlar
```json
{
  "detection": {
    "model": "yolov8s-person",
    "confidence_threshold": 0.5,
    "inference_fps": 10
  },
  "thermal": {
    "enable_enhancement": false
  },
  "stream": {
    "protocol": "tcp"
  },
  "motion": {
    "sensitivity": 7,
    "min_area": 500,
    "cooldown_seconds": 5
  }
}
```

---

## ⚠️ Deprecated Fields

| Alan | Durum | Yeni Alan |
|------|-------|-----------|
| `motion.detector_model` | ❌ Kaldırıldı | `detection.model` kullan |
| `stream.mode` | ❌ Kaldırıldı | `live.output_mode` kullan |
| `live.stream_mode` | ❌ Renamed | `live.output_mode` kullan |

---

## 📝 Validation Rules

- `confidence_threshold`: 0.0 - 1.0
- `inference_fps`: 1 - 30
- `motion.sensitivity`: 1 - 10
- `disk_limit_percent`: 50 - 95
- `telegram.snapshot_quality`: 0 - 100

---

**Referanslar**:
- API detayları: `docs/API_CONTRACT.md`
- Performance tuning: `docs/PERFORMANCE_TUNING.md`
- UI mapping: `docs/DESIGN_SYSTEM.md`
