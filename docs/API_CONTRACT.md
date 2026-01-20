# API CONTRACT — Smart Motion Detector (v2)

Base URL:
- Standalone: `http://localhost:8000`
- Home Assistant ingress: relative paths kullanılacak (`/api/...`)

---

## 1) Genel Prensipler
- **JSON only**: Tüm request/response body JSON.
- **Auth yok** (v2 için).
- **RTSP / token alanları** her zaman maskeli döner: `***REDACTED***`.
- **Zaman formatı**: ISO-8601 UTC (`2026-01-01T00:00:00Z`).
- **Error formatı** her endpoint için aynı (aşağıdaki bölüm).
- **İnsan algılama modeli** seçilebilir (iki seçenek): `yolov8n-person` | `yolov8s-person`.
- **Algılama kaynağı** kamera bazında seçilebilir: `color` | `thermal` | `auto`.
- **Live stream modu**: `mjpeg` (default) veya `webrtc` (opsiyonel, go2rtc gerekir).
- **Ayarlar kalıcıdır** ve restart sonrası korunur.
- **Stream roles**: `detect` / `live` / `record` (kamera bazında).
- **Zones**: kamera bazında polygon alanlar; `motion` ve/veya `person` için filtre.
- **Zone polygon kuralları**:
  - Min 3 nokta, max 20 nokta
  - Koordinatlar normalize: `0.0 - 1.0`
  - Self-intersection kabul edilmez
- **Record** yalnızca event bazlıdır (sürekli kayıt yok).
- **Disk temizleme**: retention + disk limitleriyle en eski medya silinir (kullanıcı ayarlayabilir).

---

## 2) Health & System

### GET /api/health
UI: **Dashboard**, **Diagnostics**

Response:
```json
{
  "status": "ok",
  "version": "2.0.0",
  "uptime_s": 12345,
  "ai": { "enabled": false, "reason": "no_api_key" },
  "cameras": { "online": 1, "retrying": 0, "down": 0 },
  "components": { "pipeline": "ok", "telegram": "disabled", "mqtt": "disabled" }
}
```

### GET /ready
UI: **Diagnostics**

Response:
```json
{ "ready": true, "status": "ok" }
```

---

## 3) Cameras

### GET /api/cameras
UI: **Settings**

Response:
```json
{
  "cameras": [
    {
      "id": "cam-1",
      "name": "Gate",
      "type": "thermal",
      "enabled": true,
      "rtsp_url": "***REDACTED***",
      "rtsp_url_color": "***REDACTED***",
      "rtsp_url_thermal": "***REDACTED***",
      "channel_color": 102,
      "channel_thermal": 202,
      "detection_source": "thermal",
      "stream_roles": ["detect", "live"],
      "status": "connected",
      "zones": [
        {
          "id": "zone-1",
          "name": "Entry",
          "enabled": true,
          "mode": "person",
          "polygon": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
        }
      ],
      "last_frame_ts": "2026-01-01T00:00:00Z",
      "motion_config": {
        "enabled": true,
        "sensitivity": 7,
        "threshold": 500,
        "cooldown": 5,
        "roi": ""
      }
    }
  ]
}
```

### POST /api/cameras
UI: **Settings** (Add Camera)

Request body:
```json
{
  "name": "Gate",
  "type": "thermal",
  "enabled": true,
  "rtsp_url_thermal": "rtsp://user:pass@host/stream",
  "rtsp_url_color": "",
  "channel_color": 102,
  "channel_thermal": 202,
  "detection_source": "thermal",
  "stream_roles": ["detect", "live"],
  "zones": [
    { "id": "zone-1", "name": "Entry", "enabled": true, "mode": "person", "polygon": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]] }
  ],
  "motion_config": {
    "enabled": true,
    "sensitivity": 7,
    "threshold": 500,
    "cooldown": 5,
    "roi": ""
  }
}
```

