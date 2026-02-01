# Thermal Dual Vision (Smart Motion Detector v2)

Person‑only motion detection for thermal + color cameras, built as a **Home Assistant add‑on**.

## 🔥 Highlights
- 🎯 **Person‑only detection** (YOLOv8/YOLOv9)
- 🌡️ **Thermal / Color / Dual** camera support
- 🎬 **Event media**: 5‑frame collage + MP4 timelapse
- 🧠 **Optional AI summaries** (OpenAI, key optional)
- 🔔 **Telegram alerts** + **MQTT auto‑discovery** (HA)
- ⚡ **Performance presets** + per‑camera zones
- 🚀 **NEW (v2.2)**: TensorRT/ONNX optimization, MOG2 motion, Prometheus metrics

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
- **NEW**: Technical Analysis: [`docs/TECHNICAL_ANALYSIS.md`](docs/TECHNICAL_ANALYSIS.md)
- **NEW**: Upgrade Guide: [`docs/UPGRADE_GUIDE.md`](docs/UPGRADE_GUIDE.md)
- **NEW**: Optimization Complete: [`docs/OPTIMIZATION_COMPLETE.md`](docs/OPTIMIZATION_COMPLETE.md)

## 🧪 Tests & Benchmarking

### Unit Tests
```bash
pytest tests/ -v
```

### Performance Benchmarking (NEW)
```bash
# Inference, preprocessing, filtering benchmarks
python tests/benchmark_performance.py
```

### Monitoring (NEW)
```bash
# Start with metrics enabled
# Config: performance.enable_metrics = true
# Metrics: http://localhost:9090/metrics
# Grafana: Import docs/grafana-dashboard.json
```

## 📄 License
MIT
