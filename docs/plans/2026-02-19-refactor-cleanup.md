# Refactor & Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Temizlik ve refactor — main.py god file'ı router'lara bölmek, tekrarlayan kodu tek yere çekmek, kırılgan AI string'lerini sabitlemek ve küçük temizlikler yapmak.

**Architecture:** Tüm FastAPI route handler'ları `app/routers/` altında mantıksal gruplara bölünür. Servis singleton'ları `app/dependencies.py`'de tanımlanır; hem `main.py` hem router dosyaları buradan import eder. Böylece circular import olmadan her router bağımsız çalışır.

**Tech Stack:** Python 3.11, FastAPI (APIRouter), SQLAlchemy, Pydantic, pytest

---

## Kapsam Dışı (Bu Planda Yok)

- `detector.py` iç parçalama (yüksek risk, ayrı plan)
- `asyncio.run()` thread fix (ayrı plan)
- Yeni feature ekleme

---

## Task 1: Hızlı Temizlikler (Sıfır Risk)

**Files:**
- Rename: `app/services/ai_test.py` → `app/services/ai_probe.py`
- Modify: `app/main.py:4,16,38`

### Step 1: ai_test.py → ai_probe.py olarak yeniden adlandır

```bash
git mv app/services/ai_test.py app/services/ai_probe.py
```

### Step 2: main.py içindeki import'u güncelle

`app/main.py` satır 38:
```python
# ESKİ:
from app.services.ai_test import test_openai_connection
# YENİ:
from app.services.ai_probe import test_openai_connection
```

### Step 3: Duplicate import'ları temizle

`app/main.py` başı — iki sorun:

**Sorun 1** (satır 4 ve ilerisi — `asyncio` iki kez):
Dosyada `import asyncio`'nun tek bir kez geçtiğinden emin ol. Lifespan içindeki ikinci import'u kaldır.

**Sorun 2** (satır 14 ve 16 — `Response` iki kez):
```python
# SATIR 14 (fastapi'den):
from fastapi import FastAPI, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect, Response, Request
# SATIR 16 (fastapi.responses'dan — BU Response satır 14'ü eziyor):
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
```
Satır 16'dan `Response`'u kaldır, sadece `FileResponse, JSONResponse, StreamingResponse` kalsın.

### Step 4: Test — import'ların çalıştığını doğrula

```bash
cd C:\Users\Administrator\.claude-worktrees\thermal-dual-vision\naughty-blackburn
python -c "from app.main import app; print('OK')"
```
Beklenen: `OK` (hata yok)

### Step 5: Commit

```bash
git add app/services/ai_probe.py app/main.py
git commit -m "refactor: rename ai_test to ai_probe, fix duplicate imports"
```

---

## Task 2: AI Confirmation String'lerini Sabitlerle Değiştir

**Sorun:** `detector.py:1448` ve `detector_mp.py:38` — `_is_ai_confirmed()` fonksiyonu AI cevabını `"insan tespit edilmedi"` gibi hardcoded string'lerle kontrol ediyor. Prompt veya model değişse sessizce bozulur.

**Files:**
- Create: `app/services/ai_constants.py`
- Modify: `app/workers/detector.py:1452-1466`
- Modify: `app/workers/detector_mp.py:42-56`
- Modify: `app/services/ai.py:40,42,69,71` (prompt kaynağını aynı yere bağla)

### Step 1: `app/services/ai_constants.py` oluştur

```python
"""
AI response parsing constants.

These strings MUST match the prompts in app/services/ai.py.
If you change the AI prompt, update these lists too.
"""

AI_NEGATIVE_MARKERS = [
    "insan tespit edilmedi",
    "no human",
    "muhtemel yanlış alarm",
    "muhtemel yanlis alarm",
    "false alarm",
]

AI_POSITIVE_MARKERS = [
    "kişi tespit edildi",
    "kisi tespit edildi",
    "insan tespit edildi",
    "person detected",
]
```

### Step 2: Test yaz

`tests/test_ai_constants.py`:
```python
from app.services.ai_constants import AI_NEGATIVE_MARKERS, AI_POSITIVE_MARKERS

def test_negative_markers_not_empty():
    assert len(AI_NEGATIVE_MARKERS) > 0

def test_positive_markers_not_empty():
    assert len(AI_POSITIVE_MARKERS) > 0

def test_no_overlap():
    overlap = set(AI_NEGATIVE_MARKERS) & set(AI_POSITIVE_MARKERS)
    assert overlap == set(), f"Marker conflict: {overlap}"
```

