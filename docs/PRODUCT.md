# PRODUCT SPEC — Smart Motion Detector (v2)

## 0) Scope (Değişmez Kurallar)
- Bu ürün **SADECE insan (person)** algılar.
- İnsan algılama için **iki model** bulunur ve **seçilebilir**: `yolov8n-person` / `yolov8s-person`.
- İnsan algılama **kamera bazında** color/thermal seçilebilir (dual kamerada kaynak seçimi).
- Zone/ROI desteği vardır: hareket ve person algılama alanları kamera bazında seçilir.
- AI (OpenAI) **opsiyoneldir**:
  - API key yoksa sistem **çalışmaya devam eder**.
  - UI’da “AI Disabled” ve sebep görünür.
- Dashboard’da **canlı görüntü yok**.
- Canlı görüntü **ayrı sayfa** (Live).
- “Yakalanan hareketler / Events” ürünün ana sayfasıdır.
- “Review” kavramı **Events ile aynıdır** (sadece motion/person event’leri).
- Her event **kanıt** üretir:
  - 5 kare birleşik görsel (collage)
  - preview GIF
  - ~20 sn hızlandırılmış MP4 (timelapse)
- Event medya dosyaları **kalıcı değildir**: retention politikası vardır ve ayarlanabilir.
- Kayıt (record) **sürekli değil**, sadece event bazlıdır.
- Disk temizleme stratejisi vardır (retention + disk limiti) ve kullanıcı değiştirebilir.
- Ayarlar **kalıcıdır**: restart sonrası korunur.
- Placeholder UI kabul edilmez: form varsa **kaydetmeli** ve backend’e **POST/PUT** atmalıdır.

---

## 1) Kullanıcı Akışı (Happy Path)
1. Kullanıcı UI’a girer → Dashboard’da sistem durumunu görür.
2. Settings → Cameras bölümünden kamera ekler:
   - Camera Type: `color` / `thermal` / `dual`
   - RTSP URL (veya channel seçimi)
   - Test butonu ile snapshot alır → OK ise kaydeder.
3. Sistem person algıladığında Event oluşur:
   - Events sayfasında event kartı görünür.
   - Kartta collage + GIF + MP4 linkleri bulunur.
   - AI açıksa kısa açıklama görünür.
4. Telegram açıksa:
   - Event açıklaması + collage + MP4 gönderilir.

---

## 2) Web UI Sayfaları (MVP)
### A) Dashboard
- Sistem sağlık özeti (/api/health)
- Kameraların bağlantı durumu (connected / retrying / down)
- AI durumu: enabled/disabled + reason
- Son event kısa özet (link)

### B) Live
- Kamera canlı görüntü grid
- 1x1 / 2x2 / 3x3
- Overlay yok
- Stream modu: `mjpeg` (default) veya `webrtc` (opsiyonel, go2rtc gerektirir)

### C) Events (Captured)
- Pagination (sayfalı)
- Filtre: camera, date, confidence
- Her event kartı:
  - collage preview
  - GIF preview
  - MP4 indir/izle
  - AI summary (varsa)

### D) Settings
**Settings altında sekmeler:**
- Cameras (CRUD + test)
- Detection (global defaults + per-camera overrides)
- Detection Source (color / thermal / auto)
- Detection Model (iki modelden biri seçilebilir)
- Zones (motion/person alanları)
- AI (enable toggle + key + model)
- Telegram (enable + token + chat id + test)

### E) Diagnostics
- /api/health çıktısı
- /ready çıktısı
- retry/backoff durumları
- son hatalar (camera last_error)
- basic logs tail

---

## 3) Camera Model (Konsept)
- Multi-camera destek
- Her kamera:
  - id, name, type, enabled
  - rtsp_url (maskelenir)
  - per-camera motion override (opsiyonel)
  - detection_source: `color` / `thermal` / `auto`
  - stream_roles: `detect` / `live` / `record`
  - zones: motion/person alanları (polygon)

---

## 4) Event Model (Konsept)
- Event oluşturma trigger’ı: person detected
- Her event dosyaları:
  - collage.jpg (5 frame)
  - preview.gif
  - timelapse.mp4 (~20s accelerated)
- AI çalışırsa event’e `ai.summary` eklenir.
- AI çalışmazsa `ai.disabled_reason` yazılır.

---

## 5) Out of Scope (MVP dışı)
- Generic object detection
- Face recognition
- Full NVR recording / sürekli kayıt
- Complex rule engine
- Multi-user auth (şimdilik yok)

---

## 6) Acceptance Criteria (MVP biterken)
- UI’da kamera ekleyip test edip kaydedebiliyorum.
- Live sayfasında canlı görüntü açılıyor.
- Person algılanınca Events listesine düşüyor.
- Event medya dosyaları oluşuyor (collage/gif/mp4).
- AI key yokken sistem crash olmuyor, UI “AI disabled” diyor.
- Telegram açıksa collage + mp4 + mesaj gidiyor.