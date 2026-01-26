# Smart Motion Detector (v2)

Thermal ve color kamera desteği ile **sadece insan algılama** odaklı akıllı hareket algılama sistemi.

## ✨ Özellikler

- 🎯 **Sadece İnsan Algılama**: YOLOv8 person detection (`yolov8n-person` / `yolov8s-person` model seçimi)
- 🌡️ **Dual Kamera Desteği**: Color, Thermal veya Dual kamera
- 🎨 **Modern Dark UI**: Frigate-inspired dashboard
- 📹 **Event Kanıtları**: Her algılamada collage (5 frame) + MP4 timelapse
- 🤖 **Opsiyonel AI**: OpenAI entegrasyonu (key yoksa sistem çalışır)
- 📱 **Telegram Bildirimleri**: Event'lerde otomatik bildirim
- 🔄 **Akıllı Retention**: Disk limiti + retention policy ile otomatik temizleme
- 🎭 **Zone/ROI Desteği**: Kamera bazında polygon alanlar (motion/person filtreleme)

## 🚀 Quick Start

### Docker Compose (Önerilen)

```bash
# .env dosyası oluştur
cp env.example .env
# .env dosyasını düzenle (OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, vb.)

# Başlat
docker-compose up -d

# UI: http://localhost:5173
# API: http://localhost:8000
```

### Manuel Kurulum

```bash
# Backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.main

# Frontend (ayrı terminal)
cd ui
npm install
npm run dev
```

## 📚 Dokümantasyon

- 📖 **Ürün Tanımı**: [`docs/PRODUCT.md`](docs/PRODUCT.md)
- 🔌 **API Sözleşmesi**: [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md)
- 🎨 **Tasarım Sistemi**: [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md)
- 🏗️ **Mimari**: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- 🛠️ **Geliştirme**: [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)
- 🔒 **Güvenlik**: [`docs/SECURITY.md`](docs/SECURITY.md)
- ⚙️ **Ortam Değişkenleri**: [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)
- 💅 **Code Style**: [`docs/CODE_STYLE.md`](docs/CODE_STYLE.md)
- 📖 **Config Reference**: [`docs/CONFIG_REFERENCE.md`](docs/CONFIG_REFERENCE.md) 📋
- ⚡ **Performance Tuning**: [`docs/PERFORMANCE_TUNING.md`](docs/PERFORMANCE_TUNING.md) 🔥
- 🎬 **Media Specification**: [`docs/MEDIA_SPEC.md`](docs/MEDIA_SPEC.md) 📹
- 🚀 **Advanced Features**: [`docs/ADVANCED_FEATURES.md`](docs/ADVANCED_FEATURES.md) 🏆
- 🤖 **YOLO Model Comparison**: [`docs/YOLO_COMPARISON.md`](docs/YOLO_COMPARISON.md) 🔥
- 🧪 **E2E Tests (Playwright)**: [`docs/E2E_TESTS.md`](docs/E2E_TESTS.md)
- 🗺️ **Implementation Roadmap**: [`ROADMAP.md`](ROADMAP.md) ⭐

## 🎯 MVP Scope

### In Scope
- ✅ Multi-camera support (color/thermal/dual)
- ✅ Person detection only (`yolov8n-person` / `yolov8s-person`)
- ✅ Event-based recording (collage/mp4) - "Review" özelliği Events sayfasında
- ✅ Live view (MJPEG/WebRTC)
- ✅ Zone/ROI configuration (polygon-based)
- ✅ AI summary (optional - OpenAI)
- ✅ Telegram notifications
- ✅ Retention policy + disk cleanup

### Out of Scope
- ❌ Generic object detection (sadece person)
- ❌ Face recognition
- ❌ Continuous recording (sadece event-based)

## 🧪 Test

```bash
pytest
```

## 📦 Tech Stack

- **Backend**: Python 3.11 + FastAPI + OpenCV + YOLOv8/YOLOv9
- **Frontend**: React + TypeScript + Vite + Tailwind
- **Storage**: SQLite + JSON config + filesystem media
- **Realtime**: WebSocket + MJPEG/WebRTC streams
- **AI Models**: YOLOv8n/s (person-specific) + YOLOv9t/s (thermal-optimized)

## 🤖 Supported YOLO Models

| Model | Speed | Accuracy | Use Case | Thermal |
|-------|-------|----------|----------|---------|
| **YOLOv8n-person** | ⚡⚡⚡ Fast | ⭐⭐⭐ Good | 5+ cameras | ✅ Good |
| **YOLOv8s-person** | ⚡⚡ Medium | ⭐⭐⭐⭐ High | 1-4 cameras | ✅ Good |
| **YOLOv9t** | ⚡⚡ Medium | ⭐⭐⭐⭐ High | Thermal optimized | ✅✅ Best |
| **YOLOv9s** | ⚡ Slower | ⭐⭐⭐⭐⭐ Best | 1-3 cameras, max accuracy | ✅✅ Best |

**Recommendation**: Start with YOLOv8n-person, upgrade to YOLOv9t if false positives are high.

**Why YOLOv9 for thermal?** PGI (Programmable Gradient Information) prevents information loss in low-contrast thermal images, resulting in +0.6% mAP and -49% parameters.

See [`docs/YOLO_COMPARISON.md`](docs/YOLO_COMPARISON.md) for detailed comparison.

## 🤝 Contributing

Bu proje MVP aşamasındadır. Katkılar için lütfen önce issue açın.

## 📄 License

MIT
