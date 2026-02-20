# Thermal Dual Vision — Smart Motion Detector

> Home Assistant addon · v3.10.102 · AI-powered person detection for thermal & color cameras

## What is this?

Thermal Dual Vision is a Home Assistant addon that runs a real-time person-only detection pipeline for thermal, color, or dual (thermal+color) IP cameras over RTSP. When a person is detected, it generates an event with a multi-frame collage, a timelapse MP4, sends a Telegram notification, and publishes to MQTT for Home Assistant automations.

## Features

- **Person-only detection** — YOLOv8n/s or YOLOv9t/s models; filters out animals, vehicles, shadows
- **Thermal, color & dual camera support** — per-camera type with separate thermal enhancement (CLAHE)
- **go2rtc integration** — RTSP restreaming via embedded go2rtc; live MJPEG view proxied through it
- **Event media** — multi-frame collage (JPEG) + timelapse MP4 with pre/post-buffer recording
- **Continuous background recording** — 1-hour rolling buffer for clean event video extraction
- **Telegram notifications** — sends collage image + event MP4 with configurable rate limiting
- **MQTT auto-discovery** — publishes camera entities and events for Home Assistant; native `mqtt:need` integration
- **Optional AI summaries** — OpenAI GPT-4o/GPT-4o-mini vision analysis of event collages (API key required)
- **Per-camera detection zones** — polygonal include/exclude zones (motion or person mode)
- **Motion pre-filter** — MOG2/KNN/frame-diff background subtraction before running YOLO
- **Pluggable inference backends** — auto-selects TensorRT (NVIDIA) > OpenVINO (Intel GPU) > ONNX > PyTorch CPU
- **Worker modes** — threading (default, stable) or multiprocessing (experimental, bypasses GIL)
- **Prometheus metrics** — optional `/metrics` endpoint for Grafana dashboards
- **Web UI** — React-based dashboard with live view, events browser, zones editor, MQTT monitor, diagnostics, logs

## Supported Hardware

| Architecture | Notes |
|---|---|
| `amd64` | Full support; TensorRT on NVIDIA GPU, OpenVINO on Intel iGPU |
| `aarch64` | Full support (Raspberry Pi 4/5, Jetson) |

**Inference backends** (auto-detected or manually selected):
- `tensorrt` — NVIDIA GPU (fastest, requires `.engine` file)
- `openvino` — Intel iGPU/NPU/CPU (Intel NUC, i5/i7 with iGPU)
- `onnx` — CPU via ONNX Runtime (good balance)
- `cpu` — PyTorch CPU (fallback, any hardware)

## Installation

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**
2. Add the repository: `https://github.com/cataloglu/thermal-dual-vision`
3. Install **Thermal Dual Vision**
4. Configure MQTT in HA (the addon requests `mqtt:need` from Supervisor)
5. Open the Web UI via Ingress (panel icon: `mdi:cctv`, title: `Thermal Vision`)

**Direct ports** (if not using Ingress):
- `8099` — Web UI + API
- `1985` — go2rtc API
- `19854` — go2rtc RTSP restream

## Configuration

All settings are managed via the Web UI Settings page or the REST API (`PUT /api/settings`). Configuration is persisted to `/app/data/config.json`.

| Group | Key settings |
|---|---|
| `detection` | model, confidence threshold, inference FPS, resolution, backend, aspect ratio preset |
| `motion` | algorithm (mog2/knn/frame_diff), sensitivity, min area, cooldown |
| `thermal` | enhancement enable, CLAHE clip limit, tile size, Gaussian blur |
| `stream` | RTSP protocol (tcp/udp), capture backend, reconnect settings |
| `live` | output mode (mjpeg/webrtc), MJPEG quality, overlay timezone |
| `event` | cooldown, pre/post buffer seconds, record FPS, min event duration |
| `media` | retention days, cleanup interval, disk limit % |
| `ai` | enabled, OpenAI API key, model, language, custom prompt |
| `telegram` | enabled, bot token, chat IDs, rate limit, video speed |
| `mqtt` | enabled, broker host/port, credentials, topic prefix |
| `performance` | worker mode (threading/multiprocessing), Prometheus metrics |
| `appearance` | theme (slate/carbon/pure-black/matrix), UI language (tr/en) |

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for the full reference.

## API

Base URL: `http://<ha-host>:8099` (or via Ingress)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check with pipeline, MQTT, Telegram status |
| `GET/PUT` | `/api/settings` | Get or update configuration (partial updates supported) |
| `GET` | `/api/cameras` | List cameras |
| `POST` | `/api/cameras` | Create camera |
| `PUT` | `/api/cameras/{id}` | Update camera |
| `DELETE` | `/api/cameras/{id}` | Delete camera |
| `POST` | `/api/cameras/test` | Test RTSP connection, returns snapshot |
| `GET` | `/api/cameras/{id}/zones` | Get detection zones |
| `POST` | `/api/cameras/{id}/zones` | Create detection zone |
| `GET` | `/api/events` | List events (pagination, filter by camera/date/confidence) |
| `GET` | `/api/events/{id}` | Get event detail with media URLs |
| `DELETE` | `/api/events/{id}` | Delete event |
| `POST` | `/api/events/bulk-delete` | Bulk delete events |
| `GET` | `/api/events/{id}/collage` | Event collage JPEG |
| `GET` | `/api/events/{id}/timelapse.mp4` | Event timelapse MP4 |
| `GET` | `/api/live/{id}.mjpeg` | Live MJPEG stream (go2rtc proxied) |
| `GET` | `/api/live/{id}.jpg` | Single live snapshot |
| `GET` | `/api/mqtt/status` | MQTT connection status and publish stats |
| `POST` | `/api/telegram/test` | Send test Telegram message |
| `POST` | `/api/ai/test` | Test OpenAI connection |
| `GET` | `/api/logs` | Application logs (last N lines) |
| `GET` | `/api/system/info` | CPU, memory, disk usage |
| `WS` | `/api/ws/events` | WebSocket for real-time event/status push |

## Web UI Pages

- **Dashboard** — camera status overview, recent events
- **Live** — MJPEG live view per camera
- **Events** — event browser with collage/video viewer
- **Settings** — full configuration (cameras, detection, motion, zones, AI, Telegram, MQTT, performance, appearance)
- **MQTT Monitoring** — live topic view, publish stats
- **Diagnostics** — system info, worker mode, camera status
- **Logs** — real-time application log viewer
- **Video Analysis** — analyze event video for quality issues

## Local Development

```bash
cp env.example .env
docker-compose up -d
# UI: http://localhost:5173
# API: http://localhost:8000
```

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## License

MIT
