# Thermal Vision AI - Project Context

## Project Overview
AI-powered thermal and color camera motion detection system with YOLO object detection
and GPT-4 Vision analysis. Works standalone or as Home Assistant add-on.

**Repository:** https://github.com/cataloglu/thermal-vision-ai

## Key Differentiator
**We do NOT use camera's built-in motion detection or NVR integrations.**

Our approach:
- ✅ **Own image processing** using OpenCV BackgroundSubtractorMOG2
- ✅ **Real-time frame analysis** - we process every frame ourselves
- ✅ **YOLO object verification** - AI confirms what triggered motion
- ✅ **LLM intelligent analysis** - GPT-4 Vision describes the scene
- ✅ **Brand-agnostic** - works with ANY RTSP camera (thermal or color)
- ✅ **Full control** - our own sensitivity, thresholds, and logic

This makes us independent from:
- ❌ Camera firmware quality/bugs
- ❌ Vendor-specific motion detection algorithms
- ❌ ONVIF event limitations
- ❌ NVR/DVR proprietary integrations

## Operating Modes
```
HA_MODE=true   → Home Assistant Add-on (ingress, MQTT auto-discovery, bashio)
HA_MODE=false  → Standalone Docker container (direct port, config file)
```

## Tech Stack
- **Language**: Python 3.11+
- **Motion Detection**: OpenCV BackgroundSubtractorMOG2
- **Object Detection**: YOLOv8 Nano (ultralytics)
- **Vision AI**: OpenAI GPT-4 Vision
- **Camera**: OpenCV VideoCapture, RTSP/HTTP streams
- **Web UI**: Flask + Vite + Preact + Tailwind CSS
- **Communication**: MQTT, Telegram Bot API
- **Container**: Docker (multi-arch: amd64, aarch64)

## Thermal Camera Features
- Thermal + Color dual camera support
- Heat anomaly detection (temperature thresholds)
- Automatic day/night mode switching
- Thermal-visible image fusion
- Compatible with: FLIR, Hikvision Thermal, InfiRay, etc.

## System Requirements
- FFmpeg (video processing)
- OpenCV dependencies (libgl1, libglib2.0)
- CUDA (optional, for GPU acceleration)
- Node.js (for web UI build)

## Architecture
```
┌─────────────────┐     ┌─────────────────┐
│  Thermal Cam    │     │   Color Cam     │
│   (RTSP)        │     │    (RTSP)       │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   Motion Detection    │
         │ (BackgroundSubtractor)│
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   YOLO Detection      │
         │   (Object Verify)     │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │  Screenshot Capture   │
         │  (Before/Now/After)   │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   LLM Vision Analysis │
         │   (GPT-4 Vision)      │
         └───────────┬───────────┘
                     ▼
    ┌────────────────┴────────────────┐
    ▼                                 ▼
┌─────────┐  ┌─────────┐  ┌───────────────┐
│  MQTT   │  │Telegram │  │   Web UI      │
│ Publish │  │  Bot    │  │  Dashboard    │
└─────────┘  └─────────┘  └───────────────┘
```

## Key Features
1. Dual camera support (Thermal + RGB)
2. Own motion detection (not camera's)
3. 3-screenshot verification (before/now/after)
4. AI-powered false positive reduction
5. Real-time web dashboard
6. Standalone or HA add-on mode
7. Turkish language analysis output

## File Structure
```
/
├── config.yaml              # HA Add-on configuration
├── Dockerfile               # Container build
├── docker-compose.yml       # Standalone deployment
├── run.sh                   # HA entry point
├── requirements.txt         # Python dependencies
├── src/
│   ├── __init__.py
│   ├── config.py            # Configuration management
│   ├── logger.py            # Logging module
│   ├── utils.py             # Helper functions
│   ├── camera.py            # Camera abstraction
│   ├── motion_detector.py   # OpenCV motion detection
│   ├── yolo_detector.py     # YOLO integration
│   ├── screenshot_manager.py
│   ├── llm_analyzer.py      # GPT-4 Vision
│   ├── mqtt_client.py       # MQTT communication
│   ├── telegram_bot.py      # Telegram integration
│   ├── web_server.py        # Flask web server
│   ├── api/                 # REST API endpoints
│   └── main.py              # Main application
├── web/                     # Frontend (Vite + Preact)
│   ├── src/
│   │   ├── pages/
│   │   └── components/
│   └── package.json
├── tests/                   # Test suite
└── docs/                    # Documentation
```

## Language
- Code comments: English
- User-facing messages: Turkish
- Documentation: Both TR and EN