Response body:
```json
{
  "id": "cam-1",
  "name": "Gate",
  "type": "thermal",
  "enabled": true,
  "rtsp_url": "***REDACTED***",
  "rtsp_url_color": "***REDACTED***",
  "rtsp_url_thermal": "***REDACTED***",
  "channel_color": 102,
  "channel_thermal": 202,
  "detection_source": "thermal",
  "stream_roles": ["detect", "live"],
  "zones": [
    { "id": "zone-1", "name": "Entry", "enabled": true, "mode": "person", "polygon": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]] }
  ],
  "status": "connected",
  "last_frame_ts": "2026-01-01T00:00:00Z",
  "motion_config": {
    "enabled": true,
    "sensitivity": 7,
    "threshold": 500,
    "cooldown": 5,
    "roi": ""
  }
}
```

### PUT /api/cameras/{id}
UI: **Settings** (Edit Camera)

Request body (partial update):
```json
{
  "name": "Gate West",
  "enabled": true,
  "detection_source": "color",
  "stream_roles": ["detect", "live", "record"],
  "zones": [
    { "id": "zone-1", "name": "Entry", "enabled": true, "mode": "motion", "polygon": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]] }
  ],
  "motion_config": { "enabled": true, "sensitivity": 6, "threshold": 450, "cooldown": 5 }
}
```

Response body:
```json
{
  "id": "cam-1",
  "name": "Gate West",
  "type": "thermal",
  "enabled": true,
  "rtsp_url": "***REDACTED***",
  "rtsp_url_color": "***REDACTED***",
  "rtsp_url_thermal": "***REDACTED***",
  "channel_color": 102,
  "channel_thermal": 202,
  "detection_source": "color",
  "stream_roles": ["detect", "live", "record"],
  "zones": [
    { "id": "zone-1", "name": "Entry", "enabled": true, "mode": "motion", "polygon": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]] }
  ],
  "status": "connected",
  "last_frame_ts": "2026-01-01T00:00:00Z",
  "motion_config": { "enabled": true, "sensitivity": 6, "threshold": 450, "cooldown": 5, "roi": "" }
}
```

### DELETE /api/cameras/{id}
UI: **Settings** (Delete Camera)

Response body:
```json
{ "deleted": true, "id": "cam-1" }
```

### Camera status enum
- `connected`
- `retrying`
- `down`
- `initializing`

### POST /api/cameras/test
UI: **Settings** (Camera Test)

Request body:
```json
{
  "type": "thermal",
  "rtsp_url_thermal": "rtsp://user:pass@host/stream",
  "rtsp_url_color": "",
  "channel_color": 102,
  "channel_thermal": 202
}
```

Response body:
```json
{
  "success": true,
  "snapshot_base64": "data:image/jpeg;base64,...",
  "latency_ms": 320,
  "error_reason": null
}
```

---

## 4) Events

### GET /api/events
UI: **Events**, **Dashboard**

Query params:
- `page` (int, default 1)
- `page_size` (int, default 20)
- `camera_id` (string, optional)
- `date` (YYYY-MM-DD, optional)
- `confidence` (float min, optional)

Response:
```json
{
  "page": 1,
  "page_size": 20,
  "total": 1,
  "events": [
    {
      "id": "evt-1",
      "camera_id": "cam-1",
      "timestamp": "2026-01-01T00:00:00Z",
      "confidence": 0.64,
      "event_type": "person",
      "summary": "Person near gate",
      "collage_url": "/api/events/evt-1/collage",
      "gif_url": "/api/events/evt-1/preview.gif",
      "mp4_url": "/api/events/evt-1/timelapse.mp4"
    }
  ]
}
```

### GET /api/events/{id}
UI: **Events** (Detail)

Response:
```json
{
  "id": "evt-1",
  "camera_id": "cam-1",
  "timestamp": "2026-01-01T00:00:00Z",
  "confidence": 0.64,
  "event_type": "person",
  "summary": "Person near gate",
  "ai": {
    "enabled": false,
    "reason": "no_api_key",
    "text": null
  },
  "media": {
    "collage_url": "/api/events/evt-1/collage",
    "gif_url": "/api/events/evt-1/preview.gif",
    "mp4_url": "/api/events/evt-1/timelapse.mp4"
  }
}
```

### Event media endpoints
- `GET /api/events/{id}/collage` → `image/jpeg`
- `GET /api/events/{id}/preview.gif` → `image/gif`
- `GET /api/events/{id}/timelapse.mp4` → `video/mp4`

