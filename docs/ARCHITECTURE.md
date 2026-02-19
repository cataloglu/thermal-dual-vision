# Architecture — Thermal Dual Vision

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        Home Assistant Host                       │
│                                                                  │
│  ┌─────────────┐      ┌──────────────────────────────────────┐  │
│  │ IP Camera   │─RTSP→│             go2rtc                   │  │
│  │ (thermal /  │      │  - RTSP restream (:19854)            │  │
│  │  color /    │      │  - MJPEG /api/stream.mjpeg           │  │
│  │  dual)      │      │  - API (:1985)                       │  │
│  └─────────────┘      └──────┬──────────────────────────┬───┘  │
│                               │ RTSP restream            │       │
│                    ┌──────────▼──────────┐   ┌──────────▼────┐  │
│                    │   DetectorWorker    │   │  Continuous   │  │
│                    │  (per-camera thread)│   │  Recorder     │  │
│                    │                     │   │ (1hr rolling) │  │
│                    │  1. Read frame      │   └───────────────┘  │
│                    │  2. Motion filter   │                       │
│                    │  3. YOLO inference  │                       │
│                    │  4. Zone check      │                       │
│                    │  5. Event emit      │                       │
│                    └──────────┬──────────┘                       │
│                               │ detection event                  │
│          ┌────────────────────┼─────────────────────┐           │
│          ▼                    ▼                      ▼           │
│  ┌──────────────┐   ┌─────────────────┐   ┌──────────────────┐  │
│  │  SQLite DB   │   │ Media Service   │   │  Notification    │  │
│  │  (events,    │   │ - Collage JPEG  │   │  - Telegram      │  │
│  │   cameras,   │   │ - Timelapse MP4 │   │  - MQTT publish  │  │
│  │   zones)     │   │   (from buffer) │   │  - WebSocket     │  │
│  └──────────────┘   └─────────────────┘   └──────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              FastAPI (port 8099)                         │   │
│  │  REST API + WebSocket + MJPEG proxy + static UI          │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

## Key Components

### FastAPI Application (`app/main.py`)

The central entry point. Manages application lifespan (startup/shutdown), initializes all services, and exposes all REST endpoints and WebSocket. On startup:
1. Starts the retention worker
2. Waits 10 seconds for services (go2rtc) to initialize
3. Syncs all cameras to go2rtc
4. Starts the detector worker (threading or multiprocessing)
5. Starts continuous recording for all enabled cameras
6. Starts the MQTT service

### go2rtc

Embedded RTSP server that restreams camera feeds. All detection and live streams are pulled from go2rtc, not directly from cameras. This decouples the camera from multiple consumers (detector, recorder, live view) and provides resilience against camera disconnects.

- Config: auto-generated at runtime per camera
- RTSP endpoint: `rtsp://127.0.0.1:8554/{camera_id}_{color|thermal}`
- MJPEG API: `http://127.0.0.1:1984/api/stream.mjpeg?src=...`

### DetectorWorker (`app/workers/detector.py`)

Runs one detection thread per camera. Pipeline per frame:
1. **Frame read** — from go2rtc RTSP restream via OpenCV or ffmpeg
2. **Motion pre-filter** — MOG2/KNN/frame-diff; skips YOLO if no motion
3. **Thermal enhancement** — CLAHE or histogram equalization (thermal cameras only)
4. **YOLO inference** — YOLOv8/YOLOv9 person detection at configured FPS and resolution
5. **Aspect ratio filter** — rejects detections that don't match person proportions
6. **Zone check** — polygon containment test for per-camera zones (include/exclude)
7. **Temporal consistency** — requires N consecutive detections before triggering event
8. **Event generation** — creates event record, saves collage, triggers notifications

Also maintains `latest_frames` dict used as the live MJPEG fallback.

**Multiprocessing mode** (`app/workers/detector_mp.py`): Experimental alternative that spawns one process per camera, bypassing Python GIL for true parallel inference. Enabled via `performance.worker_mode = "multiprocessing"`.

### Continuous Recorder (`app/services/recorder.py`)

Runs FFmpeg in the background to maintain a rolling 1-hour MPEG-TS segment buffer per camera (from go2rtc RTSP). When an event is detected, the detector clips the relevant pre/post-buffer window from the rolling buffer to produce the timelapse MP4.

### Inference Service (`app/services/inference.py`)

Loads and runs YOLO models. Backend auto-selection priority:
1. **TensorRT** — if `.engine` file exists (NVIDIA GPU)
2. **OpenVINO** — if Intel iGPU/NPU is detected via OpenVINO runtime
3. **ONNX** — if `.onnx` file exists (CPU via ONNX Runtime)
4. **PyTorch CPU** — fallback, uses `.pt` file

Models stored in `/app/data/models/`. First run downloads from Ultralytics.

