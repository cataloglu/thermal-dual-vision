# DEVELOPMENT — Smart Motion Detector (v2)

## 1) Gereksinimler
- Python 3.11
- Node.js 20+
- FFmpeg

---

## 2) Backend Kurulum
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Çalıştırma:
```bash
python -m app.main
```

Ortam değişkenleri için: `docs/ENVIRONMENT.md`

---

## 3) Frontend Kurulum
```bash
cd ui
npm install
npm run dev
```

---

## 4) Test
```bash
pytest
```

---

## 5) Smoke Test (UI)
1) Backend
```bash
python -m app.main
```

2) Frontend
```bash
cd ui
npm run dev
```

3) Kontrol listesi
- Dashboard: sistem durumu kartları yükleniyor, son event görünür.
- Events: liste açılıyor, filtreler çalışıyor, pagination geçişi var.
- Live: en az bir kamera stream görüntüsü geliyor, retry/snapshot/fullscreen çalışıyor.
- Settings: tab geçişleri sorunsuz, kaydetme toast görünüyor.
- Diagnostics: health/logs yükleniyor, log filtre + indirme çalışıyor.

---

## 6) Testing Strategy
- Unit: config validation, event pipeline, settings
- Integration: camera test endpoint, event creation
- UI smoke: dashboard/events/settings basic render
- Mock RTSP stream ile test edilir