### Step 3: Test'i çalıştır (fail etmeli — dosya yok henüz)

```bash
pytest tests/test_ai_constants.py -v
```
Beklenen: ImportError veya fail

### Step 4: `ai_constants.py`'yi oluştur (Step 1'deki kodu yaz)

### Step 5: Test'i çalıştır (pass etmeli)

```bash
pytest tests/test_ai_constants.py -v
```
Beklenen: 3 test PASS

### Step 6: `detector.py` içinde sabitleri kullan

`app/workers/detector.py` başına import ekle:
```python
from app.services.ai_constants import AI_NEGATIVE_MARKERS, AI_POSITIVE_MARKERS
```

`_is_ai_confirmed` metodunu (satır 1448-1467) güncelle:
```python
def _is_ai_confirmed(self, summary: Optional[str]) -> bool:
    if not summary:
        return False
    text = summary.lower()
    if any(marker in text for marker in AI_NEGATIVE_MARKERS):
        return False
    return any(marker in text for marker in AI_POSITIVE_MARKERS)
```

### Step 7: `detector_mp.py` içinde sabitleri kullan

`app/workers/detector_mp.py` başına import ekle:
```python
from app.services.ai_constants import AI_NEGATIVE_MARKERS, AI_POSITIVE_MARKERS
```

`_is_ai_confirmed` fonksiyonunu (satır 38-57) güncelle:
```python
def _is_ai_confirmed(summary: Optional[str]) -> bool:
    if not summary:
        return False
    text = (summary or "").lower()
    if any(marker in text for marker in AI_NEGATIVE_MARKERS):
        return False
    return any(marker in text for marker in AI_POSITIVE_MARKERS)
```

### Step 8: Smoke test — import çalışıyor mu?

```bash
python -c "from app.workers.detector import DetectorWorker; print('OK')"
python -c "from app.workers.detector_mp import get_mp_detector_worker; print('OK')"
```
Beklenen: Her ikisi `OK`

### Step 9: Mevcut testleri çalıştır

```bash
pytest tests/ -v -x --ignore=tests/stress_test.py --ignore=tests/benchmark_performance.py -k "not live and not stream"
```
Beklenen: Tüm testler PASS (hiçbir şey bozulmadı)

### Step 10: Commit

```bash
git add app/services/ai_constants.py app/workers/detector.py app/workers/detector_mp.py tests/test_ai_constants.py
git commit -m "refactor: centralize AI confirmation markers to ai_constants.py"
```

---

## Task 3: `_get_go2rtc_restream_url` Tekrarını Kaldır

**Sorun:** Aynı fonksiyon `main.py:285` ve `detector.py:1313`'te ayrı ayrı yaşıyor. `go2rtc_service`'e taşınmalı.

**Files:**
- Modify: `app/services/go2rtc.py` (metod ekle)
- Modify: `app/main.py:285-291` (lokal fonksiyonu kaldır, servisi kullan)
- Modify: `app/workers/detector.py:1313` (lokal metodu kaldır, servisi kullan)

### Step 1: `go2rtc.py`'deki `Go2RTCService` sınıfına metod ekle

`app/services/go2rtc.py` içinde `Go2RTCService` sınıfına:
```python
def get_restream_url(self, camera_id: str, source: Optional[str] = None) -> Optional[str]:
    """Return go2rtc RTSP restream URL for a camera, or None if go2rtc disabled."""
    if not self.ensure_enabled():
        return None
    import os
    rtsp_base = os.getenv("GO2RTC_RTSP_URL", "rtsp://127.0.0.1:8554")
    normalized_source = source if source in ("color", "thermal") else None
    stream_name = f"{camera_id}_{normalized_source}" if normalized_source else camera_id
    return f"{rtsp_base}/{stream_name}"
```

### Step 2: Test yaz

`tests/test_go2rtc_service.py` (eğer yoksa oluştur, varsa ekle):
```python
def test_get_restream_url_with_source(mock_go2rtc_service):
    url = mock_go2rtc_service.get_restream_url("cam1", source="thermal")
    assert url == "rtsp://127.0.0.1:8554/cam1_thermal"

def test_get_restream_url_without_source(mock_go2rtc_service):
    url = mock_go2rtc_service.get_restream_url("cam1")
    assert url == "rtsp://127.0.0.1:8554/cam1"

def test_get_restream_url_invalid_source(mock_go2rtc_service):
    url = mock_go2rtc_service.get_restream_url("cam1", source="invalid")
    assert url == "rtsp://127.0.0.1:8554/cam1"
```

