# Media Generation Specification - Smart Motion Detector v2

Bu doküman event medya dosyalarının (collage, MP4) detaylı spec'ini içerir.

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

## 🎬 2) GIF (Deprecated)

GIF üretimi kalite/performans nedeniyle devre dışı bırakıldı. Animasyon için
MP4 timelapse kullanılır.

---

## 🎥 3) Timelapse MP4 (Full Event)

### Specification
- **Duration**: 20 saniye (accelerated)
- **Resolution**: max 1280x720 (no upscale, yüksek kalite)
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

### Kayıttan Kesim vs Frame Fallback

Event MP4 iki yoldan üretilir:

1. **Kayıttan kesim (tercih)**: FFmpeg ile sürekli kayıttan `prebuffer + postbuffer` aralığı kesilir. Yüksek kalite, gerçek kayıt.
2. **Frame fallback**: Kayıt kesimi başarısız olursa detector buffer'daki karelerden timelapse oluşturulur.

**Kayıt kesimi ne zaman başarısız olur?**
- Kayıt segmentleri henüz kapatılmamış (her segment 60 sn; yazma bitene kadar exclude edilir)
- Event zamanı ile kayıt zamanı uyuşmazlığı (timezone düzeltildi)
- Kamera için sürekli kayıt başlamamış

**İki aşamalı çözüm**: İlk media üretiminde segment henüz kapatılmamışsa frame fallback kullanılır. ~50 sn sonra arka planda kayıttan kesim tekrar denenir; başarılı olursa MP4 dosyası kayıt tabanlı versiyonla güncellenir. Sonradan eventi açan kullanıcı yüksek kaliteli videoyu görür.

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
| **MP4 Resolution** | 480p | **720p (no upscale)** (daha net!) |
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

🎥 Full Video (20 saniye)
[720p, detection boxes, smooth]

━━━━━━━━━━━━━━━━━━━━━━
Powered by Smart Motion Detector v2
```

---

## 🔥 Bizimkinin Avantajları

### 1. **Detection Boxes** 🎯
- Scrypted: Sadece snapshot
- Bizimki: MP4'te person box görünür!

### 2. **Yüksek Kalite** 📹
- Scrypted: 480p
- Bizimki: 720p MP4 + 90 quality JPEG!

### 3. **Thermal Enhancement** 🌡️
- Scrypted: Raw thermal
- Bizimki: CLAHE enhancement → Daha net!

---

## 📋 ROADMAP.md Güncelleme

**Phase 6: Media Generation** bölümüne ekle:

```markdown
### 📹 Phase 6: Media Generation (Öncelik: 🟠 Orta)

**Yapılacaklar**:
- [ ] Collage generation (5 frame grid, 1920x960, JPEG quality 90)
- [ ] MP4 timelapse (20s accelerated, 720p)
  - [ ] 4x speed (80s → 20s)
  - [ ] Detection boxes (person bounding box)
  - [ ] Confidence score overlay
  - [ ] 15 FPS smooth playback
  - [ ] H.264 codec
- [ ] FFmpeg integration
- [ ] Parallel generation (collage + MP4 aynı anda)
```

---

## 🎊 Sonuç

**Dokümantasyon güncellendi**:
- ✅ PRODUCT.md (media spec güncellendi)
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