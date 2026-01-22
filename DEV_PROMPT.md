# 🚀 DEVELOPER TASK PROMPT

## 📋 PROJE: Smart Motion Detector v2 - Frontend/Backend Tamamlama

### 🎯 GÖREV ÖZETİ
Thermal kamera tabanlı hareket algılama sisteminin eksik UI/API özelliklerini tamamla. Backend'de 2 endpoint, Frontend'de 3 yeni sayfa/tab + 15 form alanı eklenecek.

---

## 📁 PROJE YAPISI
```
thermal-dual-vision/
├── app/                    # Python FastAPI backend
│   ├── main.py            # API endpoints
│   ├── models/config.py   # Pydantic config models
│   └── services/          # Business logic
├── ui/                    # React TypeScript frontend
│   ├── src/
│   │   ├── pages/         # Ana sayfalar (Dashboard, Events, Live, Settings)
│   │   ├── components/
│   │   │   └── tabs/      # Settings tab'ları (AITab, CamerasTab, DetectionTab...)
│   │   ├── types/api.ts   # TypeScript type definitions
│   │   └── services/api.ts # API client
│   └── ...
├── data/config.json       # Runtime config
└── TODO.md               # Detaylı görev listesi (20 görev)
```

---

## 🔥 ÖNCELİK SIRASI (Önerilen)

### PHASE 1: KRİTİK KULLANICI SORUNLARI (1-5)
**Amaç:** Kullanıcının şu an yaşadığı acil sorunları çöz

1. **Events Toplu Silme İyileştirme** (Frontend)
   - Select All butonu header'a taşı
   - Checkbox 6x6px yap
   - Delete All By Filter butonu ekle

2. **Events Bulk Delete API** (Backend)
   - `POST /api/events/bulk-delete` endpoint
   - Tek istekle çoklu event silme

3. **Recordings API Kontrol** (Backend)
   - Mevcut API'leri kontrol et
   - Eksikleri tamamla

4. **Recordings Sayfası** (Frontend)
   - Kayıt listesi UI
   - Filtreler, izle/sil/indir

5. **Recordings Route** (Frontend)
   - Sidebar link + routing

---

### PHASE 2: EKSİK AYARLAR (6-9)
**Amaç:** Backend'de var ama UI'da olmayan config'leri ekle

6. **MotionTab Oluştur** (Frontend)
   - sensitivity, min_area, cooldown, presets

7. **MotionTab Entegre Et** (Frontend)
   - Settings.tsx + Sidebar

8. **MediaTab Oluştur** (Frontend)
   - retention_days, cleanup_interval, disk_limit

9. **MediaTab Entegre Et** (Frontend)
   - Settings.tsx + Sidebar

---

### PHASE 3: DETECTION İYİLEŞTİRMELERİ (10-13)
**Amaç:** YOLO detection parametrelerini UI'dan ayarlanabilir yap

10. **DetectionConfig Type Güncelle** (Frontend)
    - aspect_ratio_min/max ekle

11. **Inference Resolution Input** (Frontend)
    - Width/height input alanları

12. **Aspect Ratio Slider** (Frontend)
    - Min/max slider'lar

13. **Enable Tracking Checkbox** (Frontend)
    - Gelecek özellik için hazırlık

---

### PHASE 4: TELEGRAM GELİŞMİŞ AYARLAR (14-18)
**Amaç:** Telegram bildirim kontrolünü detaylandır

14. **Rate Limit Input** (Frontend)
15. **Video Speed Slider** (Frontend)
16. **Event Types Multi-Select** (Frontend)
17. **Cooldown Input** (Frontend)
18. **Max Messages Per Min Input** (Frontend)

---

### PHASE 5: RECORDING POLİTİKALARI (19-20)
**Amaç:** Disk dolunca ne silineceğini ayarla

19. **Cleanup Policy Dropdown** (Frontend)
20. **Delete Order Sortable List** (Frontend)

---

## 🛠️ TEKNİK DETAYLAR

### Backend (Python 3.11 + FastAPI)
- **Config Models:** `app/models/config.py` (Pydantic BaseModel)
- **API Endpoints:** `app/main.py` (FastAPI router)
- **Validation:** Pydantic validators kullan
- **Error Handling:** HTTPException ile standart error response

### Frontend (React 18 + TypeScript + Vite)
- **Styling:** Tailwind CSS (dark theme)
- **State:** useState + useCallback
- **API Calls:** `services/api.ts` (fetch wrapper)
- **Types:** `types/api.ts` (backend ile sync)
- **Routing:** React Router v6
- **Icons:** react-icons/md

### Kod Standartları
- **TypeScript:** Strict mode, no any
- **React:** Functional components, hooks
- **CSS:** Tailwind utility classes
- **Naming:** camelCase (JS/TS), snake_case (Python)
- **Imports:** Absolute paths, group by type