> Not: `mock_go2rtc_service` fixture'ı `ensure_enabled()` → `True` döndürecek şekilde mock'la.

### Step 3: Test çalıştır ve pass et

```bash
pytest tests/test_go2rtc_service.py -v
```

### Step 4: `main.py:285-291` — lokal fonksiyonu kaldır, servisi kullan

`main.py`'de `_get_go2rtc_restream_url` fonksiyonunu tamamen kaldır.

Bunu çağıran yerleri (`main.py:289, 296, 302`) güncelle:
```python
# ESKİ:
_get_go2rtc_restream_url(camera.id, source=...)
# YENİ:
go2rtc_service.get_restream_url(camera.id, source=...)
```

### Step 5: `detector.py:1313` — lokal metodu kaldır

`DetectorWorker._get_go2rtc_restream_url` metodunu kaldır.

Bunu çağıran yerleri `go2rtc_service.get_restream_url(...)` ile değiştir.

> `detector.py` içinde `go2rtc_service` erişimi zaten `self._go2rtc_service` üzerinden var — bunu kullan.

### Step 6: Smoke test

```bash
python -c "from app.main import app; print('OK')"
python -c "from app.workers.detector import DetectorWorker; print('OK')"
```

### Step 7: Mevcut testleri çalıştır

```bash
pytest tests/ -v -x --ignore=tests/stress_test.py --ignore=tests/benchmark_performance.py -k "not live and not stream"
```

### Step 8: Commit

```bash
git add app/services/go2rtc.py app/main.py app/workers/detector.py tests/test_go2rtc_service.py
git commit -m "refactor: consolidate _get_go2rtc_restream_url into Go2RTCService"
```

---

## Task 4: `app/dependencies.py` Oluştur

**Amaç:** `main.py`'deki servis singleton'larını merkezi bir yere taşı. Router'lar buradan import eder, circular import olmaz.

