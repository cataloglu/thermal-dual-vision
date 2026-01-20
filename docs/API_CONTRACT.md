# API Contract (v2)

Base URL: `/api`

## Health
### GET `/api/health`
Response:
```json
{
  "status": "ok",
  "ai_enabled": true,
  "pipeline": { "status": "running", "updated_at": 1700000000 },
  "components": {
    "camera": { "status": "connected", "detail": "ok" },
    "telegram": { "status": "disabled" },
    "mqtt": { "status": "unknown" }
  }
}
```

### GET `/ready`
Response:
```json
{ "ready": true, "status": "ok" }
```

## Config
### GET `/api/config`
Response (redacted):
```json
{
  "general": { "bind_host": "0.0.0.0", "http_port": 8000, "timezone": "UTC" },
  "log_level": "INFO",
  "motion": {
    "sensitivity": 7,
    "min_area": 500,
    "cooldown_seconds": 5,
    "default_sensitivity": 7,
    "default_threshold": 500,
    "default_cooldown": 5,
    "default_roi": null
  },
  "llm": { "enabled": true, "api_key": "***REDACTED***", "model": "gpt-4", "max_tokens": 1000, "timeout": 30 },
  "screenshots": { "window_seconds": 9, "quality": 85, "max_stored": 100, "buffer_seconds": 10 },
  "mqtt": {
    "host": "broker",
    "port": 1883,
    "username": "***REDACTED***",
    "password": "***REDACTED***",
    "topic_prefix": "smart_motion",
    "discovery": true,
    "discovery_prefix": "homeassistant",
    "qos": 1
  },
  "telegram": {
    "enabled": false,
    "bot_token": "***REDACTED***",
    "chat_ids": [],
    "rate_limit_seconds": 5,
    "send_images": true,
    "video_speed": 4,
    "event_types": ["motion", "analysis", "alert"],
    "cooldown_seconds": 5,
    "max_messages_per_min": 20,
    "snapshot_quality": 85
  },
  "retry_policy": {
    "initial_delay": 1.0,
    "max_delay": 10.0,
    "multiplier": 2.0,
    "jitter": 0.2,
    "max_retries": null
  }
}
```

### POST `/api/config`
Request (partial updates allowed):
```json
{
  "motion": { "sensitivity": 6, "default_roi": null },
  "telegram": { "enabled": true }
}
```
Response: full config (redacted), same shape as GET.

## Cameras
### GET `/api/cameras`
Response:
```json
{
  "cameras": [
    {
      "id": "cam-1",
      "name": "Gate",
      "type": "thermal",
      "status": "connected",
      "last_frame_ts": 1700000000,
      "rtsp_url_color": "",
      "rtsp_url_thermal": "***REDACTED***",
      "channel_color": 102,
      "channel_thermal": 202,
      "motion_config": {
        "enabled": true,
        "sensitivity": 7,
        "threshold": 500,
        "cooldown": 5,
        "roi": ""
      },
      "uses_global_motion": false
    }
  ]
}
```

### POST `/api/cameras`
Request:
```json
{
  "name": "Gate",
  "type": "thermal",
  "rtsp_url_thermal": "rtsp://user:pass@host/stream",
  "channel_color": 102,
  "channel_thermal": 202,
  "motion_config": { "enabled": true, "sensitivity": 7, "threshold": 500, "cooldown": 5, "roi": "" }
}
```

### PUT `/api/cameras/{id}`
Request (partial update):
```json
{
  "name": "Gate West",
  "motion_config": { "enabled": true, "sensitivity": 6, "threshold": 400, "cooldown": 5 }
}
```

### POST `/api/cameras/{id}/test`
Response:
```json
{ "ok": true, "snapshot": "<base64>", "latency_ms": 120 }
```

### POST `/api/cameras/test`
Request: same as camera create payload.
Response: same as camera test response.

## Events
### GET `/api/events`
Response:
```json
{
  "events": [
    {
      "event_id": "evt-1",
      "event_type": "motion",
      "timestamp": "2026-01-01T00:00:00Z",
      "camera_id": "cam-1",
      "payload": {
        "threat_level": "low",
        "summary": "Motion detected",
        "details": "Person near gate",
        "confidence": 0.64,
        "screenshot_id": "shot-1"
      }
    }
  ],
  "count": 1
}
```

## Media
### GET `/api/screenshots/{id}/collage`
Returns a 5-frame collage image.

### GET `/api/screenshots/{id}/clip.mp4`
Returns an MP4 clip for the event.

## Telegram Tests
### POST `/api/notifications/telegram/test-message`
Response: `{ "sent": true }`

### POST `/api/notifications/telegram/test-snapshot`
Request: `{ "camera_id": "cam-1" }`
Response: `{ "sent": true }`