---

## 📖 ÖRNEK KOD PATTERN'LERİ

### Backend Endpoint Örneği
```python
@app.post("/api/events/bulk-delete")
async def bulk_delete_events(request: BulkDeleteRequest):
    """Delete multiple events in one request."""
    try:
        deleted = []
        failed = []
        for event_id in request.event_ids:
            try:
                # Delete logic
                deleted.append(event_id)
            except Exception as e:
                failed.append({"id": event_id, "error": str(e)})
        
        return {
            "deleted_count": len(deleted),
            "failed_ids": failed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Frontend Tab Component Örneği
```typescript
interface MotionTabProps {
  config: MotionConfig
  onChange: (config: MotionConfig) => void
  onSave: () => void
}

export const MotionTab: React.FC<MotionTabProps> = ({ config, onChange, onSave }) => {
  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-text mb-2">
          Sensitivity (1-10)
        </label>
        <input
          type="range"
          min="1"
          max="10"
          value={config.sensitivity}
          onChange={(e) => onChange({ ...config, sensitivity: parseInt(e.target.value) })}
          className="w-full"
        />
        <span className="text-muted text-sm">{config.sensitivity}</span>
      </div>
      
      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90"
      >
        Save
      </button>
    </div>
  )
}
```

---

## 🎨 UI/UX KURALLARI

### Tailwind Class Pattern
```typescript
// Input field
"w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"

// Button (primary)
"px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"

// Button (secondary)
"px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors"

// Slider
"w-full h-2 bg-surface2 rounded-lg appearance-none cursor-pointer accent-accent"

// Checkbox
"w-4 h-4 text-accent bg-surface2 border-border rounded focus:ring-accent"
```

### Form Layout Pattern
```typescript
<div className="space-y-4">
  <div>
    <label className="block text-sm font-medium text-text mb-2">
      Field Label
    </label>
    <input ... />
    <p className="text-xs text-muted mt-1">Helper text</p>
  </div>
</div>
```

---

## ✅ KABUL KRİTERLERİ

### Her Görev İçin:
- [ ] Kod çalışıyor (no errors)
- [ ] TypeScript type'lar doğru
- [ ] Backend validation var (Pydantic)
- [ ] UI responsive (mobile/desktop)
- [ ] Dark theme uyumlu
- [ ] Mevcut kod style'ına uygun
- [ ] Console'da error/warning yok

### Test Checklist:
- [ ] Config kaydet/yükle çalışıyor
- [ ] Form validation çalışıyor
- [ ] API error handling çalışıyor
- [ ] UI feedback var (loading, success, error)

---

## 📚 REFERANS DOSYALAR

**Mutlaka İncele:**
1. `TODO.md` - Detaylı görev listesi (satır numaraları, kod örnekleri)
2. `ui/src/components/tabs/RecordingTab.tsx` - Tab component örneği
3. `ui/src/pages/Events.tsx` - Sayfa component örneği
4. `app/models/config.py` - Backend config modelleri
5. `ui/src/types/api.ts` - Frontend type definitions

**Opsiyonel:**
- `docs/API_CONTRACT.md` - API dokümantasyonu
- `docs/DESIGN_SYSTEM.md` - UI component guide

---

## 🚨 DİKKAT EDİLECEKLER

### ❌ YAPMA:
- Mevcut çalışan kodu bozma
- Type'ları `any` yapma
- Inline style kullanma (Tailwind kullan)
- Console.log bırakma
- Hard-coded değerler (config'den al)

### ✅ YAP:
- Mevcut pattern'leri takip et
- Error handling ekle
- Loading state'leri göster
- User feedback ver (toast, modal)
- Code reuse yap (DRY principle)

---

## 💬 SORULAR?

**Eğer bir şey belirsizse:**
1. Önce `TODO.md` dosyasına bak (detaylı açıklamalar var)
2. Benzer mevcut component'lere bak (pattern'leri kopyala)
3. Backend model'e bak (field name'ler, validation'lar)
4. Soru sor (belirsizlikte kod yazma)

---

## 🎯 BAŞARILI TAMAMLAMA

**Tüm görevler bitince:**
- [ ] 20/20 görev tamamlandı
- [ ] Tüm testler geçti
- [ ] UI'da tüm config'ler ayarlanabiliyor
- [ ] Backend'deki tüm field'ler frontend'de var
- [ ] Kayıt sistemi çalışıyor
- [ ] Events toplu silme çalışıyor
- [ ] No console errors
- [ ] Production ready

---

**İyi çalışmalar! 🚀**

*Not: Görevleri tamamladıkça TODO.md'deki ilgili satırları işaretle veya sil.*
