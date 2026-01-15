# Smart Motion Detector - Project Context

## Project Overview
A Home Assistant add-on for intelligent motion detection using thermal and RGB cameras, 
with YOLO object detection and LLM Vision AI analysis.

## Tech Stack
- **Language**: Python 3.11
- **Framework**: Home Assistant Add-on
- **ML/AI**: YOLOv8 (ultralytics), OpenAI GPT-4 Vision / Ollama LLaVA
- **Camera**: OpenCV for capture, RTSP/HTTP streams
- **Communication**: MQTT, Telegram Bot API
- **Container**: Docker

## System Requirements
- FFmpeg (video processing)
- OpenCV dependencies (libgl1, libglib2.0)
- CUDA (optional, for GPU acceleration)

## Architecture
```
Camera Input → Motion Detection → YOLO Detection → Screenshot Capture
                                                          ↓
                                              LLM Vision Analysis
                                                          ↓
                                    MQTT Publish + Telegram Notification
```

## Key Features
1. Dual camera support (Thermal + RGB)
2. 3-screenshot verification (before/now/after)
3. AI-powered false positive reduction
4. Turkish language analysis output
5. Home Assistant auto-discovery

## File Structure
```
/
├── config.yaml          # Add-on configuration
├── Dockerfile           # Container build
├── run.sh              # Entry point
├── requirements.txt    # Python dependencies
├── src/
│   ├── camera.py       # Camera abstraction
│   ├── motion_detector.py
│   ├── yolo_detector.py
│   ├── screenshot_manager.py
│   ├── llm_analyzer.py
│   ├── mqtt_client.py
│   ├── telegram_bot.py
│   └── main.py         # Main application
└── README.md
```

## Language
- Code comments: English
- User-facing messages: Turkish
- Documentation: Both TR and EN
