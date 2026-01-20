# Zone/ROI UI Specification - Smart Motion Detector v2

Zone çizimi için UI spesifikasyonu (Frigate/Scrypted tarzı)

**Hedef**: Kullanıcı dostu polygon çizimi (tüm sistemlerde standart)

---

## 🎯 Genel Akış

```
1. Kamera seç (dropdown)
   ↓
2. Kamera snapshot görüntüsü gelir (canlı preview)
   ↓
3. Polygon çiz (click ile nokta ekle)
   ↓
4. Zone kaydet (name + mode)
   ↓
5. Zone listesi güncellenir
```

**Tüm sistemlerde böyle çalışır!** (Frigate, Scrypted, Hikvision, Blue Iris)

---

## 📱 UI Layout

```
┌─────────────────────────────────────────────────────┐
│  🎭 ZONES                                           │
│                                                     │
│  Camera: [Ön Kapı ▼] ← Dropdown                    │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │                                             │   │
│  │         [Snapshot Preview]                  │   │
│  │                                             │   │
│  │  ╔═══════════════╗  ← Çizilmiş zone        │   │
│  │  ║   ZONE 1      ║                          │   │
│  │  ║  (Giriş Yolu) ║                          │   │
│  │  ╚═══════════════╝                          │   │
│  │                                             │   │
│  │  [Click to add points]                      │   │
│  │                                             │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  Zone Name: [Giriş Yolu_______]                    │
│  Mode: [Person ▼] (person/motion/both)             │
│                                                     │
│  [Clear] [Undo Last Point] [Save Zone]             │
│                                                     │
│  ─────────────────────────────────────────────────  │
│                                                     │
│  Existing Zones:                                    │
│  ┌─────────────────────────────────────────────┐   │
│  │ ✓ Zone 1: Giriş Yolu (person)      [Edit] [X]│   │
│  │ ✓ Zone 2: Bahçe Sınırı (person)    [Edit] [X]│   │
│  │ ✗ Zone 3: Sokak (ignore)           [Edit] [X]│   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## 🖱️ Polygon Çizim İnteraktif

### Kullanıcı Aksiyonları:

**1. Click**: Nokta ekle
```
Click 1: (100, 100) → İlk nokta
Click 2: (500, 100) → İkinci nokta
Click 3: (500, 400) → Üçüncü nokta
Click 4: (100, 400) → Dördüncü nokta
Double-click: Polygon'u kapat
```

**2. Drag**: Nokta taşı
```
Nokta üzerine gel → Cursor değişir
Drag → Nokta hareket eder
```

**3. Right-click**: Nokta sil
```
Nokta üzerine sağ tık → Nokta silinir
```

**4. Undo**: Son noktayı geri al
```
[Undo Last Point] button
```

**5. Clear**: Tümünü temizle
```
[Clear] button → Baştan başla
```

---

## 🎨 Visual Feedback

### Çizim Sırasında:
```
- Noktalar: Beyaz daire (●)
- Çizgiler: Mavi (#5B8CFF - accent)
- Polygon: Mavi fill (opacity 0.3)
- Aktif nokta: Kırmızı (hover)
- Koordinatlar: Normalized (0.0-1.0)
```

### Kaydedilmiş Zone:
```
- Polygon: Yeşil (#2ECC71 - success)
- Label: Zone adı + mode
- Opacity: 0.2 (şeffaf)
```

### Ignore Zone:
```
- Polygon: Kırmızı (#FF4D4F - error)
- Label: "IGNORE"
- Opacity: 0.2
```

---

## 📋 Zone Types

### 1. **Person Zone** (Alarm ver)
```json
{
  "name": "Giriş Yolu",
  "mode": "person",
  "enabled": true,
  "polygon": [[0.2, 0.3], [0.8, 0.3], [0.8, 0.9], [0.2, 0.9]]
}
```

**Renk**: Yeşil  
**Davranış**: Person algılanınca alarm ver

---

### 2. **Motion Zone** (Pre-filter)
```json
{
  "name": "Geniş Alan",
  "mode": "motion",
  "enabled": true,
  "polygon": [[0.1, 0.2], [0.9, 0.2], [0.9, 0.9], [0.1, 0.9]]
}
```

**Renk**: Mavi  
**Davranış**: Motion varsa YOLOv8 çalıştır

---

### 3. **Ignore Zone** (Motion Mask)
```json
{
  "name": "Sokak",
  "mode": "ignore",
  "enabled": true,
  "polygon": [[0.0, 0.0], [1.0, 0.0], [1.0, 0.3], [0.0, 0.3]]
}
```

**Renk**: Kırmızı  
**Davranış**: Bu alanda hiçbir şey algılama

---

## 🎯 Validation Rules

**Polygon**:
- Min 3 nokta
- Max 20 nokta
- Koordinatlar: 0.0-1.0 (normalized)
- Self-intersection: İzin verilmez

**Zone Name**:
- Min 2 karakter
- Max 50 karakter
- Unique (aynı kamerada)

---

## 💡 Best Practices (Frigate/Scrypted'den)

### 1. **Snapshot Yenileme**
```
Kamera seçilince:
  → Fresh snapshot al (1-2 saniye önce)
  → Eski snapshot gösterme!
```

### 2. **Grid Overlay** (Opsiyonel)
```
3x3 grid çizgileri
→ Kullanıcı daha kolay hizalar
```

### 3. **Zoom** (Opsiyonel)
```
Mouse wheel: Zoom in/out
→ Detaylı çizim için
```

### 4. **Preset Shapes** (Opsiyonel)
```
[Full Frame] [Top Half] [Bottom Half] [Center]
→ Hızlı zone oluşturma
```

---

## 🔧 Implementation (Phase 4+ veya Phase 7)

**Dosyalar**:
```
ui/src/components/ZoneEditor.tsx
  ├─ Canvas element (polygon çizimi)
  ├─ Mouse event handlers
  ├─ Polygon state management
  └─ Save/load zones

ui/src/components/tabs/ZonesTab.tsx
  ├─ Camera select
  ├─ ZoneEditor component
  ├─ Zone list
  └─ CRUD operations
```

**Libraries** (Opsiyonel):
```
npm install react-konva
// Canvas çizimi için
```

---

## 📊 Örnek Zone Konfigürasyonu (Senin İçin)

### Kamera 1: Ön Kapı
```json
{
  "zones": [
    {
      "name": "Giriş Yolu",
      "mode": "person",
      "polygon": [[0.3, 0.4], [0.7, 0.4], [0.7, 0.9], [0.3, 0.9]]
    },
    {
      "name": "Sokak",
      "mode": "ignore",
      "polygon": [[0.0, 0.0], [1.0, 0.0], [1.0, 0.3], [0.0, 0.3]]
    }
  ]
}
```

**Sonuç**: Sadece giriş yolu alarm verir, sokak ignore!

---

## 🎯 Şu Anki Durum

**Zones Tab**: Muhtemelen placeholder (boş)

**Olması gereken**:
1. Kamera seç
2. Snapshot gelir
3. Polygon çiz
4. Kaydet

**Ne zaman yapılacak?**
- Phase 4'te placeholder bırakıldı
- Phase 7 veya sonrası implement edilecek

---

## 📝 NOTA ALINDI!

**ZONE_UI_SPEC.md** oluşturuldu! ✅

**İçerik**:
- UI layout
- Polygon çizim mantığı
- Zone types (person/motion/ignore)
- Validation rules
- Best practices
- Örnek konfigürasyon

---

**Phase 5 bitince zone UI'sını implement ederiz!** 🎯

**Developer hala Phase 5 kodluyor...** ⏳

**Başka soru var mı?** 😊