### DELETE /api/events/{id}
UI: **Events** (Manual delete)

Response:
```json
{ "deleted": true, "id": "evt-1" }
```

---

## 5) Live View

### GET /api/live
UI: **Live**

Response:
```json
{
  "streams": [
    { "camera_id": "cam-1", "name": "Gate", "stream_url": "/api/live/cam-1", "output_mode": "mjpeg" }
  ]
}
```

### WebSocket / Stream Notu
- Live görüntü için **WS veya MJPEG** stream kullanılabilir.
- API bu dokümanda **stream_url** ve **output_mode** döndürür; `webrtc` için go2rtc gereklidir.

### Stream endpoint detayları
- `mjpeg`: `GET /api/live/{camera_id}.mjpeg`
- `webrtc`: `GET /api/live/{camera_id}` (webrtc handshake + go2rtc)

---

## 6) WebSocket

### WS /api/ws/events
- Push event format:
```json
{ "type": "event", "data": { "id": "evt-1", "camera_id": "cam-1", "event_type": "person", "timestamp": "2026-01-01T00:00:00Z" } }
```
- Sistem durumu:
```json
{ "type": "status", "data": { "cameras": { "online": 1, "retrying": 0, "down": 0 }, "ai": { "enabled": false } } }
```

---

## 7) Settings

### GET /api/settings
UI: **Settings**

Response:
```json
{
  "detection": {
    "model": "yolov8n-person",
    "confidence_threshold": 0.25,
    "nms_iou_threshold": 0.45,
    "inference_resolution": [640, 640],
    "inference_fps": 5,
    "enable_tracking": false
  },
  "motion": {
    "sensitivity": 7,
    "min_area": 500,
    "cooldown_seconds": 5,
    "presets": {
      "thermal_recommended": { "sensitivity": 8, "min_area": 450, "cooldown_seconds": 4 }
    }
  },
  "thermal": {
    "enable_enhancement": true,
    "enhancement_method": "clahe",
    "clahe_clip_limit": 2.0,
    "clahe_tile_size": [8, 8],
    "gaussian_blur_kernel": [3, 3]
  },
  "stream": {
    "protocol": "tcp",
    "buffer_size": 1,
    "reconnect_delay_seconds": 5,
    "max_reconnect_attempts": 10
  },
  "live": {
    "output_mode": "mjpeg",
    "webrtc": { "enabled": false, "go2rtc_url": "" }
  },
  "record": {
    "enabled": false,
    "retention_days": 7,
    "record_segments_seconds": 10,
    "disk_limit_percent": 80,
    "cleanup_policy": "oldest_first",
    "delete_order": ["mp4", "gif", "collage"]
  },
  "event": {
    "cooldown_seconds": 5,
    "frame_buffer_size": 10,
    "frame_interval": 2,
    "min_event_duration": 1.0
  },
  "media": {
    "retention_days": 7,
    "cleanup_interval_hours": 24,
    "disk_limit_percent": 80
  },
  "ai": {
    "enabled": false,
    "api_key": "***REDACTED***",
    "model": "gpt-4",
    "max_tokens": 1000,
    "timeout": 30
  },
  "telegram": {
    "enabled": false,
    "bot_token": "***REDACTED***",
    "chat_ids": ["123456789"],
    "rate_limit_seconds": 5,
    "send_images": true,
    "video_speed": 4,
    "event_types": ["person"],
    "cooldown_seconds": 5,
    "max_messages_per_min": 20,
    "snapshot_quality": 85
  }
}
```

### POST /api/telegram/test
UI: **Settings** (Telegram Test)

Request body:
```json
{
  "bot_token": "123:abc",
  "chat_ids": ["123456789"]
}
```

Response:
```json
{ "success": true, "latency_ms": 420, "error_reason": null }
```

### PUT /api/settings
UI: **Settings**

