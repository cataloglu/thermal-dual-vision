# Post-MVP Roadmap - Smart Motion Detector v2

MVP (Phase 1-13) tamamlandıktan sonra yapılacak iyileştirmeler.

**Başlangıç**: MVP bitince (Phase 13 sonrası)

---

## 🔴 Phase 14: Kritik Düzeltmeler (ÖNCE BU!)

**Hedef**: MVP'deki kritik eksikleri gider, sistem production-ready olsun

**Tahmini Süre**: 1-2 gün

---

### 1. **Kamera CRUD UI** (En Kritik!)

**Sorun**: Kamera test edebiliyoruz ama ekleyemiyoruz!

**Backend** (zaten var):
- ✅ POST /api/cameras (endpoint hazır ama servis yok)
- ✅ PUT /api/cameras/{id}
- ✅ DELETE /api/cameras/{id}
- ✅ GET /api/cameras

**Frontend** (eksik):
- [ ] Camera list component
- [ ] Add camera form
- [ ] Edit camera modal
- [ ] Delete confirmation
- [ ] Zone management per camera

**Dosyalar**:
```
app/services/camera_crud.py (yeni)
ui/src/components/CameraList.tsx (yeni)
ui/src/components/CameraForm.tsx (yeni - şu an sadece test var)
ui/src/components/CameraEditModal.tsx (yeni)
```

**Öncelik**: 🔴 KRİTİK  
**Tahmini**: 3-4 saat

---

### 2. **Recording vs Event Media Açıklama**

**Sorun**: Kullanıcı "Recording kapalı ama event'ler nasıl kaydediliyor?" diye karışıyor.

**Çözüm**:

**A) UI'da Açıklama Ekle**:
```tsx
// Recording Tab
<div className="bg-surface2 border border-warning p-4 rounded-lg mb-6">
  ⚠️ NOT: İki farklı kayıt türü var!
  
  1. Continuous Recording (7/24):
     - Her şeyi kaydeder (person olsun olmasın)
     - ❌ KAPALI (NVR zaten yapıyor!)
     - Çok disk kullanır
  
  2. Event Recording (Person algılandığında):
     - Sadece hareket kayıtları (collage/GIF/MP4)
     - ✅ AÇIK (her zaman)
     - Az disk kullanır
</div>
```

**B) Config İsimlendirmesi** (opsiyonel):
```json
{
  "continuous_recording": { "enabled": false },
  "event_media": { "retention_days": 7 }
}
```

**Öncelik**: 🟡 Orta  
**Tahmini**: 30 dakika

---

### 3. **UI Metinleri Türkçe'ye Çevir**

**Sorun**: 
- Sidebar: Türkçe ✅ (Dashboard, Canlı Görüntü, Olaylar)
- Settings sayfası: İngilizce ❌ (Camera Type, Test Connection)

**Çözüm**:
```tsx
// Settings tabs
"Camera Type" → "Kamera Tipi"
"Test Connection" → "Bağlantıyı Test Et"
"Snapshot" → "Görüntü"
"Latency" → "Gecikme"
"Save Settings" → "Ayarları Kaydet"

// Tüm tab içerikleri
Detection → Algılama
Thermal → Termal
Stream → Yayın
etc...
```

**Dosyalar**:
```
ui/src/components/tabs/*.tsx (10 dosya)
ui/src/components/CameraTestForm.tsx
```

**Öncelik**: 🟡 Orta  
**Tahmini**: 1-2 saat

---

### 4. **AI/Telegram Test Butonları (Backend)**

**Sorun**: UI'da buton var ama backend endpoint eksik!

**Eksik Endpoint'ler**:
```
POST /api/telegram/test (Phase 12'de yapılacak zaten!)
POST /api/ai/test (yeni)
```

**AI Test**:
```python
@app.post("/api/ai/test")
def test_ai(image_base64: str):
    # OpenAI'a test resmi gönder
    # Response döndür
    return {"summary": "Test başarılı: 1 kişi..."}
```

**Öncelik**: 🟢 Düşük  
**Tahmini**: 30 dakika

---

