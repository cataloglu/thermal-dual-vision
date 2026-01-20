# 🗺️ Implementation Roadmap - Smart Motion Detector v2

Bu dosya implementation öncelik sırasını ve her aşamada yapılacakları detaylandırır.

---

## 📋 Öncelik Sırası

### ✅ Phase 0: Setup & Documentation (TAMAMLANDI)
- ✅ Tüm dokümantasyon
- ✅ Docker setup
- ✅ Frontend/Backend boilerplate
- ✅ Test infrastructure

---

## 🚀 Implementation Phases

### 🔧 Phase 1: Settings Service (Öncelik: 🔴 Kritik)
**Hedef**: Config dosyası yönetimi - tüm diğer servisler buna bağımlı

**Yapılacaklar**:
- [ ] `app/services/settings.py` oluştur
  - [ ] `config.json` okuma/yazma
  - [ ] Default config template
  - [ ] Config validation (Pydantic)
  - [ ] Restart sonrası persistence
- [ ] `GET /api/settings` endpoint implement
- [ ] `PUT /api/settings` endpoint implement
- [ ] Unit tests (`tests/test_settings.py`)

**Bağımlılıklar**: Yok  
**Tahmini Süre**: 1-2 gün  
**Dosyalar**:
- `app/services/settings.py`
- `app/models/config.py` (Pydantic models)
- `tests/test_settings.py`

---

### 📹 Phase 2: Camera Service (Öncelik: 🔴 Kritik)
**Hedef**: RTSP bağlantı + test endpoint - UI'da kamera eklemek için gerekli

**Yapılacaklar**:
- [ ] `app/services/camera.py` oluştur
  - [ ] RTSP connection (OpenCV)
  - [ ] Snapshot alma
  - [ ] Connection retry logic
  - [ ] Latency ölçümü
- [ ] `POST /api/cameras/test` endpoint implement
- [ ] `GET /api/cameras` endpoint implement
- [ ] `POST /api/cameras` endpoint implement (CRUD)
- [ ] `PUT /api/cameras/{id}` endpoint implement
- [ ] `DELETE /api/cameras/{id}` endpoint implement
- [ ] Integration tests (`tests/test_camera.py`)

**Bağımlılıklar**: Settings Service  
**Tahmini Süre**: 2-3 gün  
**Dosyalar**:
- `app/services/camera.py`
- `app/models/camera.py` (Pydantic models)
- `tests/test_camera.py`

---

### 🗄️ Phase 3: Database Models (Öncelik: 🟡 Yüksek)
**Hedef**: Event ve Camera kayıtları için SQLite database

**Yapılacaklar**:
- [ ] `app/db/models.py` oluştur
  - [ ] Camera model (SQLAlchemy)
  - [ ] Event model (SQLAlchemy)
  - [ ] Zone model (SQLAlchemy)
  - [ ] Database init/migration
- [ ] `app/db/session.py` - DB connection
- [ ] `app/services/events.py` oluştur
  - [ ] Event CRUD operations
  - [ ] Pagination
  - [ ] Filtering (camera, date, confidence)
- [ ] `GET /api/events` endpoint implement
- [ ] `GET /api/events/{id}` endpoint implement
- [ ] `DELETE /api/events/{id}` endpoint implement
- [ ] Unit tests (`tests/test_events.py`)

**Bağımlılıklar**: Settings Service, Camera Service  
**Tahmini Süre**: 2-3 gün  
**Dosyalar**:
- `app/db/models.py`
- `app/db/session.py`
- `app/services/events.py`
- `tests/test_events.py`

---

### 🎨 Phase 4: Frontend - Settings Page (Öncelik: 🟡 Yüksek)
**Hedef**: Kamera ekleme/düzenleme UI - kullanıcı kamera ekleyebilmeli

**Yapılacaklar**:
- [ ] `ui/src/pages/Settings.tsx` oluştur
- [ ] `ui/src/components/CameraForm.tsx` - Kamera ekleme formu
  - [ ] Camera type select (color/thermal/dual)
  - [ ] RTSP URL input
  - [ ] Test button + snapshot preview
  - [ ] Save/Cancel buttons
- [ ] `ui/src/components/CameraList.tsx` - Kamera listesi
- [ ] `ui/src/services/api.ts` - API client
- [ ] Settings tabs: Cameras, Detection, Zones, AI, Telegram
- [ ] Form validation + error handling
- [ ] Toast notifications

**Bağımlılıklar**: Camera Service (backend)  
**Tahmini Süre**: 3-4 gün  
**Dosyalar**:
- `ui/src/pages/Settings.tsx`
- `ui/src/components/CameraForm.tsx`
- `ui/src/components/CameraList.tsx`
- `ui/src/services/api.ts`
- `ui/src/types/api.ts`

---

### 🤖 Phase 5: Detection Pipeline (Öncelik: 🟠 Orta)
**Hedef**: YOLOv8 person detection + event trigger

