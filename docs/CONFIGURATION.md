# Configuration Reference

All settings are stored in `/app/data/config.json` and can be managed via the Web UI Settings page or the REST API (`GET/PUT /api/settings`). Secrets (API keys, tokens, passwords) are masked in API responses with `***REDACTED***`.

Partial updates are supported: only send the keys you want to change.

```json
PUT /api/settings
{"detection": {"inference_fps": 3}}
```

---

## detection

YOLOv8/YOLOv9 person detection settings.

| Setting | Type | Default | Description |
|---|---|---|---|
| `model` | string | `yolov8s-person` | Model: `yolov8n-person` (fast), `yolov8s-person` (accurate), `yolov9t` (thermal-tuned), `yolov9s` (best) |
| `confidence_threshold` | float 0–1 | `0.30` | Minimum YOLO confidence for color camera detections |
| `thermal_confidence_threshold` | float 0–1 | `0.35` | Minimum confidence for thermal camera detections |
| `nms_iou_threshold` | float 0–1 | `0.45` | Non-Maximum Suppression IoU threshold |
| `inference_resolution` | [int, int] | `[640, 640]` | Inference frame size [width, height]. Lower values (e.g. 416×416) reduce CPU significantly |
| `inference_fps` | int 1–30 | `5` | Frames per second sent to inference. 1–2 for low CPU, 5+ for smooth detection |
| `aspect_ratio_preset` | string | `person` | `person` (general, 0.2–1.2), `thermal_person` (thermal, 0.25–1.0), `custom` (use min/max below) |
| `aspect_ratio_min` | float 0–5 | `0.2` | Minimum width/height ratio; only used when preset is `custom` |
| `aspect_ratio_max` | float 0–5 | `1.2` | Maximum width/height ratio; only used when preset is `custom` |
| `inference_backend` | string | `auto` | `auto` (TensorRT > OpenVINO > ONNX > PyTorch), `tensorrt`, `openvino`, `onnx`, `cpu` |
| `enable_tracking` | bool | `false` | Object tracking (reserved for future use) |

---

## motion

Background subtraction pre-filter. Runs before YOLO to skip frames with no motion and reduce CPU load.

| Setting | Type | Default | Description |
|---|---|---|---|
| `algorithm` | string | `mog2` | `frame_diff` (simple), `mog2` (stable, shadow-resistant), `knn` (adaptive) |
| `sensitivity` | int 1–10 | `8` | Motion sensitivity. Higher = triggers on smaller movements |
| `min_area` | int ≥ 0 | `450` | Minimum pixel area of moving region to consider as motion |
| `cooldown_seconds` | int ≥ 0 | `6` | Seconds between consecutive motion triggers per camera |

**Built-in presets** (reference values, not editable):

| Preset | sensitivity | min_area | cooldown |
|---|---|---|---|
| `thermal_recommended` | 9 | 350 | 6 |
| `color_recommended` | 8 | 400 | 6 |

---

## thermal

Image enhancement applied to thermal camera frames before inference.

| Setting | Type | Default | Description |
|---|---|---|---|
| `enable_enhancement` | bool | `true` | Enable thermal enhancement pipeline |
| `enhancement_method` | string | `clahe` | `clahe` (contrast limited adaptive), `histogram` (global), `none` |
| `clahe_clip_limit` | float ≥ 0 | `2.0` | CLAHE contrast clip limit. Higher = more contrast, more noise |
| `clahe_tile_size` | [int, int] | `[32, 32]` | CLAHE grid tile size. Larger = less blockiness |
| `gaussian_blur_kernel` | [int, int] | `[3, 3]` | Gaussian blur kernel size applied before enhancement |

---

## stream

RTSP stream ingestion settings (camera → go2rtc → detector).

| Setting | Type | Default | Description |
|---|---|---|---|
| `protocol` | string | `tcp` | `tcp` (recommended for reliability) or `udp` |
| `capture_backend` | string | `auto` | `auto`, `opencv`, or `ffmpeg` |
| `buffer_size` | int ≥ 1 | `1` | OpenCV VideoCapture internal buffer size |
| `reconnect_delay_seconds` | int ≥ 1 | `10` | Seconds between reconnect attempts on failure |
| `max_reconnect_attempts` | int ≥ 1 | `20` | Maximum consecutive reconnect attempts before marking camera as DOWN |
| `read_failure_threshold` | int ≥ 1 | `5` | Consecutive read failures before triggering reconnect |
| `read_failure_timeout_seconds` | float 1–60 | `20.0` | Seconds without a frame before triggering reconnect |

---

## live

Live view output settings (browser → UI).

| Setting | Type | Default | Description |
|---|---|---|---|
| `output_mode` | string | `mjpeg` | `mjpeg` (proxied from go2rtc or worker fallback) or `webrtc` |
| `mjpeg_quality` | int 50–100 | `92` | JPEG quality for MJPEG stream. Higher = better quality, more bandwidth |
| `overlay_timezone` | string | `local` | `local` (server local time) or `utc` — used for video overlay timestamps |
| `webrtc.enabled` | bool | `false` | Enable WebRTC output |
| `webrtc.go2rtc_url` | string | `""` | go2rtc server URL for WebRTC signaling |

