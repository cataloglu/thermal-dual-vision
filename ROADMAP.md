# Thermal Dual Vision – Roadmap

## Amaç
RTSP üzerinden thermal ve color kameraları işleyip Home Assistant add-on olarak çalışmak.

## Vizyon
- Multi-camera (thermal + color)
- Ayrı pipeline (ThermalPipeline / ColorPipeline)
- Ortak event modeli
- Web UI + MQTT + Telegram

## Sprint 1 (Core)
- Multi-camera config
- Pipeline interface
- UI kamera sekmeleri
- Health/Ready genişletme

## Sprint 2 (MVP)
- Color motion detection
- Thermal hotspot/ROI
- Event bus

## Sprint 3 (Advanced)
- YOLO (color)
- Observability
- CI/CD
