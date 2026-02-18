# Changelog

Tüm önemli değişiklikler bu dosyada listelenir.

Format [Keep a Changelog](https://keepachangelog.com/tr/1.0.0/) esas alınır.

---

## [3.10.67] - 2026-02-18

### Düzeltmeler

- **Telegram video:** `.legacy` MP4'ler artık engellenmez; gönderimde hata olursa `send_document` fallback + log eklendi.
- **Motion presetleri:** Eco/Balanced/Frigate/Quality ayarları güncellendi; varsayılan artık Balanced.
- **Motion global ayar:** Kamera custom yoksa global motion ayarı uygulanır (eski default override engellendi).
- **MP reconnect:** Multiprocessing modunda read failure sonrası go2rtc stream yeniden açılır.

## [3.10.56] - 2026-02-18

### Düzeltmeler

- **Live View (Ingress):** MJPEG response header’ları ile HA ingress buffering/sıkıştırma sorunu azaltıldı.
- **Live View fallback:** go2rtc MJPEG erişilemezse worker frame’lerinden yayın.

## [3.10.53] - 2026-02-18

### Düzeltmeler

- **Live View (Ingress):** MJPEG response header’larına `Content-Encoding: identity` ve `X-Accel-Buffering: no` eklendi; HA ingress sıkıştırma/buffering sorunlarıyla uyum.

## [3.10.52] - 2026-02-18

### Eklenenler

- **Live View fallback:** go2rtc MJPEG erişilemezse worker frame’lerinden MJPEG yayın.
- **Event gate debug:** MP modda min_duration/cooldown/temporal nedenleri için debug logları.

### Değişenler

- **go2rtc sağlığı:** availability dinamik yenileniyor (restart sonrası otomatik toparlama).

### Düzeltmeler

- **MP motion cooldown:** hızlı active/idle dalgalanması sonrası event kaçırma azaltıldı.
- **MP zone filtre:** polygon kontrolü ve zone payload aktarımı düzeltildi.
- **Motion log:** efektif min_area eşiği loglanıyor.

## [3.10.51] - 2026-02-16

### Eklenenler

- **Motion filtresi logları:** Motion aktif/idle geçişleri ve alan/eşik bilgisi loglanır (MP + threading).

### Değişenler

- **Yeni kamera akışı:** go2rtc config güncellemesi detection/recording öncesine alındı; update sonrası detection yeniden başlatılır.
- **RTSP açılışı retry:** go2rtc reload gecikmesine karşı MP detector açılış denemeleri backoff ile sürer.

### Düzeltmeler

- **Gürültülü loglar:** Bazı RTSP ve kamera durumu logları debug seviyesine çekildi.

## [3.10.45] - 2026-02-16

### Eklenenler

- **Auto backend seçimi:** `auto` artık TensorRT → OpenVINO(GPU) → ONNX → PT sırasıyla dener; seçilen backend loga yazılır.
- **Backend rehberi:** Inference backend seçimi geniş panel + kısa açıklamalarla daha anlaşılır.
- **Preset açıklamaları:** Dengeli ve Güvenilir farkı (stream/event stabilite) netleştirildi.

---

## [3.10.44] - 2026-02-16

### Eklenenler

- **Diagnostics – Worker:** Sistem Tanılama sayfasında Worker kartı (mod: threading/multiprocessing, process sayısı, PIDs). Multiprocessing açık mı kontrol edilebilir.
- **System info:** `/api/system/info` yanıtına `worker` alanı eklendi.

---

## [3.10.43] - 2026-02-16

### Değişenler

- **Live View – tek kamera:** Grid kaldırıldı; tek kamera seçimi + tek yayın. Açılır listeden kamera seçilir, yayın go2rtc üzerinden.
- **Live stream – sadece go2rtc:** Canlı yayın fallback’siz yalnızca go2rtc; go2rtc yoksa net 503 mesajı.

### Düzeltmeler

- **Live View ayarları:** MJPEG kalitesi kaldırıldı; sabit 92 ile kararlı yayın, arayüz sadeleştirildi.
- **Worker modu:** Health ve system info’da worker bilgisi; Ayarlar’da “addon yeniden başlatıldıktan sonra geçerli” notu.

---

## [3.10.42] - 2026-02-16

### Düzeltmeler

- **MP4 .legacy:** OpenCV fallback ile oluşturulan MP4 artık gösteriliyor; .legacy marker mp4_url'yi engellemiyordu (collage var video yok).

---

## [3.10.41] - 2026-02-16

### Düzeltmeler

- **AI collage path:** `str` veya `Path` kabul ediyor; `'str' object has no attribute 'exists'` hatası giderildi.
- **Disk limit varsayılan:** %80 → %85 (HA ortamında daha uygun).

---

## [3.10.40] - 2026-02-16

### Düzeltmeler

- **AI onayı UI:** AI onayladığında `rejected_by_ai = False` açıkça ayarlanıyor; video/event artık "onaysız" görünmüyor.

---

## [3.10.39] - 2026-02-16

### Değişenler

- **Event timestamp:** Frame zamanı (`current_time`) kullanılıyor – `datetime.utcnow()` yerine buffer ile tam uyum.
- **Medya sırası:** Video/collage önce üretiliyor, AI sonra – AI beklemeden zaman tutarlılığı.
- **AI onayı son kapı:** MQTT/WebSocket/Telegram sadece AI onayladığında gönderiliyor; reddederse event UI'da kalıyor.
- **Recorder log:** Segment bulunamadığında search range vs mevcut segment aralığı loglanıyor.

### Düzeltmeler

- **Media UTC:** Local timezone fallback kaldırıldı (FFmpeg TZ=UTC ile tutarsızlık).
- **Event timestamp:** DB'den okunan `event.timestamp` için naive/aware UTC işleme düzeltildi.

---

## [3.10.38] - 2026-02-16

### Düzeltmeler

- **Video oluşturma:** Event timestamp artık detection zamanını kullanıyor (recording extract için doğru aralık).
- **Buffer:** Child process 250 frame kullanıyor (main ile uyumlu).
- **Loglama:** buffer_info eksik, "No frames" ve MP4 hata durumları için diagnostik loglar.

---

## [3.10.37] - 2026-02-16

### Eklenenler

- **Substream (Detection):** `rtsp_url_detection` ile detection için düşük çözünürlüklü substream kullanımı. Kamera formunda "Substream (Detection)" alanı – tanımlanırsa detection bu URL üzerinden yapılır, recording/live main stream'de kalır (~%5 CPU / 10 kamera hedefi).
- **Video fallback:** MP4 oluşturma başarısız olursa ilk frame ile minimal video üretiliyor.
- **extract_frames:** Recording'den frame kurtarma için `max_frames` 5 → 60.

### Düzeltmeler

- **Buffer zaman aralığı:** Tam aralıkta frame yoksa 2x prebuffer/postbuffer ile tekrar deneniyor.
- **Event MP4:** `Accept-Ranges: bytes` header, H.264 baseline profile (tarayıcı uyumluluğu).

---

## [3.10.36] - 2026-02-16

### Değişenler

- **Scrypted-style tek kaynak:** Tüm stream akışı (Live, Detection, Recording) artık sadece go2rtc üzerinden. Fallback yok – go2rtc aktif olmalı.
- **detector_mp:** Sadece go2rtc restream kullanıyor.
- **detector (threading):** Sadece go2rtc restream, direct RTSP kaldırıldı.
- **recorder:** go2rtc restream üzerinden kayıt.
- **Live / Snapshot:** go2rtc restream kullanılıyor.

---

## [3.10.35] - 2026-02-16

### Düzeltmeler

- **Ingress tam destek:** Merkezi `resolveApiPath()` ile tüm API/media URL’leri (collage, MP4, live stream, snapshot) Ingress prefix ile güncelleniyor. EventCard, EventDetail, Dashboard, AITab, EventCompare, StreamViewer, ZonesTab tek kaynaktan güncellendi.
- **AI reddeden eventler:** MP4 artık AI reddetse bile üretiliyor; collage + video "AI Reddedilenler" sekmesinde görüntülenebilir.
- **Event video oynatma:** OpenCV fallback MP4’ler için faststart remux eklendi; tarayıcıda siyah ekran azaltıldı.
- **EventDetail MP4 polling:** MP4 henüz hazır değilse (son 60 sn) 3 sn aralıkla API’den güncelleme alınıyor.

### Değişenler

- **Nginx:** API location için `proxy_request_buffering off` eklendi (video streaming için).

---

## [3.10.23] - 2026-02-10

### Değişenler

- **Event video buffer FPS:** SharedFrameBuffer artık `record_fps` (varsayılan 10) kullanıyor; önceden sabit 5 FPS vardı. Ayarlar → Events → Frame rate ile 1–30 arası ayarlanabilir; daha akıcı timelapse için 15–20 önerilir.

### Eklenenler

- **docs/VIDEO_QUALITY_ANALYSIS.md:** Event video kalite değişkenliği analizi ve iyileştirme önerileri.

---

## [3.10.22] - 2026-02-10

### Düzeltmeler

- **go2rtc buffer tutarlılığı:** detector_mp artık `config.stream.buffer_size` kullanıyor; önceden sabit 3 vardı.
- **go2rtc "reader is too slow" dokümantasyonu:** `docs/GO2RTC_SLOW_READER.md` güncellendi – buffer değerleri, performans etkisi ve tavsiyeler (substream, direct RTSP, log seviyesi, kamera FPS) eklendi.

---

## [3.10.21] - 2026-02-14

### Düzeltmeler

- **go2rtc Live View:** Ingress üzerinden /live sayfasındayken go2rtc URL'si yanlış base path kullanıyordu (…/live/go2rtc → 404). Artık Ingress base doğru çıkarılıyor.
- **go2rtc WebRTC modu:** WebRTC seçiliyken backend stream_url döndürmüyordu; MJPEG fallback URL'si eksikti. Artık webrtc modunda da stream_url üretiliyor.

---

## [3.10.20] - 2026-02-14

### Eklenenler

- **Telegram video_speed:** Ayarlardan event video hızı (web + Telegram için tek video) artık yönetiliyor.
- **Telegram max_messages_per_min:** Dakika başı mesaj limiti backend'de uygulanıyor.
- **Telegram ayar açıklamaları:** Video hızı, cooldown, rate limit için TR/EN açıklamalar eklendi.
- **Appearance:** Dil değişikliği backend config'e kaydediliyor.

### Değişenler

- **Kamera Ayarları:** 3 kolonlu gruplu layout, collapse "Gelişmiş" bölümler, kısa algoritma ipuçları.
- **Ayarlar sadeleştirme:** Kullanılmayan DetectionTab, MotionTab, ThermalTab, StreamTab kaldırıldı; enable_tracking UI'dan çıkarıldı.
- **SettingsTabs:** Tekrarlayan performance tab kaldırıldı.

### Düzeltmeler

- **API audit:** Tüm uçlar ve ayar tab'ları kontrol edildi; `docs/API_AUDIT.md` eklendi.

---

## [3.10.19] - 2026-02-14

### Düzeltmeler

- **WebSocket:** Ping 15 sn, reconnect 2 sn, sınırsız deneme – bağlantı kopması azaltıldı.

---

## [3.10.18] - 2026-02-14

### Düzeltmeler

- **Port:** RTSP host port 19854'e alındı (8554/8555 çakışma önlendi).

---

## [3.10.17] - 2026-02-14

### Düzeltmeler

- **Port 8554:** RTSP host port 8555'e alındı (çakışma önlendi).

---

## [3.10.16] - 2026-02-14

### Düzeltmeler

- **Port:** go2rtc port formatı düzeltildi (container 1984 → host 1985).

---

## [3.10.15] - 2026-02-14

### Düzeltmeler

- Root yapı geri yüklendi (dockerfile missing hatası giderildi).
- Port 1985, migration fix, stream_roles tüm iyileştirmeler dahil.

---

## [3.10.14] - 2026-02-14

### Düzeltmeler

- **Port 1984:** go2rtc host port 1985'e alındı (başka uygulama 1984 kullanıyorsa çakışma önlenir).

---

## [3.10.13] - 2026-02-10

### Düzeltmeler

- **Başlangıç:** run.sh migration app import kaldırıldı, standalone script kullanılıyor; addon açılışta çökmesi düzeltildi.

---

## [3.10.12] - 2026-02-10

### Düzeltmeler

- **Algılama:** Boş `stream_roles` olan kameralar artık algılanıyor (geriye dönük uyum).

---

## [3.10.11] - 2026-02-10

### Değişenler

- **Versiyon:** Tek kaynak config.yaml; uygulama versiyonu otomatik oradan okunuyor.

---

## [3.10.10] - 2026-02-10

### Düzeltmeler

- **MP4 hızlandırma:** MP4_MIN_OUTPUT_DURATION 20→3, MP4_SPEED_FACTOR 3→4; 20 sn içerik ~5 sn MP4 olarak çıkıyor.
- **Tek versiyon kaynağı:** Tüm uygulama (API health, system info, MQTT) `app/version.py` üzerinden tek parametreden versiyon alıyor.

---

## [2.5.9] - 2026-02-10

### Düzeltmeler

- **Hareket tespiti:** Migration gevşetildi – confidence 0.30, thermal 0.35, cooldown 7sn, min_event_duration 1sn. Varsayılanlar ve 4 Performance preset güncellendi.

---

## [2.5.8] - 2026-02-10

### Düzeltmeler

- **Live View 502/Loading:** MJPEG artık go2rtc üzerinden sunuluyor; backend RTSP blocking ve timeout kaynaklı 502 hatası giderildi. Ingress go2rtc path düzeltmesi, 502 toast spam azaltıldı.

---

## [2.5.7] - 2026-02-10

### Düzeltmeler

- **AI gate:** AI aktifken video/media yalnızca AI onayından sonra oluşturulur. AI reddederse event ve media silinir; MP4/GIF hiç üretilmez. AI kapalıyken normal akış devam eder (detector.py ve detector_mp.py).

---

## [2.3.0] - 2026-02-11

### Değişenler

- **MP4 fallback:** Kayıt yoksa frame-based MP4 üretiliyor (video her zaman oluşur).
- **Recording tab:** Gereksiz ayarlar kaldırıldı; saklama Medya sekmesinde.

### Düzeltmeler

- Event video "No data" hatası düzeltildi (MP4 fallback geri eklendi).

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

[2.5.9]: https://github.com/cataloglu/thermal-dual-vision/compare/v2.5.8...v2.5.9
[2.5.8]: https://github.com/cataloglu/thermal-dual-vision/compare/v2.5.7...v2.5.8
[2.5.7]: https://github.com/cataloglu/thermal-dual-vision/compare/v2.5.6...v2.5.7
[2.3.0]: https://github.com/cataloglu/thermal-dual-vision/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/cataloglu/thermal-dual-vision/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/cataloglu/thermal-dual-vision/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/cataloglu/thermal-dual-vision/releases/tag/v2.0.0
