# Changelog

Tüm önemli değişiklikler bu dosyada listelenir.

Format [Keep a Changelog](https://keepachangelog.com/tr/1.0.0/) esas alınır.

---

## [2.2.0] - 2026-02-10

### Değişenler

- **Kayıt buffer:** Sürekli kayıt 7 gün yerine sabit 1 saatlik rolling buffer; her kamera son 1 saati tutar, en eskisi üzerine yazılır.
- **Event retention:** Event saklama süresi seçmeli (Sınırsız, 1-365 gün); Medya sekmesinde dropdown.
- **Event MP4:** MP4 yalnızca kaydedilen videodan oluşturulur; frame-based fallback kaldırıldı (frame tekrarı önlendi).

### Düzeltmeler

- `_select_indices` / `_select_indices_by_time`: frame tekrarı engellendi.

---

## [2.1.0] - 2026-02-10

### Eklenenler

- **Zone güncelleme (UI):** Bölge listesinde enable/disable checkbox'ı `PUT /api/zones/{id}` ile bağlandı. `updateZone` API fonksiyonu ve ilgili i18n (zoneEnabled, zoneDisabled, enableZone, disableZone) eklendi.
- **Prometheus metrikleri:** Detector tarafında `record_inference_latency`, `record_event`, `set_fps`, `set_cpu_usage` çağrıları eklendi; metrikler artık dolduruluyor.
- **Sürekli kayıttan event MP4:** Event media üretilirken önce sürekli kayıttan `extract_clip` deneniyor, yoksa frame-based MP4 üretiliyor.
- **CHANGELOG.md:** Bu dosya eklendi.

### Değişenler

- **API uyumu:** `create_camera` → 201 Created, `delete_camera` → 204 No Content. Snapshot RTSP hatası 502, live stream URL yok 409. `get_live_streams` MJPEG değilse `stream_url: null`.
- **Frontend delete_camera:** 204 yanıtında body olmadığı için `{ deleted: true }` döndürülüyor.
- **DB:** RecordingState ↔ Camera için ORM ilişkisi eklendi (one-to-one, back_populates).
- **Event oluşturma:** `create_event` çağrısına `person_count` parametresi eklendi.

### Performans

- **Varsayılan config:** `inference_fps` 5 → 3, `inference_resolution` [640,640] → [480,480] (yeni kurulum / reset).
- **CPU throttling:** CPU > %90 → FPS 1’e kadar, > %80 → 2’ye düşürme; CPU < %40’ta FPS artışı 5’te sınırlandı.
- **Motion:** Hareket hesabı 640px → 480px, GaussianBlur (5,5) → (3,3) (detector + motion servisi).

### Düzeltmeler

- Snapshot endpoint’te `result` null/eksik key güvenliği.
- Return type’lar: `get_live_stream` → StreamingResponse, `get_camera_snapshot` → Response.

---

## [2.0.0] - (önceki sürüm)

- Smart Motion Detector v2: YOLOv8 person detection, termal/renkli kamera, zones, sürekli kayıt (Scrypted-style), AI özeti, Telegram, MQTT, go2rtc entegrasyonu.

---

[2.2.0]: https://github.com/cataloglu/thermal-dual-vision/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/cataloglu/thermal-dual-vision/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/cataloglu/thermal-dual-vision/releases/tag/v2.0.0