Request body (partial update):
```json
{
  "detection": { "model": "yolov8s-person", "confidence_threshold": 0.3, "inference_fps": 10 },
  "thermal": { "enable_enhancement": true, "enhancement_method": "clahe" },
  "stream": { "protocol": "tcp", "buffer_size": 2 },
  "motion": { "sensitivity": 6, "cooldown_seconds": 4 },
  "live": { "output_mode": "webrtc", "webrtc": { "enabled": true, "go2rtc_url": "http://localhost:1984" } },
  "record": { "enabled": true, "retention_days": 14, "record_segments_seconds": 10, "disk_limit_percent": 85 },
  "event": { "cooldown_seconds": 3, "frame_buffer_size": 15 },
  "media": { "retention_days": 14, "disk_limit_percent": 85 },
  "ai": { "enabled": true, "api_key": "sk-***" },
  "telegram": { "enabled": true, "chat_ids": ["123456789"] }
}
```

Response:
```json
{
  "detection": {
    "model": "yolov8s-person",
    "confidence_threshold": 0.3,
    "nms_iou_threshold": 0.45,
    "inference_resolution": [640, 640],
    "inference_fps": 10,
    "enable_tracking": false
  },
  "motion": {
    "sensitivity": 6,
    "min_area": 500,
    "cooldown_seconds": 4,
    "presets": {
      "thermal_recommended": { "sensitivity": 8, "min_area": 450, "cooldown_seconds": 4 }
    }
  },
  "thermal": {
    "enable_enhancement": true,
    "enhancement_method": "clahe",
    "clahe_clip_limit": 2.0,
    "clahe_tile_size": [8, 8],
    "gaussian_blur_kernel": [3, 3]
  },
  "stream": {
    "protocol": "tcp",
    "buffer_size": 2,
    "reconnect_delay_seconds": 5,
    "max_reconnect_attempts": 10
  },
  "live": {
    "output_mode": "webrtc",
    "webrtc": { "enabled": true, "go2rtc_url": "http://localhost:1984" }
  },
  "record": {
    "enabled": true,
    "retention_days": 14,
    "record_segments_seconds": 10,
    "disk_limit_percent": 85,
    "cleanup_policy": "oldest_first",
    "delete_order": ["mp4", "gif", "collage"]
  },
  "event": {
    "cooldown_seconds": 3,
    "frame_buffer_size": 15,
    "frame_interval": 2,
    "min_event_duration": 1.0
  },
  "media": {
    "retention_days": 14,
    "cleanup_interval_hours": 24,
    "disk_limit_percent": 85
  },
  "ai": { "enabled": true, "api_key": "***REDACTED***", "model": "gpt-4", "max_tokens": 1000, "timeout": 30 },
  "telegram": {
    "enabled": true,
    "bot_token": "***REDACTED***",
    "chat_ids": ["123456789"],
    "rate_limit_seconds": 5,
    "send_images": true,
    "video_speed": 4,
    "event_types": ["person"],
    "cooldown_seconds": 5,
    "max_messages_per_min": 20,
    "snapshot_quality": 85
  }
}
```

---

## 8) Diagnostics

### GET /api/logs
UI: **Diagnostics**

Query params:
- `lines` (int, default 200)

Response:
```json
{ "lines": ["2026-01-01 00:00:00 INFO ..."] }
```

---

## 9) Error format (GLOBAL)
```json
{
  "error": true,
  "code": "VALIDATION_ERROR",
  "message": "camera_id is required"
}
```

### Error code list
- `VALIDATION_ERROR`
- `CAMERA_NOT_FOUND`
- `EVENT_NOT_FOUND`
- `RTSP_CONNECTION_FAILED`
- `SNAPSHOT_FAILED`
- `DISK_FULL`
- `AI_DISABLED`
- `INTERNAL_ERROR`

---

## 10) UI Mapping

| Endpoint | Page |
| --- | --- |
| GET /api/health | Dashboard, Diagnostics |
| GET /ready | Diagnostics |
| GET /api/cameras | Settings |
| POST /api/cameras | Settings |
| PUT /api/cameras/{id} | Settings |
| DELETE /api/cameras/{id} | Settings |
| GET /api/events | Dashboard (summary), Events |
| GET /api/events/{id} | Events |
| GET /api/live | Live |
| GET /api/settings | Settings |
| PUT /api/settings | Settings |