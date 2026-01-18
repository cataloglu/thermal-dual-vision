# Metrics & Logging

This document defines baseline metrics and standard log format requirements.

## Core metrics
- `frame_fps`: frames processed per second
- `event_rate`: events emitted per minute
- `pipeline_latency_ms`: average pipeline latency
- `mqtt_publish_ms`: MQTT publish latency
- `telegram_send_ms`: Telegram send latency
- `memory_mb`: process RSS
- `cpu_percent`: process CPU usage

## Log format
Structured JSON (preferred):
```
{
  "ts": "2026-01-18T02:00:00Z",
  "level": "INFO",
  "component": "pipeline.dual",
  "message": "Dual stream sync",
  "camera_id": "cam-01",
  "event_id": "uuid",
  "meta": { "delta_ms": 85.2 }
}
```

## Log levels
- `DEBUG`: detailed flow and diagnostic data
- `INFO`: state changes and key events
- `WARNING`: recoverable issues
- `ERROR`: failures that require attention

## Observability compatibility
- JSON logs are compatible with ELK / Loki / CloudWatch.
- Metrics can be exported via Prometheus in a future phase.
