# Development Guide

## Requirements

| Tool | Version |
|---|---|
| Python | 3.11 |
| Node.js | 20+ |
| FFmpeg | any recent |
| go2rtc | bundled in Docker; install separately for local dev |

---

## Backend Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

Run:
```bash
python -m uvicorn app.main:app --reload --port 8000
# or simply:
python -m app.main
```

API available at `http://localhost:8000`  
Swagger docs at `http://localhost:8000/docs`

Environment variables: see `docs/ENVIRONMENT.md`

---

## Frontend Setup

```bash
cd ui
npm install
npm run dev
```

UI at `http://localhost:5173` — proxies `/api` to `localhost:8000` automatically.

Build for production:
```bash
npm run build   # outputs to ui/dist/
npm run lint    # ESLint check (0 warnings policy)
```

---

## Running Tests

```bash
# All tests
python -m pytest

# Specific file
python -m pytest tests/test_settings.py -v

# Fast smoke (health + settings)
python -m pytest tests/test_health.py tests/test_settings.py -v
```

Test config: `pytest.ini` (root)

---

## Smoke Test Checklist (manual)

Start backend + frontend, then verify:

| Page | Check |
|---|---|
| Dashboard | Health cards load, last event visible |
| Events | List loads, filters work, pagination works |
| Live | Camera stream appears (snapshot fallback if no go2rtc) |
| Settings → Cameras | Add/test/save camera works |
| Settings → Detection | Change value → Save → toast appears |
| Settings → Zones | Draw polygon → Save |
| Settings → AI | API key field masked, test button works |
| Settings → Telegram | Test message sends |
| Settings → MQTT | Status panel shows connected/disconnected |
| Diagnostics | Health + logs load, log filter works |
| Video Analysis | Event list loads, analyze button works |

---

## Project Structure

```
thermal-dual-vision/
├── app/                    # FastAPI backend
│   ├── main.py             # All API routes
│   ├── db/                 # SQLAlchemy models + session + migrations
│   ├── models/             # Pydantic config models
│   ├── services/           # Business logic (ai, mqtt, telegram, go2rtc...)
│   └── workers/            # Background workers (detector, media, retention)
├── ui/                     # React + TypeScript frontend
│   └── src/
│       ├── pages/          # Full-page components
│       ├── components/     # Shared components + tab components
│       ├── hooks/          # Custom React hooks
│       ├── services/       # API client
│       └── i18n/           # en.json + tr.json translations
├── tests/                  # pytest test suite
├── docs/                   # Documentation
├── config.yaml             # HA addon manifest + version (single source of truth)
├── env.example             # Environment variable template
└── pytest.ini              # Test configuration
```

---

## Adding a New Setting

1. Add field to the right config class in `app/models/config.py`
2. If it's a DB column: add migration in `app/db/session.py` (`_migrate_add_*`)
3. Add UI input in the relevant `ui/src/components/tabs/` file
4. Add i18n keys to `ui/src/i18n/en.json` and `ui/src/i18n/tr.json`
5. Run `npm run build` + `python -m pytest` to verify
