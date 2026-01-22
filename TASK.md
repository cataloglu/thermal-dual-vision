# 🎯 GÖREV: Smart Motion Detector - Eksik Özellikler

## Ne Yapacaksın?
Thermal kamera projesi var, çalışıyor ama bazı ayarlar/sayfalar eksik. Backend'de var, frontend'de yok. Sen frontend + 2 backend endpoint ekleyeceksin.

## Dosyalar
- **TODO.md** - 20 görev detaylı (hangi satır, ne yapılacak, kod örneği)
- **DEV_PROMPT.md** - Teknik detaylar (pattern'ler, kurallar, örnekler)
- **Proje:** `thermal-dual-vision/`

## Stack
- **Backend:** Python + FastAPI
- **Frontend:** React + TypeScript + Tailwind

## Görevler (23 tane)

1. Events toplu silme düzelt
2. Backend bulk delete API
3. Backend recordings API kontrol
4. Recordings sayfası
5. Recordings route
6. MotionTab yap
7. MotionTab entegre et
8. MediaTab yap
9. MediaTab entegre et
10. DetectionConfig type güncelle
11. DetectionTab inference_resolution
12. DetectionTab aspect_ratio
13. DetectionTab enable_tracking
14. TelegramTab rate_limit_seconds
15. TelegramTab video_speed
16. TelegramTab event_types
17. TelegramTab cooldown_seconds
18. TelegramTab max_messages_per_min
19. RecordingTab cleanup_policy
20. RecordingTab delete_order
21. Backend startup delay (10 saniye)
22. Settings Export/Import kaldır, Reset ekle
23. Varsayılan tema pure-black yap

**Detaylar:** TODO.md'de her görev için kod örneği var

## Nasıl Başlayacaksın?

### 1. Projeyi Aç
```bash
cd thermal-dual-vision
```

### 2. TODO.md'yi Oku
Her görevde:
- Hangi dosya
- Hangi satır
- Ne sorunu var
- Ne yapılacak
- Kod örneği

### 3. Mevcut Kodu İncele
Yeni bir şey yapacaksan, benzerini bul, kopyala, düzenle.

**Örnek:**
- Tab yapacaksan → `ui/src/components/tabs/RecordingTab.tsx` bak
- Sayfa yapacaksan → `ui/src/pages/Events.tsx` bak
- API ekleyeceksen → `app/main.py` bak

### 4. Pattern'leri Takip Et

**Backend Endpoint:**
```python
@app.post("/api/events/bulk-delete")
async def bulk_delete_events(request: BulkDeleteRequest):
    try:
        # logic
        return {"deleted_count": 10}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Frontend Tab:**
```typescript
export const MotionTab: React.FC<MotionTabProps> = ({ config, onChange, onSave }) => {
  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-text mb-2">
          Sensitivity
        </label>
        <input
          type="range"
          value={config.sensitivity}
          onChange={(e) => onChange({ ...config, sensitivity: parseInt(e.target.value) })}
          className="w-full"
        />
      </div>
      <button onClick={onSave} className="px-4 py-2 bg-accent text-white rounded-lg">
        Save
      </button>
    </div>
  )
}
```

**Tailwind Classes (kopyala yapıştır):**
```typescript
// Input
"w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"

// Button
"px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"

// Checkbox
"w-4 h-4 text-accent bg-surface2 border-border rounded focus:ring-accent"
```

## Kurallar

### ❌ Yapma
- Mevcut kodu bozma
- `any` kullanma (TypeScript)
- Inline style yazma (Tailwind kullan)
- console.log bırakma

### ✅ Yap
- Mevcut pattern'leri kopyala
- Error handling ekle
- Loading state göster
- Toast notification ver (başarı/hata)

## ⚠️ ÖNEMLİ: HER GÖREV İÇİN ZORUNLU

### 1. Görevi Yap
### 2. TEST ET (atla geçme!)
### 3. Console'a bak (F12)
### 4. Çalışıyor mu? ✅ Sonraki göreve geç / ❌ Düzelt

## Test Nasıl Yapılır?

```bash
# Frontend başlat
cd ui
npm run dev

# Tarayıcıda aç
http://localhost:5173

# Yaptığın özelliği test et
# Örnek: MotionTab yaptıysan
# → Settings > Motion > Değerleri değiştir > Save > F5 yenile > Değerler kaldı mı?

# Console'a bak (F12 > Console)
# Error var mı? ❌ Varsa düzelt, ✅ Yoksa sonraki göreve geç
```

## 🚨 Hata Alırsan Ne Yapacaksın?

### "Type 'MotionConfig' not found"
→ `ui/src/types/api.ts` açmadın, type'ı ekle

### "Cannot find module './MotionTab'"
→ Import path yanlış, `../components/tabs/MotionTab` olacak

### "config.motion is undefined"
→ Settings.tsx'de case eklememiş olabilirsin

### Console'da kırmızı error var
→ F12 bas, Console tab'ına bak, error'u oku, TODO.md'de ara

### Sayfa yenileyince değerler kayboldu
→ Save fonksiyonu çalışmıyor, api.ts'ye bak

## Soru?

1. TODO.md bak
2. Benzer component bak
3. Backend model bak (`app/models/config.py`)
4. Console'a bak (F12)
5. Sor

## Örnek: MotionTab Yapma (Görev 6)

### 1. Dosya Oluştur
`ui/src/components/tabs/MotionTab.tsx`

### 2. RecordingTab'ı Kopyala
```bash
cp ui/src/components/tabs/RecordingTab.tsx ui/src/components/tabs/MotionTab.tsx
```

### 3. İçini Düzenle
- `RecordingTab` → `MotionTab` değiştir
- `RecordConfig` → `MotionConfig` değiştir
- Input'ları değiştir:
  - sensitivity (slider 1-10)
  - min_area (input number)
  - cooldown_seconds (input number)
  - presets (dropdown)

### 4. Settings.tsx'e Ekle
```typescript
// Import
import { MotionTab } from '../components/tabs/MotionTab';

// Case ekle (satır 70)
case 'motion': updates.motion = localSettings.motion;

// Render ekle (satır 164)
if (activeTab === 'motion' && localSettings) {
  return <MotionTab 
    config={localSettings.motion} 
    onChange={(motion) => updateLocalSettings({ ...localSettings, motion })} 
    onSave={handleSave} 
  />
}
```

### 5. Sidebar'a Ekle
`ui/src/components/Sidebar.tsx` satır 54:
```typescript
{ tab: 'motion', label: t('motion') }
```

### 6. Test
- Settings'e git
- Motion tab'ı aç
- Değerleri değiştir
- Save bas
- Sayfa yenile
- Değerler kaldı mı?

## Bitti mi?

20/20 görev tamamlandı mı?
- [ ] Events toplu silme çalışıyor
- [ ] Recordings sayfası var
- [ ] MotionTab var
- [ ] MediaTab var
- [ ] DetectionTab tam
- [ ] TelegramTab tam
- [ ] RecordingTab tam
- [ ] Console'da error yok

---

**Başarılar! 🚀**

*Takıldığın yer olursa TODO.md'ye bak, orada her şey var.*
