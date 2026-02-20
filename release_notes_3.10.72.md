# v3.10.72 — Teknik Refactor

Bu sürüm kullanıcıya görünür yeni özellik içermez. Kod kalitesini ve bakım kolaylığını artıran teknik iyileştirmeler yapıldı.

## Yapılan Değişiklikler

### `main.py` Bölündü
2566 satırlık tek dosya, 6 ayrı router'a ayrıldı:
- `app/routers/cameras.py` — kamera CRUD, zone, kayıt, snapshot
- `app/routers/events.py` — event CRUD, medya endpoint'leri
- `app/routers/live.py` — MJPEG stream, canlı snapshot
- `app/routers/settings.py` — ayarlar, MQTT durumu
- `app/routers/system.py` — loglar, sistem bilgisi, AI/Telegram test, video analiz
- `app/routers/websocket_router.py` — WebSocket endpoint

### Servis Yönetimi
- `app/dependencies.py` oluşturuldu: tüm singleton'lar tek yerden

### AI Onay String'leri
- `app/services/ai_constants.py` oluşturuldu
- `detector.py` ve `detector_mp.py` artık bu sabitleri kullanıyor

### Küçük Temizlikler
- `ai_test.py` → `ai_probe.py` olarak yeniden adlandırıldı
- `go2rtc` URL oluşturma mantığı tek yerde toplandı (`Go2RTCService.build_restream_url`)
- `main.py` içindeki duplicate import'lar kaldırıldı

## Kullanıcıya Etkisi

Sıfır. Tüm API endpoint'leri aynı, tüm davranışlar aynı.