**Files:**
- Create: `app/dependencies.py`
- Modify: `app/main.py` (singleton init'leri buraya taşı, import et)

### Step 1: `app/dependencies.py` oluştur

```python
"""
Shared service singletons for dependency injection across routers.
All module-level singleton instances are initialized here.
"""
import threading

from app.db.session import init_db
from app.services.camera import get_camera_service
from app.services.camera_crud import get_camera_crud_service
from app.services.events import get_event_service
from app.services.media import get_media_service
from app.services.settings import get_settings_service
from app.services.websocket import get_websocket_manager
from app.services.telegram import get_telegram_service
from app.services.logs import get_logs_service
from app.services.ai import get_ai_service
from app.services.go2rtc import get_go2rtc_service
from app.services.mqtt import get_mqtt_service
from app.services.recording_state import get_recording_state_service
from app.services.metrics import get_metrics_service
from app.services.recorder import get_continuous_recorder
from app.workers.retention import get_retention_worker
from app.workers.detector import get_detector_worker

init_db()

settings_service = get_settings_service()
camera_service = get_camera_service()
camera_crud_service = get_camera_crud_service()
event_service = get_event_service()
ai_service = get_ai_service()
media_service = get_media_service()
retention_worker = get_retention_worker()
detector_worker = get_detector_worker()
websocket_manager = get_websocket_manager()
telegram_service = get_telegram_service()
logs_service = get_logs_service()
go2rtc_service = get_go2rtc_service()
mqtt_service = get_mqtt_service()
recording_state_service = get_recording_state_service()
metrics_service = get_metrics_service()
continuous_recorder = get_continuous_recorder()

# Max 2 concurrent live MJPEG streams (her stream = full RTSP decode + encode)
live_stream_semaphore = threading.Semaphore(2)
```

### Step 2: `main.py` içinde singleton'ları bu dosyadan import et

`main.py`'de satır 241-262 arasındaki tüm singleton init bloğunu kaldır, yerine:
```python
from app.dependencies import (
    settings_service, camera_service, camera_crud_service,
    event_service, ai_service, media_service, retention_worker,
    detector_worker, websocket_manager, telegram_service,
    logs_service, go2rtc_service, mqtt_service,
    recording_state_service, metrics_service, continuous_recorder,
    live_stream_semaphore,
)
```

`_live_stream_semaphore` referanslarını `live_stream_semaphore` olarak güncelle (ya da alias: `_live_stream_semaphore = live_stream_semaphore`).

### Step 3: Smoke test

```bash
python -c "from app.main import app; print('OK')"
```

### Step 4: Commit

```bash
git add app/dependencies.py app/main.py
git commit -m "refactor: extract service singletons to app/dependencies.py"
```

---

## Task 5: Router'ları Oluştur — `app/routers/`

**Amaç:** `main.py`'deki route'ları 6 router dosyasına böl.

**Router grupları:**

| Dosya | Route'lar |
|---|---|
| `app/routers/cameras.py` | `/api/cameras`, zones, recording, snapshot, camera test |
| `app/routers/events.py` | `/api/events` (CRUD + media) |
| `app/routers/live.py` | `/api/live` (MJPEG, JPG snapshot) |
| `app/routers/settings.py` | `/api/settings`, `/api/mqtt/status` |
| `app/routers/system.py` | `/api/logs`, `/api/system/info`, `/api/video/analyze`, `/api/ai/test`, `/api/ai/test-event`, `/api/telegram/test` |
| `app/routers/websocket.py` | `/api/ws/events` |

**Files:**
- Create: `app/routers/__init__.py`
- Create: `app/routers/cameras.py`
- Create: `app/routers/events.py`
- Create: `app/routers/live.py`
- Create: `app/routers/settings.py`
- Create: `app/routers/system.py`
- Create: `app/routers/websocket.py`
- Modify: `app/main.py` (router'ları include et, handler'ları kaldır)

### Step 1: `app/routers/__init__.py` oluştur (boş)

```python
```

### Step 2: Her router dosyasını oluştur

Her dosya şu kalıpla başlar:
```python
import logging
from fastapi import APIRouter, ...
from app.dependencies import settings_service, camera_service, ...

logger = logging.getLogger(__name__)
router = APIRouter()
```

Sonra `main.py`'den ilgili `@app.get/post/...` dekoratörlü handler'ları bu dosyaya taşı — `@app.` → `@router.` olarak değiştirerek.

**Taşıma sırası (riski azaltmak için):**

1. `system.py` — en bağımsız (logs, system/info, video/analyze, ai/test, telegram/test)
2. `settings.py` — settings + mqtt/status
3. `websocket.py` — tek endpoint
4. `events.py` — events CRUD + media
5. `cameras.py` — en büyük grup, en sona bırak
6. `live.py` — streaming logic, ayrı dikkat gerekir

> Her router taşındıktan sonra `main.py`'ye `app.include_router(router, ...)` ekle ve eski handler'ları sil. **Bir seferde bir router.**

### Step 3: `main.py`'ye router'ları kaydet

```python
from app.routers import cameras, events, live, settings_router, system, websocket

app.include_router(cameras.router)
app.include_router(events.router)
app.include_router(live.router)
app.include_router(settings_router.router)
app.include_router(system.router)
app.include_router(websocket.router)
```

### Step 4: Her router taşıması sonrası smoke test

```bash
python -c "from app.main import app; print(len(app.routes), 'routes')"
```
Beklenen: Route sayısı taşımadan önce ve sonra aynı kalır.

### Step 5: Mevcut testleri çalıştır

```bash
pytest tests/ -v -x --ignore=tests/stress_test.py --ignore=tests/benchmark_performance.py -k "not live and not stream"
```
Beklenen: Tüm testler PASS

### Step 6: Her router tamamlandığında commit

```bash
git commit -m "refactor: extract <router_name> routes to app/routers/<file>.py"
```

---

## Task 6: Son Kontrol ve Temizlik

### Step 1: `main.py` satır sayısını doğrula

```bash
(Get-Content app/main.py).Count
```
Beklenen: 400'ün altında (lifespan + app init + router include'lardan ibaret)

### Step 2: Tüm testleri çalıştır

```bash
pytest tests/ -v --ignore=tests/stress_test.py --ignore=tests/benchmark_performance.py -k "not live and not stream"
```
Beklenen: Tüm testler PASS

### Step 3: Import kontrolü

```bash
python -c "from app.main import app; print('Routes:', len(app.routes))"
```

### Step 4: Final commit

```bash
git add -A
git commit -m "refactor: complete main.py split into app/routers/ — cleanup done"
```

---

## Özet

| Task | Risk | Süre |
|---|---|---|
| Task 1: ai_probe.py + import temizlik | Sıfır | 10 dk |
| Task 2: AI constants | Düşük | 30 dk |
| Task 3: go2rtc dedup | Düşük | 30 dk |
| Task 4: dependencies.py | Orta | 20 dk |
| Task 5: Router'lara böl | Orta | 2-3 saat |
| Task 6: Son kontrol | — | 10 dk |
