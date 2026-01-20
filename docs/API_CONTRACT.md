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

---

## 5) Live View

### GET /api/live
UI: **Live**

Response:
```json
{
  "streams": [
    { "camera_id": "cam-1", "name": "Gate", "stream_url": "/api/live/cam-1" }
  ]
}
```

### WebSocket / Stream Notu
- Live görüntü için **WS veya MJPEG** stream kullanılabilir.
- API bu dokümanda sadece **stream_url** döndürür; transport detayı backend implementasyonuna bağlıdır.

---

## 6) Settings

### GET /api/settings
UI: **Settings**

Response:
```json
{
  "motion": {
    "sensitivity": 7,
    "min_area": 500,
    "cooldown_seconds": 5
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

### PUT /api/settings
UI: **Settings**

Request body (partial update):
```json
{
  "motion": { "sensitivity": 6 },
  "ai": { "enabled": true, "api_key": "sk-***" },
  "telegram": { "enabled": true, "chat_ids": ["123456789"] }
}
```

Response:
```json
{
  "motion": { "sensitivity": 6, "min_area": 500, "cooldown_seconds": 5 },
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

## 7) Error format (GLOBAL)
```json
{
  "error": true,
  "code": "VALIDATION_ERROR",
  "message": "camera_id is required"
}
```

---

## 8) UI Mapping

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