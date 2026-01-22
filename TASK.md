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

## Görevler (20 tane)

### 🔴 Acil (1-5)
1. Events sayfası - toplu silme düzelt (Select All üste, checkbox büyüt)
2. Backend - bulk delete API ekle
3. Backend - recordings API kontrol et
4. Frontend - Recordings sayfası yap
5. Frontend - Recordings route ekle

### 🟡 Önemli (6-9)
6-7. MotionTab yap + entegre et
8-9. MediaTab yap + entegre et

### 🟢 Orta (10-18)
10-13. DetectionTab'a 4 alan ekle
14-18. TelegramTab'a 5 alan ekle

### ⚪ Düşük (19-20)
19-20. RecordingTab'a 2 alan ekle

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

## Test

Her görev bitince:
- [ ] Kod çalışıyor
- [ ] Console'da error yok
- [ ] UI responsive
- [ ] Dark theme uyumlu

## Soru?

1. TODO.md bak
2. Benzer component bak
3. Backend model bak (`app/models/config.py`)
4. Sor

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
