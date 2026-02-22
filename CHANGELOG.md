# Changelog

Tüm önemli değişiklikler bu dosyada listelenir.

Format [Keep a Changelog](https://keepachangelog.com/tr/1.0.0/) esas alınır.

---

## [4.0.10] - 2026-02-22

### Düzeltmeler

- Settings ekranındaki `Reset Defaults` akışı sayfa-bazlı hale getirildi; global reset çağrısı kaldırıldı.
- Ayarlar ekranına ikinci onaylı `Factory Default (Full Reset)` butonu eklendi (`FACTORY` yazma onayı).
- Detection/Performance presetlerinin `event` ayarlarını istemeden ezmesi engellendi.
- İnsan tespiti yokken sahte collage/media üretimini kesen koruma her iki worker moduna da eklendi.
- Kısa geçişlerde kaçırmayı azaltmak için temporal consistency ayarı `2/2` olarak güncellendi.

## [4.0.9] - 2026-02-22

### Düzeltmeler

- Collage event vurgusunda tam-kare mavi çerçeve kaldırıldı; işaretleme yalnızca kişi bbox alanına çekildi.
- `min_event_duration` kullanıcı kontrolüne geri alındı; zorunlu `1.5s` clamp kaldırıldı.
- Event cooldown varsayılanı `60s` olarak güncellendi; kullanıcı değişikliği korunur.
- Settings update akışında kullanıcı ayarlarını ezen sanitize kuralları kaldırıldı; yalnızca eksik/geçersiz alanlar normalize edilir.
- Save sırasında `***REDACTED***` değerlerinin gerçek secret üzerine yazılmasını engelleyen koruma eklendi.

## [4.0.8] - 2026-02-22

### Düzeltmeler

- Threading detector için `stream_stale` gate debounce eklendi; anlık spike'larda yanlış stale tetiklemesi azaltıldı.
- Reconnect döngüsüne cooldown eklendi; kısa sürede art arda reconnect engellendi.
- Geçici toparlanma reconnect logları `warning` yerine `info` seviyesine çekildi.

## [4.0.7] - 2026-02-22

### Düzeltmeler

- Auto motion eşikleme yeniden ayarlandı; `min_area` değerinin sık sık tavana (`2500`) vurması azaltıldı.
- Ürün varsayılanları güncellendi: `auto_multiplier=1.0`, `auto_min_area_ceiling=1800`.
- Threading modda `stream_stale` gate daha toleranslı hale getirildi; kısa frame gecikmelerinde gereksiz reconnect azaltıldı.

## [4.0.6] - 2026-02-22

### Düzeltmeler

- Threading detector başlangıcında görülen `Camera ... is not bound to a Session` hatası giderildi.
- Kamera ORM nesneleri thread başlatmadan önce güvenli snapshot nesnelerine çevrildi.
- Başlangıçta detection loop'un kamera bazında düşmesi engellendi; threading modda stabilite artırıldı.

## [4.0.5] - 2026-02-22

### İyileştirmeler

- Product varsayılanları stabilize edildi: motion her zaman global auto modunda çalışır.
- False alarm azaltımı için `auto_profile=low`, `sensitivity=4`, `cooldown=3`, `auto_min_area_floor>=120` politikası sabitlendi.
- UI tarafında manual motion modu kapatıldı; üretim davranışı tek ve tutarlı hale getirildi.

## [4.0.4] - 2026-02-21

### İyileştirmeler

- AI onay akışı hızlandırıldı: Collage analizi sonrası AI onay verirse MQTT bildirimi video beklemeden hemen yayınlanır.
- MP4 üretimi arka planda devam eder; event bildirimi medya üretimi nedeniyle gecikmez.
- `postbuffer_seconds` ürün politikası olarak `2.0s` sabitlendi ve UI'dan kaldırıldı.

## [3.10.97] - 2026-02-20

### Düzeltmeler (Bug Fix Sprint)

- **K-1:** SQLite WAL modu + foreign key enforcement her bağlantıda etkin
- **K-2:** Settings `deepcopy` düzeltmesi — migration'lar artık diske yazılıyor
- **K-3:** Paylaşımlı frame buffer yazmaları `mp.Lock` ile korunuyor
- **K-4:** Çöken kamera process 5 saniye sonra otomatik yeniden başlatılıyor
- **Y-1/Y-2:** Recorder zombie fix (`wait` sonrası `kill`) + process dict thread-safe
- **Y-3:** go2rtc YAML config yazmaları atomik (tmp→rename) + lock korumalı
- **Y-4:** Çift MQTT reconnect mekanizması devre dışı (paho + manual thread çakışması)
- **Y-5:** `rejected_only=None` artık event filtrelemiyor (tümü gösteriliyor)
- **Y-6:** cameras/status N+1 sorgusu tek GROUP BY aggregate ile değiştirildi
- **Y-7:** Video seeking — Range:bytes header'ı 206 Partial Content döndürüyor
- **Y-8:** `main.py` `detector_worker` `UnboundLocalError` riski giderildi
- **Y-9:** `stop()` shared memory serbest bırakmadan önce event_handler_thread'i join ediyor
- **Y-10:** `useWebSocket` callback'leri ref'lerde saklanıyor — parent re-render'da reconnect yok
- **O-1:** `video_analyzer` `VideoCapture` try/finally ile sarıldı
- **D-1–D-16:** i18n, locale, confirm dialog, auto-save, localStorage quota, datetime.utcnow düzeltmeleri

## [3.10.75] - 2026-02-19

### Düzeltmeler

- **AI bağımsız analiz (kutu yok):** AI collage'ına bounding box çizilmemesi sağlandı.

## [3.10.74] - 2026-02-19

### Düzeltmeler

- **AI yanlış onay sorunu:** Prompt'a YOLO güven skoru ekleniyor; dinamik prompt oluşturma.

## [3.10.73] - 2026-02-19

### İyileştirmeler

- **Kritik: Paralel event işleme (detector_mp):** Her detection eventi kendi Thread'inde işleniyor.

## [3.10.72] - 2026-02-19

### Teknik İyileştirmeler (Refactor)

- **`app/main.py` bölündü:** 2566 satırlık god file, 6 ayrı router dosyasına ayrıldı.
- **`app/dependencies.py` oluşturuldu:** Tüm servis singleton'ları tek yerden yönetilir.
- **AI onay string'leri merkezi hale getirildi:** `app/services/ai_constants.py`'e taşındı.
- **`_get_go2rtc_restream_url` tekrarı kaldırıldı:** `Go2RTCService.build_restream_url()` metodunda birleştirildi.
- **`ai_test.py` → `ai_probe.py`:** Servis klasöründeki yanıltıcı isim düzeltildi.
- **`postbuffer_seconds` sanitizer override sorunu:** Sanitizer eşiği 15→3'e düşürüldü.

---

## [3.10.71] - 2026-02-19

### Düzeltmeler

- **Kritik: Boş video sorunu (recorder):** FFmpeg `returncode == 0` döndürmesi dosyanın oynatılabilir olduğunu garanti etmiyor. Kayıt segmentinde tam o zaman aralığında boşluk varsa FFmpeg geçerli MP4 container'ı ama 0 frame ile yazıyordu (< 4KB). Bu boş dosya `os.replace()` ile buffer MP4'ün üzerine yazılıyordu — AI onaylı event'te bile siyah video görülmesinin nedeni buydu. `_extract_single` ve `_extract_multi` fonksiyonlarına 4KB minimum boyut kontrolü eklendi; boyut altında kalırsa mevcut buffer MP4 korunuyor.
- **UI: Bozuk video hata mesajı:** Video oynatıcı bozuk/boş dosyayı yüklemeye çalışırken tarayıcının cryptic "no source" ikonunu göstermek yerine artık "noData" mesajı gösteriliyor (`onError` handler eklendi).

## [3.10.70] - 2026-02-19

### Düzeltmeler

- **Kritik: Kamera bağlantı kopması engellendi (MP modu):** `detector_mp.py` ana döngüsünde `cap.read()` artık FPS throttle'dan **önce** çalışır. Önceden sistem inference_fps (5fps) arasında `time.sleep(0.01)` ile bekliyordu; bu sürede go2rtc frame buffer'ı dolup "reader too slow" hatası vererek bağlantıyı kesiyordu. Artık her frame stream'den tüketilir (Scrypted/NVR yaklaşımı), inference FPS'i sadece YOLO çalıştırma sıklığını belirler. Ek olarak `frame_buffer` yazımı da FPS throttle'dan bağımsız çalışarak `record_fps` (10fps) hızında buffer doldurur.

## [3.10.69] - 2026-02-19

### İyileştirmeler

- **`postbuffer_seconds` varsayılanı:** 15 → 5 saniye. Kayıt her zaman açık olduğundan olay videosu kayıt dosyasından çıkarılır; frame buffer'ın uzun süre dolmasını beklemek gereksizdi. AI onaylı Telegram bildirimi gecikmesi ~25-45 saniyeden ~12-15 saniyeye düşer.

## [3.10.68] - 2026-02-19

### Düzeltmeler

- **Kritik: Video kaybı engellendi:** `_extract_single` ve `_extract_multi` artık FFmpeg çıktısını geçici dosyaya yazar; yalnızca başarı durumunda `os.replace()` ile hedef dosyanın üzerine atomik yazar. Böylece geç gelen kayıt çıkarma denemesi başarısız olsa da mevcut buffer MP4 bozulmadan korunur. Bu hata hem UI'da hem Telegram'da video görünmemesinin ana nedeni idi.

## [3.10.67] - 2026-02-18

### Düzeltmeler

- **Telegram video:** `.legacy` MP4'ler artık engellenmez; gönderimde hata olursa `send_document` fallback + log eklendi.
- **Motion presetleri:** Eco/Balanced/Frigate/Quality ayarları güncellendi; varsayılan artık Balanced.
- **Motion global ayar:** Kamera custom yoksa global motion ayarı uygulanır (eski default override engellendi).
- **MP reconnect:** Multiprocessing modunda read failure sonrası go2rtc stream yeniden açılır.

## [3.10.66] - 2026-02-18

### Düzeltmeler

- **Live View:** Uzayan yüklemede snapshot fallback devreye girer.

## [3.10.65] - 2026-02-18

### Düzeltmeler

- **Collage bbox:** MP modda kutu koordinatları buffer boyutuna ölçeklenir.

## [3.10.64] - 2026-02-18

### Düzeltmeler

- **Telegram video:** Video gönderimi hata verirse dosya olarak fallback.
- **Telegram log:** Video gönderim denemeleri loglanır.

## [3.10.63] - 2026-02-18

### Düzeltmeler

- **Telegram video:** `.legacy` MP4'ler artık Telegram’a gönderilir.

## [3.10.62] - 2026-02-18

### Eklenenler

- **Live Snapshot:** MJPEG çalışmazsa tek kare snapshot fallback.

## [3.10.61] - 2026-02-18

### Düzeltmeler

- **Live View:** go2rtc başarısızsa worker stream tercih edilir.

## [3.10.60] - 2026-02-18

### Düzeltmeler

- **Live View:** Worker frame hazırsa önce worker fallback kullanılır.

## [3.10.59] - 2026-02-18

### Eklenenler

- **Live Log:** Canlı görüntü altında debug bilgisi gösterilir.
- **Live probe:** `/api/live/{id}.mjpeg?probe=1` ile hızlı durum sorgusu.

## [3.10.58] - 2026-02-18

### Düzeltmeler

- **Live View:** go2rtc MJPEG ilk frame gelmezse fallback kullanılır.

## [3.10.57] - 2026-02-18

### Düzeltmeler

- **Backend crash:** Live View fallback type hint için eksik `numpy` import eklendi.

## [3.10.56] - 2026-02-18

### Düzeltmeler

- **Live View (Ingress):** MJPEG response header’ları ile HA ingress buffering/sıkıştırma sorunu azaltıldı.
- **Live View fallback:** go2rtc MJPEG başlamazsa worker frame’lerinden MJPEG yayın.

## [3.10.55] - 2026-02-18

### Düzeltmeler

- **MP motion cooldown:** Hareket algılama, cooldown süresince aktif tutulur (false negative azalır).

## [3.10.54] - 2026-02-17

### Değişenler

- **Preset ayarları:** Eco/Balanced/Frigate/Quality stream + event + motion + detection değerleri netleştirildi.
- **MP motion:** Global motion ayarları MP modda kamera ayarlarına merge edilir.

## [3.10.53] - 2026-02-17

### Eklenenler

- **CI:** GitHub Actions ile backend test + UI lint.
- **Medya sırası kontrolü:** Eşzamanlı medya üretimi sınırlandı (queue logları).

### Değişenler

- **MQTT ayarları:** Auto-save kaldırıldı, tek state + manuel kaydet akışı.
- **Tema tokenları:** UI token eşlemesi (bg-card/foreground/primary vb.).

### Düzeltmeler

- **Live View (Ingress):** MJPEG response header’larına `Content-Encoding: identity` ve `X-Accel-Buffering: no` eklendi; HA ingress sıkıştırma/buffering sorunlarıyla uyum.
- **MP zone filtresi:** Polygon check hatası giderildi.
- **go2rtc retry:** Threading + MP modda go2rtc yoksa sürekli retry + uyarı.
- **Kamera update:** Whitelist ile güvenli update.
- **Events bulk seçimi:** Filtre/sayfa değişince seçim temizlenir.
- **EventDetail:** localStorage parse güvenliği.

## [3.10.52] - 2026-02-17

### Eklenenler

- **Live View fallback:** go2rtc MJPEG erişilemezse worker frame’lerinden MJPEG yayın.
- **Event gate debug:** MP modda min_duration/cooldown/temporal nedenleri için debug logları.
- **Motion filtresi logları:** Motion aktif/idle geçişleri ve alan/eşik bilgisi loglanır (MP + threading).

### Değişenler

- **go2rtc sağlığı:** availability dinamik yenileniyor (restart sonrası otomatik toparlama).
- **Yeni kamera akışı:** go2rtc config güncellemesi detection/recording öncesine alındı; update sonrası detection yeniden başlatılır.
- **RTSP açılışı retry:** go2rtc reload gecikmesine karşı MP detector açılış denemeleri backoff ile sürer.

### Düzeltmeler

- **MP motion cooldown:** hızlı active/idle dalgalanması sonrası event kaçırma azaltıldı.
- **MP zone filtre:** polygon kontrolü ve zone payload aktarımı düzeltildi.
- **Motion log:** efektif min_area eşiği loglanıyor.
- **Gürültülü loglar:** Bazı RTSP ve kamera durumu logları debug seviyesine çekildi.

### Eklenenler

- **Motion filtresi logları:** Motion aktif/idle geçişleri ve alan/eşik bilgisi loglanır (MP + threading).

### Değişenler

- **Yeni kamera akışı:** go2rtc config güncellemesi detection/recording öncesine alındı; update sonrası detection yeniden başlatılır.
- **RTSP açılışı retry:** go2rtc reload gecikmesine karşı MP detector açılış denemeleri backoff ile sürer.

### Düzeltmeler

- **Gürültülü loglar:** Bazı RTSP ve kamera durumu logları debug seviyesine çekildi.
## [3.10.51] - 2026-02-17

### Düzeltmeler

- **Live View:** go2rtc MJPEG başlamazsa go2rtc RTSP restream ile MJPEG üretimi (tek stream desteği).

---

## [3.10.50] - 2026-02-17

### Düzeltmeler

- **Kamera silme:** Kayıt süreci silinen kamerada yeniden başlatılmıyor.
- **MP medya:** Silinen kamera için paylaşılan buffer yoksa medya üretimi temiz şekilde atlanıyor.

---

## [3.10.49] - 2026-02-17

### Düzeltmeler

- **Live View:** Ana stream yoksa go2rtc `*_detect` substream ile canlı görüntü verilir.

---

## [3.10.48] - 2026-02-17

### Düzeltmeler

- **MP kamera durumu:** Multiprocessing modunda kamera status güncellemeleri ve UI göstergeleri düzeltildi.

---

## [3.10.47] - 2026-02-17

### Değişenler

- **Kamera ekleme:** Kullanılmayan ikinci stream (substream) alanı kaldırıldı.

---

## [3.10.46] - 2026-02-17

### Düzeltmeler

- **go2rtc durumu:** Live/detection için erişilebilirlik dinamik kontrol ediliyor; geç açılan go2rtc artık sistemi kilitlemiyor.
- **go2rtc sync:** go2rtc kapalı olsa bile kamera stream config'i yazılıyor; online olduğunda restart ile yükleniyor.

---
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