---

## event

Event trigger and buffer configuration.

| Setting | Type | Default | Description |
|---|---|---|---|
| `cooldown_seconds` | int ≥ 0 | `7` | Minimum seconds between events per camera. Prevents rapid-fire duplicates |
| `prebuffer_seconds` | float 0–60 | `5.0` | Seconds of video before detection to include in the timelapse |
| `postbuffer_seconds` | float 0–60 | `5.0` | Seconds of video after detection to include in the timelapse |
| `record_fps` | int 1–30 | `10` | Frame rate for the event video buffer |
| `frame_buffer_size` | int ≥ 1 | `10` | Number of frames kept for collage generation |
| `frame_interval` | int ≥ 1 | `2` | Frame capture interval for collage |
| `min_event_duration` | float ≥ 0 | `1.0` | Minimum continuous detection time (seconds) before triggering an event |

---

## media

Media file retention and disk management.

| Setting | Type | Default | Description |
|---|---|---|---|
| `retention_days` | int 0–365 | `7` | Days to keep event media. `0` = unlimited |
| `cleanup_interval_hours` | int ≥ 1 | `24` | How often the retention job runs |
| `disk_limit_percent` | int 50–95 | `85` | Oldest events are deleted when disk usage exceeds this percentage |

---

## ai

Optional OpenAI vision integration for event summaries.

| Setting | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `false` | Enable AI event summary generation |
| `api_key` | string | `""` | OpenAI API key (must start with `sk-`). Masked in responses |
| `model` | string | `gpt-4o` | `gpt-4o`, `gpt-4o-mini`, or `gpt-4-vision-preview` |
| `prompt_template` | string | `default` | `default` (built-in prompt) or `custom` (use `custom_prompt`) |
| `custom_prompt` | string | `""` | Custom prompt text when `prompt_template = custom` |
| `language` | string | `tr` | AI response language: `tr` (Turkish) or `en` (English) |
| `max_tokens` | int ≥ 1 | `200` | Maximum tokens per AI response |
| `temperature` | float 0–1 | `0.3` | Response randomness. Lower = more consistent |
| `timeout` | int ≥ 1 | `30` | API request timeout in seconds |

---

## telegram

Telegram bot notification settings.

| Setting | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `false` | Enable Telegram notifications |
| `bot_token` | string | `""` | Telegram bot token (format: `123456:ABCDef...`). Masked in responses |
| `chat_ids` | list[string] | `[]` | List of numeric chat IDs (e.g. `["-100123456789"]`) |
| `rate_limit_seconds` | int ≥ 0 | `5` | Minimum seconds between messages |
| `send_images` | bool | `true` | Send collage image with notifications |
| `video_speed` | int ≥ 1 | `2` | Timelapse speed multiplier (2 = 2× speed) |
| `cooldown_seconds` | int ≥ 0 | `5` | Per-camera cooldown between notifications |
| `max_messages_per_min` | int ≥ 1 | `20` | Global rate cap (Telegram API limit) |
| `snapshot_quality` | int 0–100 | `85` | JPEG quality for snapshot images in notifications |

---

## mqtt

MQTT broker connection and HA auto-discovery settings.

| Setting | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `false` | Enable MQTT integration |
| `host` | string | `core-mosquitto` | MQTT broker hostname (default is HA's built-in Mosquitto addon) |
| `port` | int | `1883` | MQTT broker port |
| `username` | string | `null` | MQTT username (optional; leave null for anonymous) |
| `password` | string | `null` | MQTT password. Masked in responses |
| `topic_prefix` | string | `thermal_vision` | Prefix for all MQTT topics |

**Topics published** (with default prefix `thermal_vision`):
- `thermal_vision/status` — addon online/offline
- `thermal_vision/{camera_id}/state` — camera connection state
- `thermal_vision/{camera_id}/event` — detection event payload (JSON)
- `homeassistant/binary_sensor/thermal_vision_{camera_id}/config` — HA discovery

---

## performance

Worker and observability settings.

| Setting | Type | Default | Description |
|---|---|---|---|
| `worker_mode` | string | `threading` | `threading` (stable, default) or `multiprocessing` (experimental, bypasses GIL) |
| `enable_metrics` | bool | `false` | Expose Prometheus metrics at `http://host:{metrics_port}/metrics` |
| `metrics_port` | int 1024–65535 | `9090` | Port for Prometheus metrics HTTP server |

---

## appearance

Web UI theme and language.

| Setting | Type | Default | Description |
|---|---|---|---|
| `theme` | string | `pure-black` | `slate`, `carbon`, `pure-black`, `matrix` |
| `language` | string | `tr` | UI language: `tr` (Turkish) or `en` (English) |
