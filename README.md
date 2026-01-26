# Thermal Dual Vision (Smart Motion Detector v2)

Person‑only motion detection for thermal + color cameras, built as a **Home Assistant add‑on**.

## 🔥 Highlights
- 🎯 **Person‑only detection** (YOLOv8/YOLOv9)
- 🌡️ **Thermal / Color / Dual** camera support
- 🎬 **Event media**: 5‑frame collage + MP4 timelapse
- 🧠 **Optional AI summaries** (OpenAI, key optional)
- 🔔 **Telegram alerts** + **MQTT auto‑discovery** (HA)
- ⚡ **Performance presets** + per‑camera zones

## 🚀 Quick Start

### Home Assistant Add‑on
- Add the repository in HA
- Configure options in the add‑on UI
- Open Web UI via Ingress

See: [`TASK_HA_ADDON.md`](TASK_HA_ADDON.md)

### Local Dev
```bash
cp env.example .env
docker-compose up -d
# UI: http://localhost:5173
# API: http://localhost:8000
```

## 📚 Docs (Short List)
- Product: [`docs/PRODUCT.md`](docs/PRODUCT.md)
- Config: [`docs/CONFIG_REFERENCE.md`](docs/CONFIG_REFERENCE.md)
- Performance: [`docs/PERFORMANCE_TUNING.md`](docs/PERFORMANCE_TUNING.md)
- Media: [`docs/MEDIA_SPEC.md`](docs/MEDIA_SPEC.md)
- Development: [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)

## 🧪 Tests
```bash
pytest
```

## 📄 License
MIT