**Yapılacaklar**:
- [ ] `app/workers/detector.py` oluştur
  - [ ] YOLOv8 model loader (auto-download)
  - [ ] Frame ingestion (RTSP stream)
  - [ ] Person detection inference
  - [ ] Confidence filtering
  - [ ] Zone/ROI filtering
  - [ ] Event trigger logic
  - [ ] Cooldown mechanism
- [ ] `app/workers/motion.py` - Motion detection (opsiyonel)
- [ ] Model dosyaları yönetimi (`app/models/`)
- [ ] Worker lifecycle (start/stop/restart)
- [ ] Integration tests (mock RTSP stream)

**Bağımlılıklar**: Database Models, Camera Service  
**Tahmini Süre**: 4-5 gün  
**Dosyalar**:
- `app/workers/detector.py`
- `app/workers/motion.py`
- `app/services/inference.py`
- `tests/test_detector.py`

---

### 📹 Phase 6: Media Generation (Öncelik: 🟠 Orta)
**Hedef**: Collage, GIF, MP4 oluşturma

**Yapılacaklar**:
- [ ] `app/workers/media.py` oluştur
  - [ ] Collage generation (5 frames)
  - [ ] GIF generation (preview)
  - [ ] MP4 timelapse (20s accelerated)
  - [ ] FFmpeg integration
- [ ] Media file storage (`data/media/`)
- [ ] Media URL generation
- [ ] `GET /api/events/{id}/collage` endpoint
- [ ] `GET /api/events/{id}/preview.gif` endpoint
- [ ] `GET /api/events/{id}/timelapse.mp4` endpoint

**Bağımlılıklar**: Detection Pipeline  
**Tahmini Süre**: 3-4 gün  
**Dosyalar**:
- `app/workers/media.py`
- `app/services/media.py`
- `tests/test_media.py`

---

### ✅ Phase 7: Retention Worker (TAMAMLANDI)
**Hedef**: Disk temizleme + retention policy

**Yapılacaklar**:
- [x] `app/workers/retention.py` oluştur
  - [x] Retention policy (days)
  - [x] Disk limit check (%)
  - [x] Cleanup strategy (oldest first)
  - [x] Delete order (mp4 → gif → collage)
  - [x] Scheduled cleanup (cron-like)
- [x] Database cleanup (orphan records)
- [x] Disk space monitoring

**Bağımlılıklar**: Media Generation  
**Tahmini Süre**: 2-3 gün  
**Dosyalar**:
- `app/workers/retention.py`
- `tests/test_retention.py`

---

### ✅ Phase 8: Frontend - Dashboard & Live (TAMAMLANDI)
**Hedef**: Ana sayfa + canlı görüntü

**Yapılacaklar**:
- [x] `ui/src/pages/Dashboard.tsx`
  - [x] System health card
  - [x] Cameras summary card
  - [x] AI status card
  - [x] Last event card
- [x] `ui/src/pages/Live.tsx`
  - [x] Camera grid (1x1, 2x2, 3x3)
  - [x] MJPEG stream viewer
  - [x] Stream reconnect logic
  - [x] Camera status indicators
- [x] `ui/src/components/StreamViewer.tsx`
- [x] `ui/src/components/Sidebar.tsx`
- [x] `ui/src/components/Layout.tsx`
- [x] `ui/src/pages/Events.tsx`
- [x] `ui/src/pages/Diagnostics.tsx`
- [x] React Router integration
- [x] Full navigation system

**Bağımlılıklar**: Detection Pipeline, Media Generation  
**Tahmini Süre**: 3-4 gün  
**Dosyalar**:
- `ui/src/pages/Dashboard.tsx`
- `ui/src/pages/Live.tsx`
- `ui/src/pages/Events.tsx`
- `ui/src/pages/Diagnostics.tsx`
- `ui/src/components/StreamViewer.tsx`
- `ui/src/components/Sidebar.tsx`
- `ui/src/components/Layout.tsx`
- `ui/src/App.tsx`
- `ui/src/services/api.ts`

---

### 📋 Phase 9: Frontend - Events Page (Öncelik: 🟡 Yüksek)
**Hedef**: Event listesi + detay görünümü

**Yapılacaklar**:
- [ ] `ui/src/pages/Events.tsx`
  - [ ] Event list (pagination)
  - [ ] Filters (camera, date, confidence)
  - [ ] Event cards (collage thumbnail)
  - [ ] Sort (newest first)
- [ ] `ui/src/components/EventCard.tsx`
- [ ] `ui/src/components/EventDetail.tsx` (modal veya ayrı sayfa)
  - [ ] Collage preview
  - [ ] GIF preview
  - [ ] MP4 player
  - [ ] AI summary
  - [ ] Download buttons
- [ ] Infinite scroll veya pagination

**Bağımlılıklar**: Media Generation  
**Tahmini Süre**: 3-4 gün  
**Dosyalar**:
- `ui/src/pages/Events.tsx`
- `ui/src/components/EventCard.tsx`
- `ui/src/components/EventDetail.tsx`

---

### 🔌 Phase 10: WebSocket Server (Öncelik: 🟠 Orta)
**Hedef**: Real-time event push + system status

