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

- **Backend tests**: `source .venv/bin/activate && python -m pytest tests/ -v` (266 tests, all unit/integration, no external services required)
- **Frontend lint**: `cd ui && npm run lint` (zero-warning policy)
- **Frontend build**: `cd ui && npm run build` (runs `tsc` then `vite build`)
- Config: `pytest.ini` at repo root
- **UI testing policy (default)**:
  - UI değişikliklerinde manuel fonksiyonel test yap (ekran akışını gerçekten çalıştır).
  - Kullanıcı özellikle istemedikçe demo video/screenshot üretme.
  - Sonuçları kısa metin + çalıştırılan komut çıktılarıyla raporla.

### Gotchas

- Python **3.11** is required (installed via `deadsnakes` PPA); the venv is at `.venv` and uses `python3.11`.
- The backend process may appear to exit immediately if run via a non-backgrounded shell in certain sandbox environments — always verify with `curl http://localhost:8000/api/health`.
- Node 20+ is required for the frontend; the repo uses `npm` (not pnpm/yarn), matching `package-lock.json` is absent so `npm install` generates a fresh lockfile.
- `requirements.txt` pulls PyTorch + CUDA/NVIDIA wheels (~3 GB); this is expected and needed for Ultralytics YOLO inference.

### Home Assistant update visibility checklist (release hygiene)

When changes are intended to reach Home Assistant users as an addon update:

0. Never announce "update hazır/geldi" until `master` merge is completed and verified.
0.1 If `config.yaml` version is bumped, `master` merge is mandatory in the same flow (otherwise HA won't show update).
1. Ensure the PR is **merged to `master`** (not draft/open).
2. Ensure addon manifest version is bumped in `config.yaml` when needed.
3. Verify `origin/master:config.yaml` has the expected version after merge.
4. If user says "update görünmüyor", explicitly remind:
   - Add-on Store → 3 dots → **Reload**
   - **Check for updates**
5. In final report, always state merge state + effective `master` version to avoid ambiguity.

#### Required release verification commands

- `git fetch origin master && git show origin/master:config.yaml | rg "version:"`
- `curl -sL https://raw.githubusercontent.com/cataloglu/thermal-dual-vision/master/config.yaml | rg "version:"`

#### If PR creation is blocked by token scope

If `gh pr create` fails with `Resource not accessible by integration`, try direct merge API:

- `gh api -X POST repos/cataloglu/thermal-dual-vision/merges -f base='master' -f head='cursor/termal-kamera-alg-lama-ayarlar-4dc2' -f commit_message='Merge release fixes into master'`

Then re-run required release verification commands above.

#### Stubborn HA store cache (still no update visible)

Tell user to do all steps in order:

1. Add-on Store → 3 dots → **Repositories**
2. Remove `https://github.com/cataloglu/thermal-dual-vision`
3. Add the same repository URL again
4. 3 dots → **Reload**
5. **Check for updates**
6. Browser hard refresh (`Ctrl+F5`)
7. If still missing: restart Home Assistant once
