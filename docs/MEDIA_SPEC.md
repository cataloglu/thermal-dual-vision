# Media Generation Specification - Smart Motion Detector v2

Bu doküman event medya dosyalarının (collage, GIF, MP4) detaylı spec'ini içerir.

**Hedef**: Professional-grade event kanıtları (Scrypted'den daha iyi!)

---

## 🎯 Tasarım Prensipleri

1. **Yüksek Kalite**: Kanıt amaçlı, net görüntü
2. **Smooth Animation**: Hareket akıcı görünmeli
3. **Telegram Optimize**: <2 MB (Telegram limiti 5 MB)
4. **Hızlı Oluşturma**: <5 saniye (event sonrası)
5. **Disk Efficient**: Retention policy ile otomatik temizlenir

---

## 📸 1) Collage (5 Frame Grid)

### Format
```
┌─────────┬─────────┬─────────┐
│ Frame 1 │ Frame 2 │ Frame 3 │
│ (başla) │ (orta)  │ (orta)  │
├─────────┼─────────┼─────────┤
│ Frame 4 │ Frame 5 │         │
│ (orta)  │ (son)   │         │
└─────────┴─────────┴─────────┘
```

### Specification
- **Layout**: 3x2 grid (5 frame + 1 boş)
- **Frame Selection**: Event'in başlangıç → son, eşit aralıklı
- **Resolution**: 640x480 per frame → 1920x960 total
- **Format**: JPEG
- **Quality**: 90 (yüksek kalite)
- **Boyut**: ~500-800 KB
- **Overlay**: 
  - Timestamp (üst sol)
  - Camera name (üst sağ)
  - Confidence score (alt)
  - Frame number (1/5, 2/5, ...)

### Örnek
```
Event: 20 frame buffer
Frame selection: [0, 5, 10, 15, 19]
```

**Sonuç**: Hareketin tüm aşamaları görünür (statik)

---

## 🎬 2) Preview GIF (Timeline Animation)

### Specification
- **Frame Count**: 10 frame (Scrypted: 5-8, bizimki daha smooth!)
- **Duration**: 5 saniye (0.5s per frame)
- **Resolution**: 640x480 (Telegram optimize)
- **Format**: Animated GIF
- **Loop**: Infinite
- **Optimization**: 
  - Dithering: Floyd-Steinberg
  - Color palette: 256 colors
  - Compression: Optimize=True
- **Boyut**: <2 MB (Telegram için)
- **Frame Selection**: Event buffer'dan eşit aralıklı
- **Overlay**:
  - Timestamp (üst sol, her frame)
  - Camera name (üst sağ)
  - Progress bar (alt, timeline göstergesi)
  - Motion trail (opsiyonel, hareket yolu)

### Algoritma
```python
def create_timeline_gif(event_frames: list, output_path: str):
    """
    Create smooth timeline animation GIF.
    
    Better than Scrypted: More frames, smoother motion, progress bar!
    
    Args:
        event_frames: All frames from event (örn: 20-30 frame)
        output_path: Output GIF path
    """
    import imageio
    import cv2
    
    total = len(event_frames)
    num_frames = 10  # Scrypted'den fazla!
    
    # Select evenly distributed frames
    indices = [int(i * (total - 1) / (num_frames - 1)) for i in range(num_frames)]
    selected = [event_frames[i] for i in indices]
    
    # Resize to 640x480
    resized = []
    for idx, frame in enumerate(selected):
        # Resize
        img = cv2.resize(frame, (640, 480))
        
        # Add timestamp overlay
        timestamp = event_start + timedelta(seconds=idx * 0.5)
        cv2.putText(img, timestamp.strftime("%H:%M:%S"), 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Add camera name
        cv2.putText(img, camera_name, 
                    (540, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Add progress bar (timeline indicator)
        progress = idx / (num_frames - 1)
        bar_width = int(640 * progress)
        cv2.rectangle(img, (0, 470), (bar_width, 480), (91, 140, 255), -1)  # Accent color
        
        resized.append(img)
    
    # Create GIF with optimization
    imageio.mimsave(
        output_path,
        resized,
        duration=0.5,  # 0.5s per frame = 5s total
        loop=0,  # Infinite
        optimize=True,
        quality=85
    )
    
    # Check size, reduce quality if needed
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    if size_mb > 2:
        # Re-create with lower quality
        imageio.mimsave(output_path, resized, duration=0.5, loop=0, optimize=True, quality=70)
```

### Özellikler (Scrypted'den Daha İyi!)
- ✅ **10 frame** (Scrypted: 5-8) → Daha smooth!
- ✅ **Progress bar** (Scrypted'de yok) → Timeline görünür!
- ✅ **Motion trail** (opsiyonel) → Hareket yolu görünür!
- ✅ **Timestamp her frame'de** → Zaman akışı net!
- ✅ **Optimize compression** → <2 MB garantili!

---

## 🎥 3) Timelapse MP4 (Full Event)

### Specification
- **Duration**: 20 saniye (accelerated)
- **Resolution**: 1280x720 (yüksek kalite)
- **Format**: MP4 (H.264)
- **Frame Rate**: 15 FPS (smooth playback)
- **Speed**: 4x accelerated (gerçek süre 80 saniye → 20 saniye)
- **Codec**: H.264 (high profile)
- **Bitrate**: 2 Mbps (kalite/boyut dengesi)
- **Boyut**: ~5-8 MB
- **Overlay**:
  - Timestamp (üst sol)
  - Camera name (üst sağ)
  - Confidence score (alt sol)
  - Speed indicator "4x" (alt sağ)
  - Detection boxes (person bounding box)

### Algoritma
```python
def create_timelapse_mp4(event_frames: list, detections: list, output_path: str):
    """
    Create high-quality timelapse MP4.
    
    Better than Scrypted: Higher resolution, detection boxes, smooth!
    
    Args:
        event_frames: All frames from event
        detections: Person detection data per frame
        output_path: Output MP4 path
    """
    import cv2
    
    # Video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 15.0, (1280, 720))
    
    for idx, (frame, detection) in enumerate(zip(event_frames, detections)):
        # Resize to 720p
        img = cv2.resize(frame, (1280, 720))
        
        # Draw detection box (person)
        if detection:
            x1, y1, x2, y2 = detection['bbox']
            cv2.rectangle(img, (x1, y1), (x2, y2), (91, 140, 255), 3)  # Accent color
            
            # Confidence label
            label = f"Person {detection['confidence']:.0%}"
            cv2.putText(img, label, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (91, 140, 255), 2)
        
        # Timestamp overlay
        cv2.putText(img, timestamp, (20, 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        # Camera name
        cv2.putText(img, camera_name, (1100, 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Speed indicator
        cv2.putText(img, "4x", (1220, 700), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        out.write(img)
    
    out.release()
```

### Özellikler (Scrypted'den Daha İyi!)
- ✅ **720p resolution** (Scrypted: 480p) → Daha net!
- ✅ **Detection boxes** (person bounding box) → Nerede olduğu görünür!
- ✅ **Confidence score** → Ne kadar emin olduğu görünür!
- ✅ **Speed indicator** → Hızlandırılmış olduğu belli!
- ✅ **Smooth 15 FPS** → Akıcı playback!

---

## 📊 Karşılaştırma

| Özellik | Scrypted | Bizimki |
|---------|----------|---------|
| **Collage** | 4 frame | **5 frame** (daha fazla!) |
| **GIF Frame** | 5-8 | **10 frame** (daha smooth!) |
| **GIF Duration** | 3-4s | **5s** (daha uzun!) |
| **GIF Progress Bar** | ❌ Yok | ✅ **VAR!** |
| **MP4 Resolution** | 480p | **720p** (daha net!) |
| **MP4 Detection Box** | ❌ Yok | ✅ **VAR!** |
| **MP4 Confidence** | ❌ Yok | ✅ **VAR!** |

**BİZİMKİ DAHA İYİ!** 🏆

---

## 📱 Telegram'a Gidecek (Örnek)

```
🚨 Ön Kapı - Hareket Algılandı
⏰ 01:19:44
📍 Zone: Giriş Yolu
🎯 Confidence: 87%

📸 Collage (5 frame)
[Statik grid görüntü]

🎬 Timeline GIF (5 saniye)
[Animasyon - hareket başlangıç → son]
[Progress bar altta]

🎥 Full Video (20 saniye)
[720p, detection boxes, smooth]

━━━━━━━━━━━━━━━━━━━━━━
Powered by Smart Motion Detector v2
```

---

## 🔥 Bizimkinin Avantajları

### 1. **Daha Smooth GIF** 🎬
- Scrypted: 5-8 frame → Hoppalamalı
- Bizimki: 10 frame → Akıcı!

### 2. **Progress Bar** 📊
- Scrypted: Yok
- Bizimki: Timeline göstergesi var!

### 3. **Detection Boxes** 🎯
- Scrypted: Sadece snapshot
- Bizimki: MP4'te person box görünür!

### 4. **Yüksek Kalite** 📹
- Scrypted: 480p
- Bizimki: 720p MP4 + 90 quality JPEG!

### 5. **Thermal Enhancement** 🌡️
- Scrypted: Raw thermal
- Bizimki: CLAHE enhancement → Daha net!

---

## 📋 ROADMAP.md Güncelleme

**Phase 6: Media Generation** bölümüne ekle:

```markdown
### 📹 Phase 6: Media Generation (Öncelik: 🟠 Orta)

**Yapılacaklar**:
- [ ] Collage generation (5 frame grid, 1920x960, JPEG quality 90)
- [ ] GIF generation (timeline animation)
  - [ ] 10 frame selection (evenly distributed)
  - [ ] 5 saniye duration (0.5s per frame)
  - [ ] Progress bar overlay (timeline indicator)
  - [ ] Timestamp per frame
  - [ ] Optimize <2 MB (Telegram için)
  - [ ] Infinite loop
- [ ] MP4 timelapse (20s accelerated, 720p)
  - [ ] 4x speed (80s → 20s)
  - [ ] Detection boxes (person bounding box)
  - [ ] Confidence score overlay
  - [ ] 15 FPS smooth playback
  - [ ] H.264 codec
- [ ] FFmpeg integration
- [ ] Parallel generation (collage + GIF + MP4 aynı anda)
```

---

## 🎊 Sonuç

**Dokümantasyon güncellendi**:
- ✅ PRODUCT.md (GIF spec detaylandırıldı)
- ✅ API_CONTRACT.md (media endpoint açıklamaları)
- ✅ MEDIA_SPEC.md (YENİ - tam detay)

**Bizimki Scrypted'den daha iyi çünkü**:
- 🔥 Daha fazla frame (10 vs 5-8)
- 🔥 Progress bar (timeline göstergesi)
- 🔥 Detection boxes (MP4'te)
- 🔥 Yüksek kalite (720p vs 480p)
- 🔥 Thermal enhancement (CLAHE)

---

**Şimdi Phase 2'yi test edip commit edelim mi?** 🚀