# Bug Report — Thermal Dual Vision
**Analiz tarihi:** 2026-02-20  
**Versiyon:** 3.10.96  

---

## 🔴 KRİTİK

| # | Dosya | Satır | Sorun | Durum |
|---|---|---|---|---|
| K-1 | `app/db/session.py` | 25 | SQLite foreign key enforcement KAPALI; `ondelete=CASCADE` çalışmıyor; WAL mode yok | ✅ YAPILDI |
| K-2 | `app/services/settings.py` | 256 | `data.copy()` shallow copy → migration'lar diske asla yazılmıyor | ✅ YAPILDI |
| K-3 | `app/workers/detector_mp.py` | 668 | `write_frame()` dead code; child shared memory'ye kilitsiz yazıyor → torn frame | ✅ YAPILDI |
| K-4 | `app/workers/detector_mp.py` | 1580 | Çöken kamera process asla restart edilmiyor | ✅ YAPILDI |

---

## 🟠 YÜKSEK

| # | Dosya | Satır | Sorun | Durum |
|---|---|---|---|---|
| Y-1 | `app/services/recorder.py` | 151 | `kill()` sonrası `wait()` yok → zombie FFmpeg process | ✅ YAPILDI |
| Y-2 | `app/services/recorder.py` | 48 | `self.processes` dict kilitsiz; monitor thread + request thread race | ✅ YAPILDI |
| Y-3 | `app/services/go2rtc.py` | 71 | YAML config dosyasına eş zamanlı yazma → stream kaybı | ✅ YAPILDI |
| Y-4 | `app/services/mqtt.py` | 101 | paho auto-reconnect + manual thread → çift reconnect, duplicate HA discovery | ✅ YAPILDI |
| Y-5 | `app/services/events.py` | 136 | `rejected_only=None` yine de `rejected_by_ai=False` filtreler → tüm eventler görüntülenemiyor | ✅ YAPILDI |
| Y-6 | `app/routers/cameras.py` | 72 | N+1 query: `/api/cameras/status` her kamera için 2 sorgu | ✅ YAPILDI |
| Y-7 | `app/routers/events.py` | 225 | `Accept-Ranges: bytes` ama `Range` isteği handle edilmiyor → video seek çalışmıyor | ✅ YAPILDI |
| Y-8 | `app/main.py` | 210 | `detector_worker` local var finally'de UnboundLocalError riski | ✅ YAPILDI |
| Y-9 | `app/workers/detector_mp.py` | 1094 | `stop()` event handler thread'i join etmiyor → shared memory temizlenmeden thread çalışıyor | ✅ YAPILDI |
| Y-10 | `ui/src/hooks/useWebSocket.ts` | 153 | Inline callback deps → her parent render'da WS disconnect/reconnect | ✅ YAPILDI |

---

## 🟡 ORTA

