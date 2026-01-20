# DESIGN SYSTEM — Smart Motion Detector (v2)

## 0) Genel Stil
- Tema: **Dark** (default)
- Stil: Frigate benzeri ama daha sade, “dashboard” hissi
- Font: System UI (default)
- Dil: TR/EN (UI metinleri ileride i18n ile ayrılır; şimdilik TR)

---

## 1) Renk Paleti (Dark)
- Background: #0B1020
- Surface 1:  #111A2E
- Surface 2:  #17223A
- Border:     #22304A
- Text:       #E6EAF2
- Muted text: #9AA6BF

### Durum Renkleri
- Success: #2ECC71
- Warning: #F5A524
- Error:   #FF4D4F
- Info:    #3B82F6

### Accent (marka rengi)
- Accent: #5B8CFF (butonlar, seçili menü, linkler)

---

## 2) Layout Kuralları
- Sol menü (sidebar): sabit, ikon + label
- Üst bar: sayfa başlığı + sağda küçük “system status dot”
- Ana içerik: kart bazlı grid
- Her sayfa üstte:
  - Title
  - Subtitle (1 satır)
  - Sağda primary action (varsa)

---

## 3) Navigasyon (MVP)
Sidebar menü:
1. Dashboard
2. Live
3. Events
4. Settings
5. Diagnostics

---

## 4) Bileşenler

### Card
- Round: 14px
- Padding: 16px
- Border: 1px solid Border rengi
- Hover: çok hafif brighten

### Button
- Primary: Accent arkaplan + beyaz yazı
- Secondary: Surface2 + border
- Danger: Error rengi

### Input
- Dark input, border visible
- Placeholder muted
- Error state kırmızı border + küçük helper text

### Badge (Status chip)
- `OK` / `DEGRADED` / `DOWN` gibi kısa etiketler
- Success/Warning/Error renkleriyle

### Table / List
- Events sayfasında list: kart-list hibrit
- Satır hover highlight

---

## 5) Sayfa Bazlı UI Notları

### Dashboard
- Canlı görüntü YOK
- Kartlar:
  - System Health (OK/DEGRADED/DOWN)
  - Cameras Summary (X online / Y retry / Z down)
  - AI Status (enabled/disabled + reason)
  - Last Event (thumbnail collage + link)

### Live
- Grid, her tile:
  - Camera name
  - küçük status dot
  - stream frame
- Fullscreen opsiyonel (sonra)
- Stream mode bilgisi: `mjpeg` / `webrtc`
- `webrtc` seçiliyse go2rtc gereklilik uyarısı
- Reconnect durumu (spinner + kısa mesaj)

### Events
- Default: newest first
- Event kartı:
  - sol: collage thumbnail
  - sağ: camera name, time, confidence
  - actions: View / Download GIF / Download MP4
  - AI summary: 2 satır clamp
- Retention bilgisi (medya süresi) küçük not olarak gösterilebilir
- “Review” sayfası yok; Events sayfası review rolündedir

### Settings
- Sekmeler:
  - Cameras
  - Detection
  - Detection Source
  - Detection Model
  - Zones
  - Live Stream
  - Recording
  - AI
  - Telegram
- Cameras:
  - “Add camera” form (wizard yok)
  - Camera type select (color/thermal/dual)
  - RTSP input + “Test” button
  - Test sonucu: snapshot preview + latency + error text
 - Detection Model:
  - Tek seçim (radio/select)
  - Seçenekler: `yolov8n-person` / `yolov8s-person`
 - Detection Source:
  - Kamera bazında seçim (color/thermal/auto)
  - Thermal için “önerilen ayarlar” kısa açıklaması
  - Motion ayarları UI’dan seçilebilir (preset + manuel)
 - Zones:
  - Kamera seçimi + sahne önizleme
  - Polygon çizimi (add/remove point)
  - Mod seçimi: `motion` / `person` / `both`
  - Enable toggle + isim
 - Live Stream:
  - Stream modu seçimi: `mjpeg` / `webrtc`
  - webrtc için go2rtc URL alanı
 - Recording:
  - Enable toggle
  - Retention days
  - Segment length (seconds)
  - Disk limit (%) + cleanup policy (oldest first)
  - Media delete order (mp4 → gif → collage)
  - Default değerler gösterilir ve değiştirilebilir

### Diagnostics
- JSON viewer (pretty)
- log tail (son 200 satır)
- copy button

---

## 6) UX Kuralları
- Her form:
  - Save butonu disabled (dirty değilse)
  - Save sonrası toast: “Saved”
  - Hata mesajı net ve kısa
- Secrets:
  - UI’da maskeli göster
  - “Show” toggle opsiyonel (default: kapalı)
- Performans:
  - Live view dışında hiçbir sayfa stream çekmeyecek

---

## 7) “Do Not Do” (yasaklar)
- Dashboard’a canlı görüntü koyma
- Placeholder text bırakma (form yoksa sayfa yok sayılır)
- AI key yok diye crash ettirme
- RTSP URL’yi loglarda açık yazma

---

## 8) UI Decisions (kilitlenecek maddeler)
- Settings sekmelerinde alan sırası ve global/per-camera ayrımı
- Motion preset değerleri (thermal öneri değerleri + manuel override davranışı)
- Event detail görünümü (ayrı sayfa vs modal) ve içerik listesi
- Boş/hata durumları için metin ve görünüm
- Live view stream UX (mjpeg/ws) + reconnect davranışı
- UI metinleri (başlık/label listesi, TR içerik)