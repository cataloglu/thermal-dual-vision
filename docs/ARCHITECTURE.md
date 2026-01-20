# ARCHITECTURE — Smart Motion Detector (v2)

## 1) Tech Stack (Karar)
- Backend: Python 3.11 + FastAPI
- Video: OpenCV + FFmpeg
- Detection: YOLOv8 (ultralytics)
- Storage:
  - Config: JSON file (`/app/data/config.json`)
  - Metadata: SQLite (`/app/data/app.db`)
  - Media: filesystem (`/app/data/media/...`)
- Frontend: React + Vite + TypeScript + Tailwind
- Realtime: WebSocket (events/live status), MJPEG/WebRTC for streams

---

## 2) Bileşenler
- API Server (FastAPI)
- Detector Worker (frame ingest + inference + event üretimi)
- Media Worker (collage/gif/mp4 üretimi)
- Retention Worker (disk temizleme)

---

## 3) Deployment
- Standalone: Docker Compose
- Home Assistant: Ingress (API base path `/api/...`)

---

## 4) Dizin Yapısı (Backend)
- `/app`:
  - `main.py` (API)
  - `workers/` (detector/media/retention)
  - `services/` (camera, events, settings)
  - `data/` (config, db, media)

---

## 5) Dizin Yapısı (Frontend)
- `/ui`:
  - `src/components`
  - `src/pages`
  - `src/services` (API client)
  - `src/hooks`
  - `src/types`

---

## 6) Model Dosyaları
- Varsayılan konum: `/app/models/`
  - `/app/models/yolov8n-person.pt`
  - `/app/models/yolov8s-person.pt`
- İlk çalıştırmada eksikse otomatik indirilir.

---

## 7) Kaynak Gereksinimleri (MVP)
- Önerilen minimum: 4 CPU / 8 GB RAM
- Disk: en az 20 GB boş alan (media + db)
- Kamera sayısı: başlangıç hedefi 1-8 kamera

