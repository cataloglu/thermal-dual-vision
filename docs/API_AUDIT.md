# API & Ayarlar Audit Raporu

## API Uçları – Durum

| Endpoint | Method | Kullanım | Durum |
|----------|--------|----------|-------|
| `/api/health` | GET | Dashboard, Layout | ✅ |
| `/api/system/info` | GET | Diagnostics | ✅ |
| `/api/logs` | GET | Diagnostics | ✅ |
| `/api/logs/clear` | POST | Diagnostics | ✅ |
| `/api/settings` | GET | Tüm ayar tab'ları | ✅ |
| `/api/settings` | PUT | Kaydet (partial) | ✅ |
| `/api/settings/defaults` | GET | (frontend'de kullanılmıyor) | ⚠️ |
| `/api/settings/reset` | POST | Reset butonu | ✅ |
| `/api/cameras` | GET | Kamera listesi, Zones, Events | ✅ |
| `/api/cameras` | POST | Yeni kamera | ✅ |
| `/api/cameras/{id}` | PUT | Kamera güncelle | ✅ |
| `/api/cameras/{id}` | DELETE | Kamera sil | ✅ |
| `/api/cameras/test` | POST | Kamera test | ✅ |
| `/api/cameras/{id}/snapshot` | GET | Zone editor, preview | ✅ |
| `/api/cameras/{id}/zones` | GET | Zone listesi | ✅ |
| `/api/cameras/{id}/zones` | POST | Yeni zone | ✅ |
| `/api/cameras/{id}/record` | GET | Recording durumu | ✅ |
| `/api/cameras/{id}/record/start` | POST | Kayıt başlat | ✅ |
| `/api/cameras/{id}/record/stop` | POST | Kayıt durdur | ✅ |
| `/api/zones/{id}` | PUT | Zone güncelle | ✅ |
| `/api/zones/{id}` | DELETE | Zone sil | ✅ |
| `/api/events` | GET | Event listesi | ✅ |
| `/api/events/{id}` | GET | Event detay | ✅ |
| `/api/events/{id}` | DELETE | Event sil | ✅ |
| `/api/events/bulk-delete` | POST | Toplu silme | ✅ |
| `/api/events/clear` | POST | Filtreyle silme | ✅ |
| `/api/live` | GET | Canlı akış listesi | ✅ |
| `/api/ai/test` | POST | AI API test | ✅ |
| `/api/ai/test-event` | POST | Event özet test | ✅ |
| `/api/telegram/test` | POST | Telegram test | ✅ |
| `/api/mqtt/status` | GET | MQTT monitoring | ✅ |

## Ayar Tab'ları – Backend Bağlantısı

| Tab | Config alanı | Kaydetme | Durum |
|-----|--------------|----------|-------|
| Kameralar | - | CRUD API | ✅ |
| Kamera Ayarları | detection, motion, thermal, stream, performance | handleSavePartial | ✅ |
| Zones | - | Zones API | ✅ |
| Live | live | handleSave | ✅ |
| Recording | - | Sadece bilgi (retention Media'da) | ✅ |
| Events | event | handleSave | ✅ |
| Media | media | handleSave | ✅ |
| AI | ai | handleSave | ✅ |
| Telegram | telegram | handleSave | ✅ |
| MQTT | mqtt | saveSettings (otomatik) | ✅ |
| Appearance | appearance | handleSave | ✅ (düzeltildi) |

## Yapılan Düzeltme

**AppearanceTab:** Dil değişikliği önceden sadece `localStorage` ve i18n ile yapılıyordu, backend config güncellenmiyordu. Artık dil değişince `appearance.language` backend'e de kaydediliyor.

## Config Model Eşleşmesi (Frontend ↔ Backend)

- `detection`, `motion`, `thermal`, `stream`, `live`, `record`, `event`, `media`, `ai`, `telegram`, `performance`, `mqtt`, `appearance` → Tüm alanlar uyumlu ✅
- `record` (backend) = `record` (frontend) ✅

## Notlar

- `getDefaultSettings` frontend'de hiçbir yerde kullanılmıyor; ileride "Varsayılanlara dön" benzeri bir akışta kullanılabilir.
- MQTT tab kendi `useSettings` instance'ı ile çalışıyor ve her değişiklikte anında kaydediyor; parent ile state paylaşmıyor ama bu tasarım gereği.
- Recording tab sadece bilgi gösteriyor, retention ayarı Media tab'da.