**Yapılacaklar**:
- [ ] `app/services/websocket.py` oluştur
  - [ ] WebSocket endpoint (`/api/ws/events`)
  - [ ] Event broadcast
  - [ ] System status broadcast
  - [ ] Connection management
- [ ] Frontend WebSocket client
- [ ] Real-time event notifications (UI)
- [ ] Real-time camera status updates

**Bağımlılıklar**: Detection Pipeline  
**Tahmini Süre**: 2-3 gün  
**Dosyalar**:
- `app/services/websocket.py`
- `ui/src/hooks/useWebSocket.ts`

---

### 🤖 Phase 11: AI Integration (Öncelik: 🟢 Düşük - Opsiyonel)
**Hedef**: OpenAI event summary

**Yapılacaklar**:
- [ ] `app/services/ai.py` oluştur
  - [ ] OpenAI API client
  - [ ] Event frame analysis
  - [ ] Summary generation
  - [ ] Error handling (key yok, quota, timeout)
- [ ] AI status check (`/api/health`)
- [ ] AI toggle (settings)
- [ ] Graceful degradation (AI yok = sistem çalışır)

**Bağımlılıklar**: Media Generation  
**Tahmini Süre**: 2-3 gün  
**Dosyalar**:
- `app/services/ai.py`
- `tests/test_ai.py`

---

### 📱 Phase 12: Telegram Integration (Öncelik: 🟢 Düşük - Opsiyonel)
**Hedef**: Event notifications via Telegram

**Yapılacaklar**:
- [ ] `app/services/telegram.py` oluştur
  - [ ] Telegram bot client
  - [ ] Send message + photo + video
  - [ ] Rate limiting
  - [ ] Cooldown mechanism
  - [ ] Test endpoint (`POST /api/telegram/test`)
- [ ] Event notification trigger
- [ ] Settings UI (bot token, chat IDs)

**Bağımlılıklar**: Media Generation  
**Tahmini Süre**: 2-3 gün  
**Dosyalar**:
- `app/services/telegram.py`
- `tests/test_telegram.py`

---

### 🔍 Phase 13: Diagnostics Page (Öncelik: 🟢 Düşük)
**Hedef**: System diagnostics + logs

**Yapılacaklar**:
- [ ] `GET /api/logs` endpoint implement
- [ ] `ui/src/pages/Diagnostics.tsx`
  - [ ] Health JSON viewer
  - [ ] Logs tail (last 200 lines)
  - [ ] Copy button
  - [ ] Retry/backoff status
  - [ ] Camera errors

**Bağımlılıklar**: Yok  
**Tahmini Süre**: 1-2 gün  
**Dosyalar**:
- `ui/src/pages/Diagnostics.tsx`
- `app/services/logs.py`

---

## 📊 Tahmini Toplam Süre

| Phase | Süre | Öncelik |
|-------|------|---------|
| Phase 1: Settings | 1-2 gün | 🔴 Kritik |
| Phase 2: Camera | 2-3 gün | 🔴 Kritik |
| Phase 3: Database | 2-3 gün | 🟡 Yüksek |
| Phase 4: Frontend Settings | 3-4 gün | 🟡 Yüksek |
| Phase 5: Detection | 4-5 gün | 🟠 Orta |
| Phase 6: Media | 3-4 gün | 🟠 Orta |
| Phase 7: Retention | 2-3 gün | 🟢 Düşük |
| Phase 8: Frontend Dashboard/Live | 3-4 gün | 🟡 Yüksek |
| Phase 9: Frontend Events | 3-4 gün | 🟡 Yüksek |
| Phase 10: WebSocket | 2-3 gün | 🟠 Orta |
| Phase 11: AI | 2-3 gün | 🟢 Düşük |
| Phase 12: Telegram | 2-3 gün | 🟢 Düşük |
| Phase 13: Diagnostics | 1-2 gün | 🟢 Düşük |

**Toplam**: ~30-40 gün (1-2 ay, tek kişi)

---

## 🎯 MVP Minimum (Hızlı Prototip)

Eğer hızlı bir prototip istiyorsanız, sadece şunları implement edin:

1. ✅ Phase 1: Settings Service
2. ✅ Phase 2: Camera Service
3. ✅ Phase 3: Database Models
4. ✅ Phase 4: Frontend Settings
5. ✅ Phase 5: Detection Pipeline (basit versiyon)
6. ✅ Phase 8: Frontend Dashboard/Live (basit versiyon)

**Tahmini Süre**: ~2 hafta

---

## 📝 Notlar

- Her phase bağımsız branch'te çalışılabilir
- Test coverage minimum %70 hedeflenmeli
- Her phase için PR + code review
- Dokümantasyon her phase'de güncellenmeli

---

## 🤝 Katkı Yapmak İster misiniz?

1. Bir phase seçin
2. Issue açın: "Implement Phase X: [Phase Name]"
3. Branch oluşturun: `feature/phase-X-[name]`
4. PR gönderin!

Detaylar için: [`CONTRIBUTING.md`](CONTRIBUTING.md)