| # | Dosya | Satır | Sorun | Durum |
|---|---|---|---|---|
| O-1 | `app/services/video_analyzer.py` | 26 | `VideoCapture` try/finally yok → exception'da file handle leak | ✅ YAPILDI |
| O-2 | `app/services/websocket.py` | 44 | `asyncio.Lock` event loop dışında oluşturuluyor | ✅ YAPILDI |
| O-3 | `app/services/ai.py` | 178 | OpenAI API call'larında timeout yok | ✅ YAPILDI |
| O-4 | `app/workers/detector_mp.py` | 1569 | Unbounded thread spawn per event → thread/DB tükenmesi | ✅ YAPILDI |
| O-5 | `app/workers/retention.py` | 144 | Dosya silinip DB commit başarısız → yetim DB satırı | ✅ YAPILDI |
| O-6 | `app/db/session.py` | — | WAL mode (K-1 ile birlikte düzeltildi) | ✅ YAPILDI |
| O-7 | `app/workers/media.py` | 783 | `imageio.mimsave duration=0.5` → imageio v3'te ms → 2000fps GIF | ✅ YAPILDI |
| O-8 | `app/workers/media.py` | 791 | GIF size reduction overwrite atomic değil | ✅ YAPILDI |
| O-9 | `app/services/telegram.py` | 99 | `Bot` nesnesi close edilmiyor → her event'te HTTP session leak | ✅ YAPILDI |
| O-10 | `app/routers/cameras.py` | 387 | `update_zone` polygon koordinatlarını validate etmiyor | ✅ YAPILDI |
| O-11 | `app/routers/cameras.py` | 376 | Zone değişiklikleri çalışan detector process'e yansımıyor | ✅ YAPILDI |
| O-12 | `app/models/config.py` | 512 | MQTT port min/max constraint yok; gaussian_blur_kernel çift sayıya izin veriyor | ✅ YAPILDI |
| O-13 | `ui/src/components/EventDetail.tsx` | 36 | MP4 hazır → polling duruyor ama collage hâlâ yüklenmiyor | ✅ YAPILDI |
| O-14 | `ui/src/pages/Events.tsx` | 63 | Filter değişiminde WS reconnect | ✅ YAPILDI |
| O-15 | `ui/src/hooks/useEvents.ts` | 41 | AbortController yok → stale data race condition | ✅ YAPILDI |
| O-16 | `ui/src/components/StreamViewer.tsx` | 176 | 15sn WebRTC timeout ref'e atılmıyor → unmount'ta memory leak | ✅ YAPILDI |
| O-17 | `ui/src/services/api.ts` | 55 | axios timeout yok → backend takılırsa UI sonsuza bekler | ✅ YAPILDI |
| O-18 | `app/routers/websocket_router.py` | 16 | Server-side keepalive yok → NAT drop'ta ölü bağlantı birikimi | ✅ YAPILDI |
| O-19 | `app/workers/retention.py` | 113 | Stop signal sleep sırasında ignore ediliyor | ✅ YAPILDI |
| O-20 | `app/services/media.py` | 18 | `RECORDING_MP4_DELAY_SEC=58` < 60s segment süresi | ✅ YAPILDI |

---

## 🟢 DÜŞÜK / UX

| # | Dosya | Satır | Sorun | Durum |
|---|---|---|---|---|
| D-1 | `ui/src/components/tabs/MqttTab.tsx` | — | 10 i18n key eksik → ekranda raw key adları | ✅ YAPILDI |
| D-2 | `ui/src/components/tabs/MqttTab.tsx` | — | Yanlış design system: `bg-card`, `text-foreground` (shadcn) → projede yok | ✅ YAPILDI |
| D-3 | `ui/src/pages/Settings.tsx` | 101 | Reset to Defaults → onay dialog yok | ✅ YAPILDI |
| D-4 | `ui/src/components/tabs/TelegramTab.tsx` | 19 | Bot token plaintext açılıyor (default gizli olmalı) | ✅ YAPILDI |
| D-5 | `ui/src/pages/Events.tsx` | 149 | `toast.success('Event silindi')` hardcoded Türkçe | ✅ YAPILDI |
| D-6 | `ui/src/components/EventCard.tsx` | 58 | `toLocaleString('tr-TR')` hardcoded → EN modda Türkçe tarih | ✅ YAPILDI |
| D-7 | `ui/src/pages/Dashboard.tsx` | 144 | Uptime "g/s/d/sn" kısaltmaları hardcoded Türkçe | ✅ YAPILDI |
| D-8 | `ui/src/pages/CameraMonitor.tsx` | 71 | "Snapshot yok", "Renk" hardcoded Türkçe | ✅ YAPILDI |
| D-9 | `ui/src/components/tabs/AITab.tsx` | 221 | API key test başarılı → otomatik settings save | ✅ YAPILDI |
| D-10 | `ui/src/components/tabs/ZonesTab.tsx` | 44 | Kamera değişince eski zone'lar görünüyor | ✅ YAPILDI |
| D-11 | `ui/src/pages/Logs.tsx` | 42 | Auto-scroll kullanıcı scroll'unu override ediyor | ✅ YAPILDI |
| D-12 | `ui/src/components/ZoneEditor.tsx` | — | Snapshot load → canvas mouse olmadan güncellenmiyor | ✅ YAPILDI |
| D-13 | `ui/src/components/ZoneEditor.tsx` | — | `hoveredPoint` -1 set ediliyor (null yerine) | ✅ YAPILDI |
| D-14 | `ui/src/components/EventDetail.tsx` | 110 | localStorage `event_meta` temizlenmiyor → quota riski | ✅ YAPILDI |
| D-15 | `app/db/models.py` | 99 | `datetime.utcnow` deprecated (Python 3.12+) | ✅ YAPILDI |
| D-16 | `app/services/telegram.py` | 225 | Telegram mesaj şablonu hardcoded Türkçe | ✅ YAPILDI |