### MQTT Service (`app/services/mqtt.py`)

Connects to the broker configured via `services: mqtt:need` (HA Supervisor injects credentials). Publishes:
- **HA auto-discovery** configs for each camera (binary sensor, camera entity)
- **Event payloads** on `{prefix}/{camera_id}/event`
- **Availability** on `{prefix}/status`
- **Camera status** on `{prefix}/{camera_id}/state`

Monitoring endpoint at `GET /api/mqtt/status` exposes active topics, publish count, and last messages.

### AI Service (`app/services/ai.py`)

Optional OpenAI vision integration. On each event, if enabled:
- Reads the box-free collage image
- Sends to GPT-4o (or configured model) with a system prompt describing the camera type
- Stores the text summary on the event record
- Low-confidence detections include a warning in the prompt

### Telegram Service (`app/services/telegram.py`)

Sends collage photo + timelapse MP4 video to configured chat IDs. Respects rate limits (`rate_limit_seconds`, `max_messages_per_min`). Video speed is configurable (default 2x = 10s from 20s clip).

### Retention Worker (`app/workers/retention.py`)

Background thread that runs every `media.cleanup_interval_hours` hours. Deletes events and their media files older than `media.retention_days` days, and enforces `media.disk_limit_percent`.

## Data Flow: RTSP → Event → Notification

```
Camera RTSP
    │
    ▼
go2rtc restream (RTSP :8554)
    │
    ├──→ DetectorWorker thread
    │        │
    │        ├── Motion filter (skip if no motion)
    │        ├── Thermal CLAHE enhancement
    │        ├── YOLO inference (at inference_fps)
    │        ├── Aspect ratio + zone filter
    │        ├── Temporal consistency check
    │        └── Event triggered
    │                │
    │                ├── SQLite: INSERT event
    │                ├── Media: save collage JPEG
    │                ├── Media: extract MP4 from rolling buffer
    │                ├── AI: analyze collage (optional)
    │                ├── Telegram: send photo + video
    │                ├── MQTT: publish event payload
    │                └── WebSocket: push to UI clients
    │
    └──→ ContinuousRecorder (FFmpeg, rolling 1hr buffer)
```

## Database Models

SQLite database at `/app/data/app.db`.

### `cameras`
| Column | Type | Notes |
|---|---|---|
| `id` | String(36) | UUID primary key |
| `name` | String(100) | Display name |
| `type` | Enum | `color`, `thermal`, `dual` |
| `enabled` | Boolean | Whether detection is active |
| `rtsp_url_color` | String(500) | Color stream URL |
| `rtsp_url_thermal` | String(500) | Thermal stream URL |
| `rtsp_url_detection` | String(500) | Optional detection-specific stream |
| `detection_source` | Enum | `color`, `thermal`, `auto` |
| `stream_roles` | JSON | `["detect", "live"]` |
| `status` | Enum | `connected`, `retrying`, `down`, `initializing` |
| `motion_config` | JSON | Per-camera motion override |

### `zones`
| Column | Type | Notes |
|---|---|---|
| `id` | String(36) | UUID |
| `camera_id` | FK → cameras | Cascade delete |
| `name` | String(100) | Display name |
| `enabled` | Boolean | |
| `mode` | Enum | `motion`, `person`, `both` |
| `polygon` | JSON | `[[x,y], ...]` normalized 0.0–1.0 |

### `events`
| Column | Type | Notes |
|---|---|---|
| `id` | String(36) | UUID |
| `camera_id` | FK → cameras | Cascade delete |
| `timestamp` | DateTime | Detection time (indexed) |
| `confidence` | Float | YOLO confidence score |
| `event_type` | String | Default `"person"` |
| `person_count` | Integer | Number of persons detected |
| `summary` | Text | AI-generated text (optional) |
| `ai_enabled` | Boolean | Whether AI was used |
| `rejected_by_ai` | Boolean | AI rejected but kept for review |
| `collage_url` | String | Path to collage JPEG |
| `gif_url` | String | Path to preview GIF |
| `mp4_url` | String | Path to timelapse MP4 |

### `recording_state`
Per-camera boolean recording toggle, persisted across restarts.

## API Structure

All routes under `/api/`. See the full reference in `README.md`.

Key route groups:
- `/api/settings` — global config CRUD
- `/api/cameras` — camera CRUD + zones + snapshots + recording control
- `/api/events` — event CRUD + media file serving
- `/api/live/{id}.mjpeg` — MJPEG stream (go2rtc proxied, falls back to worker frames)
- `/api/mqtt/status` — MQTT monitoring
- `/api/ai/*` — AI connection tests
- `/api/telegram/test` — Telegram connection test
- `/api/system/info` — system metrics (psutil)
- `/api/ws/events` — WebSocket for real-time push
