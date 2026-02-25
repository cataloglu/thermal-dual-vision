# Thermal Dual Vision — Agent Instructions

## Cursor Cloud specific instructions

### Architecture

Single-product Home Assistant add-on: Python 3.11 FastAPI backend + React 18 TypeScript frontend (Vite). go2rtc handles RTSP restreaming. SQLite is the embedded database. See `docs/DEVELOPMENT.md` for full project structure.

### Running services (dev mode)

| Service | Command | Port | Notes |
|---|---|---|---|
| Backend | `source .venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | 8000 | go2rtc warning on startup is expected in dev (no go2rtc running); backend continues with best effort after 15s readiness timeout |
| Frontend | `cd ui && npm run dev` | 5173 | Vite proxies `/api` → `localhost:8000` |

- The backend **does not require** go2rtc to start; it logs warnings about `go2rtc not available` and continues. Camera live view and RTSP features will not work without go2rtc, but all API/CRUD/settings/events features work fine.
- MQTT and Telegram are optional; they stay disabled if not configured.
- `.env` file at repo root is needed (copy from `env.example`).

### Testing

- **Backend tests**: `source .venv/bin/activate && python -m pytest tests/ -v` (178 tests, all unit/integration, no external services required)
- **Frontend lint**: `cd ui && npm run lint` (zero-warning policy)
- **Frontend build**: `cd ui && npm run build` (runs `tsc` then `vite build`)
- Config: `pytest.ini` at repo root

### Gotchas

- Python **3.11** is required (installed via `deadsnakes` PPA); the venv is at `.venv` and uses `python3.11`.
- The backend process may appear to exit immediately if run via a non-backgrounded shell in certain sandbox environments — always verify with `curl http://localhost:8000/api/health`.
- Node 20+ is required for the frontend; the repo uses `npm` (not pnpm/yarn), matching `package-lock.json` is absent so `npm install` generates a fresh lockfile.
- `requirements.txt` pulls PyTorch + CUDA/NVIDIA wheels (~3 GB); this is expected and needed for Ultralytics YOLO inference.
