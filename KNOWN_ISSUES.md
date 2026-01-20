# Known Issues & Future Improvements

Bu dosya bilinen sorunları ve gelecek iyileştirmeleri listeler.

**Son Güncelleme**: 2026-01-20

---

## 🔴 Kritik (Düzeltilmeli)

### 1. **Recording vs Event Media Karışıklığı**

**Sorun**:
```json
{
  "record": { ... },  // Continuous recording
  "media": { ... }    // Event media
}
```

İki farklı kavram ama isimlendirme net değil:
- `record`: 7/24 continuous recording (kapalı olmalı)
- `media`: Event media retention (her zaman açık)

**Kullanıcı karışıyor**: "Recording kapalı ama hareket kayıtları nasıl oluşuyor?"

**Çözüm Önerileri**:

**A) Config Yeniden Yapılandır** (Breaking Change):
```json
{
  "continuous_recording": {
    "enabled": false,
    "retention_days": 7
  },
  "event_media": {
    "retention_days": 7,
    "cleanup_interval_hours": 24
  }
}
```

**B) UI'da Açıklama Ekle** (Kolay):
```
Recording Tab:
  ━━━ Continuous Recording (7/24) ━━━
  [ ] Enable (NOT RECOMMENDED - NVR already does this)
  
  ━━━ Event Media (Person Detections) ━━━
  [✓] Enabled (Always On)
  ℹ️ Collage/GIF/MP4 automatically saved
```

**C) Dokümantasyonu Netleştir**:
- PRODUCT.md'ye açıklama ekle
- API_CONTRACT.md'de net ayır

**Öncelik**: Orta  
**Etki**: Kullanıcı deneyimi  
**Önerilen Çözüm**: B (UI açıklama) + C (doküman)

---

### 2. **Kamera Ekleme UI'sı Eksik**

**Sorun**:
- Cameras tab var
- Camera test formu var
- Ama kamera ekleme/listeleme/düzenleme/silme UI'sı yok!

**Eksik**:
- Camera list (kayıtlı kameralar)
- Add camera button
- Edit camera modal
- Delete camera button
- Camera CRUD operations (POST/PUT/DELETE /api/cameras)

**Çözüm**:
Phase 4'e eklenecek (Camera CRUD UI)

**Öncelik**: Yüksek  
**Etki**: Kullanıcı kamera ekleyemiyor  
**Tahmini**: 1-2 gün

---

## 🟡 Orta (İyileştirme)

### 3. **UI Dili İngilizce**

**Sorun**:
DESIGN_SYSTEM.md: "Dil: TR/EN (şimdilik TR)"  
Ama UI İngilizce: "Settings", "Camera Type", "Test Connection"

**Çözüm**:
- A) Şimdi Türkçe'ye çevir (5 dakika)
- B) i18n ekle (TR/EN switch) (1 gün)
- C) İngilizce kalsın, dokümanı güncelle

**Öncelik**: Düşük  
**Etki**: Kullanıcı deneyimi  
**Önerilen**: B (i18n) - Phase 8+

---

### 4. **Zone UI Eksik**

**Sorun**:
- Zones tab var (placeholder)
- Ama polygon çizimi yok!

**Eksik**:
- Camera select
- Snapshot preview
- Polygon drawing (canvas)
- Zone list
- CRUD operations

**Çözüm**:
Phase 7 veya sonrası (Zone Editor UI)

**Öncelik**: Orta  
**Etki**: Zone manuel DB'ye eklenmeli (şimdilik)  
**Tahmini**: 2-3 gün

---

### 5. **Sidebar Navigation Yok**

**Sorun**:
Sadece Settings sayfası var.  
Dashboard, Live, Events, Diagnostics sayfaları yok.

**Eksik**:
- Sidebar menu
- Dashboard page
- Live view page
- Events page
- Diagnostics page

**Çözüm**:
Phase 8-9 (Frontend pages)

**Öncelik**: Orta  
**Etki**: Sadece Settings kullanılabilir  
**Tahmini**: 3-4 gün

---

## 🟢 Düşük (Gelecek)

### 6. **Theme Selector Yok**

**Sorun**:
Sadece 1 tema var (Frigate - mavi accent).  
Kullanıcı tema seçemiyor.

**İstenilen**:
```
Settings → Appearance Tab:
  Theme:
  ○ Slate Professional (Yeşil) ⭐
  ○ Carbon Dark (Turkuaz)
  ○ Pure Black (Kırmızı)
  ○ Matrix (Neon Yeşil)
  
  [Preview] [Save]
```

**Çözüm**:
Phase 14 (Theme Selector)

**Dosyalar**:
- Config'e `appearance.theme` field
- UI'da Appearance tab
- Theme switcher (Tailwind config)
- 4 tema: slate, carbon, pure-black, matrix

**Öncelik**: Düşük  
**Etki**: Kullanıcı deneyimi (görsel)  
**Tahmini**: 1-2 saat

---

### 7. **AI Prompt Test Butonu Yok**

**Sorun**:
AI prompt ayarlıyorsun ama test edemiyorsun.

**İstenilen**:
```
AI Tab:
  Custom Prompt: [...]
  [Preview AI Response] ← Test butonu
  
  Response:
  "1 kişi, ön kapıda, normal davranış..."
```

**Çözüm**: Phase 11 (AI Integration)

**Öncelik**: Düşük  
**Tahmini**: 1 saat

---

### 8. **Telegram Test Butonu Eksik**

**Sorun**:
Telegram ayarları var ama test butonu yok.

**İstenilen**:
```
Telegram Tab:
  Bot Token: [...]
  Chat IDs: [...]
  [Test Connection] ← Butonu var ama backend endpoint yok!
```

**Çözüm**: Phase 12 (Telegram Integration)

**Öncelik**: Düşük  
**Tahmini**: 30 dakika

---

### 9. **Model Download Progress Yok**

**Sorun**:
YOLOv8 model ilk kez indirilirken kullanıcı görmüyor.

**İstenilen**:
```
Diagnostics page:
  Model Status:
  ⏳ Downloading yolov8n-person.pt (45%)
  ✅ Model ready
```

**Çözüm**: Phase 13 (Diagnostics)

**Öncelik**: Düşük  
**Tahmini**: 1 saat

---

## 📋 Öncelik Sırası (Düzeltme İçin)

### Hemen (Bugün):
1. ❌ Yok (Phase 6'ya devam)

### Yarın:
2. 🔴 Kamera CRUD UI (Phase 4 tamamla)
3. 🟡 Recording vs Event Media açıklama (UI + doküman)

### Bu Hafta:
4. 🟡 Zone UI (Phase 7)
5. 🟡 Sidebar + Dashboard (Phase 8)

### Gelecek:
6. 🟢 UI Türkçe (i18n)
7. 🟢 AI/Telegram test butonları
8. 🟢 Model download progress

---

## 🎯 Şu An Ne Yapalım?

**Önerim**: 
1. **Phase 6'yı bitir** (Media generation test et)
2. **Commit et**
3. **Bugünlük yeter** (7 saat çalıştık!)
4. **Yarın**: Kamera CRUD UI + Recording açıklama

**Yoksa devam mı?**

**Söyle!** 😊

**Developer Phase 6 bitirdi, test ediyoruz!** ⏳
