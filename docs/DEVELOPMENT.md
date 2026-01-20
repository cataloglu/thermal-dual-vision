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

## 5) Testing Strategy
- Unit: config validation, event pipeline, settings
- Integration: camera test endpoint, event creation
- UI smoke: dashboard/events/settings basic render
- Mock RTSP stream ile test edilir