## 🟢 Phase 15: Opsiyonel İyileştirmeler (SONRA)

**Hedef**: Nice-to-have özellikler, zorunlu değil

**Tahmini Süre**: 2-3 gün

---

### 1. **Theme Selector** (En İstenen!)

**4 Tema**:
- Slate Professional (Yeşil) ⭐
- Carbon Dark (Turkuaz)
- Pure Black (Kırmızı)
- Matrix (Neon Yeşil)

**Implementation**:
```
Config:
{
  "appearance": {
    "theme": "slate",  // slate | carbon | pure-black | matrix
    "language": "tr"
  }
}

UI:
Settings → Appearance Tab
  Theme: [Slate ▼]
  Language: [Türkçe ▼]
  [Preview] [Save]
```

**Dosyalar**:
```
app/models/config.py (appearance section)
ui/src/components/tabs/AppearanceTab.tsx (yeni)
ui/tailwind.config.js (dinamik renkler)
ui/src/themes/ (4 tema dosyası)
```

**Öncelik**: 🟢 Düşük  
**Tahmini**: 2-3 saat

---

### 2. **Zone UI (Polygon Çizimi)**

**Implementation**:
```
ui/src/components/ZoneEditor.tsx:
  - Canvas element
  - Mouse events (click, drag, delete)
  - Polygon state
  - Save/load zones

ui/src/components/tabs/ZonesTab.tsx:
  - Camera select
  - Snapshot preview
  - ZoneEditor component
  - Zone list (CRUD)
```

**Library**:
```
npm install react-konva (opsiyonel)
```

**Öncelik**: 🟢 Düşük  
**Tahmini**: 3-4 saat

---

### 3. **i18n (TR/EN Switch)**

**Implementation**:
```
npm install react-i18next

Config:
{
  "appearance": {
    "language": "tr"  // tr | en
  }
}

UI:
Settings → Appearance
  Language: [Türkçe ▼]
    - Türkçe
    - English
```

**Dosyalar**:
```
ui/src/i18n/tr.json (Türkçe çeviriler)
ui/src/i18n/en.json (İngilizce çeviriler)
ui/src/i18n/index.ts (i18n setup)
```

**Öncelik**: 🟢 Düşük  
**Tahmini**: 2-3 saat

---

### 4. **Model Download Progress Indicator**

**Implementation**:
```
Diagnostics page:
  Model Status:
  ⏳ Downloading yolov8n-person.pt (45%)
  ✅ Model ready (123 MB)
```

**Backend**:
```python
# app/workers/detector.py
def download_model_with_progress(model_name):
    # Progress callback
    # Broadcast via WebSocket
    pass
```

**Öncelik**: 🟢 Düşük  
**Tahmini**: 1 saat

---

### 5. **Advanced Features** (Post-MVP)

**Thermal Signature Validation**:
```python
# 30-40°C = insan
# 55°C = araba → ignore
```

**Multi-Camera Correlation**:
```python
# Aynı kişi 3 kamerada → yüksek tehdit
```

**Motion Trail Analysis**:
```python
# Loitering detection
# Threat level scoring
```

**Öncelik**: 🟢 Çok Düşük  
**Tahmini**: 5-10 gün

---

## 📊 Öncelik Sırası

### Hemen (Phase 14 - Kritik):
1. 🔴 Kamera CRUD UI (3-4 saat)
2. 🟡 Recording açıklama (30 dk)
3. 🟡 UI Türkçe (1-2 saat)
4. 🟢 Test butonları (30 dk)

**Toplam**: ~1 gün

### Sonra (Phase 15 - Opsiyonel):
5. 🟢 Theme selector (2-3 saat)
6. 🟢 Zone UI (3-4 saat)
7. 🟢 i18n (2-3 saat)
8. 🟢 Model progress (1 saat)

**Toplam**: ~2-3 gün

---

## 🎯 Özet

**Phase 14**: Kritik düzeltmeler (zorunlu)  
**Phase 15**: İyileştirmeler (opsiyonel)

**MVP bitince**: Önce Phase 14, sonra Phase 15

---

**Bu dosya kaydedildi**: POST_MVP_ROADMAP.md
