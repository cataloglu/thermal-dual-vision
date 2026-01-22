# TODO LİSTESİ - 20 GÖREV

## 1. Events: Select All butonunu header'a taşı, checkbox büyüt, Delete All By Filter ekle
**Dosya:** `ui/src/pages/Events.tsx`
**Sorun:** 
- Select All butonu pagination'da (satır 432-443), sayfa altında gizli kalıyor
- Checkbox çok küçük (4x4px, satır 108), fark edilmiyor
- 1000 event varsa sayfa sayfa seçmek gerekiyor, hepsi birden seçilemiyor
**Yapılacak:**
- Select All butonunu header'a taşı (satır 240 civarı, Delete butonunun yanına)
- Checkbox'ı 6x6px yap (satır 108: `className="w-6 h-6 accent-accent"`)
- "Delete All By Filter" butonu ekle (mevcut filtreye uyan tüm event'leri sil)

---

## 2. Backend: POST /api/events/bulk-delete endpoint'i ekle
**Dosya:** `app/main.py`
**Sorun:**
- Şu an her event tek tek siliniyor (Events.tsx satır 145: `Promise.all(ids.map(...))`)
- 1000 event silmek için 1000 HTTP isteği atılıyor, çok yavaş
**Yapılacak:**
- Yeni endpoint: `POST /api/events/bulk-delete`
- Body: `{"event_ids": ["id1", "id2", ...]}`
- Response: `{"deleted_count": 123, "failed_ids": []}`
- Frontend'de api.ts'ye `bulkDeleteEvents(ids: string[])` fonksiyonu ekle

---

## 3. Backend: /api/recordings endpoints kontrol et
**Dosya:** `app/main.py`
**Sorun:**
- Kayıt sistemi var ama kayıtları listeleyecek/izleyecek API yok
- StreamViewer'da kayıt başlat/durdur var (satır 157-168) ama kayıtlar nerede?
**Kontrol edilecek:**
- `GET /api/recordings?camera_id=xxx&start_date=xxx&end_date=xxx` var mı?
- `GET /api/recordings/{recording_id}/stream` var mı?
- `DELETE /api/recordings/{recording_id}` var mı?
- Yoksa ekle, varsa frontend'e bağla

---

## 4. Frontend: Recordings.tsx sayfası oluştur
**Dosya:** `ui/src/pages/Recordings.tsx` (yeni dosya)
**Sorun:**
- Kayıtları görecek sayfa hiç yok
- Kullanıcı kayıt yaptı ama nerede olduğunu bilmiyor
**Yapılacak:**
- Kamera dropdown filtresi
- Tarih aralığı filtresi (start_date, end_date)
- Kayıt listesi (thumbnail, süre, boyut, tarih)
- İzle butonu (modal'da video player)
- Sil butonu (onay ile)
- İndir butonu (download link)
- Pagination (Events.tsx'teki gibi)

---

## 5. Frontend: Recordings route ekle
**Dosyalar:** 
- `ui/src/components/Sidebar.tsx` (satır 40-45)
- `ui/src/App.tsx`
**Sorun:**
- Sidebar'da Recordings linki yok
- Route tanımlı değil
**Yapılacak:**
- Sidebar.tsx satır 44'e ekle: `{ path: '/recordings', icon: MdVideoLibrary, label: t('recordings') }`
- App.tsx'e route ekle: `<Route path="/recordings" element={<Recordings />} />`
- MdVideoLibrary icon'u import et: `import { MdVideoLibrary } from 'react-icons/md'`

---

## 6. Frontend: MotionTab.tsx oluştur
**Dosya:** `ui/src/components/tabs/MotionTab.tsx` (yeni dosya)
**Sorun:**
- Backend'de MotionConfig var (app/models/config.py satır 86-114)
- Frontend'de type var (ui/src/types/api.ts satır 14-25)
- Ama tab yok, kullanıcı ayarlayamıyor
**Yapılacak:**
- sensitivity: slider (1-10, default 7)
- min_area: input number (default 500)
- cooldown_seconds: input number (default 5)
- presets: dropdown (thermal_recommended, color_recommended, custom)
- Preset seçince otomatik doldursun
- RecordingTab.tsx'i örnek al (benzer yapı)

---

## 7. Frontend: MotionTab'ı Settings.tsx'e ekle
**Dosya:** `ui/src/pages/Settings.tsx`
**Sorun:**
- MotionTab var ama Settings'e entegre değil
**Yapılacak:**
- Satır 15'e import ekle: `import { MotionTab } from '../components/tabs/MotionTab';`
- Satır 70'e case ekle: `case 'motion': updates.motion = localSettings.motion;`
- Satır 164'e render ekle:
```typescript
if (activeTab === 'motion' && localSettings) {
  return <MotionTab config={localSettings.motion} onChange={(motion) => updateLocalSettings({ ...localSettings, motion })} onSave={handleSave} />
}
```
- Sidebar.tsx satır 54'e ekle: `{ tab: 'motion', label: t('motion') }`

---

## 8. Frontend: MediaTab.tsx oluştur
**Dosya:** `ui/src/components/tabs/MediaTab.tsx` (yeni dosya)
**Sorun:**
- Backend'de MediaConfig var (app/models/config.py satır 261-279)
- Frontend'de type var (ui/src/types/api.ts satır 66-70)
- Ama tab yok, disk yönetimi ayarlanamıyor
**Yapılacak:**
- retention_days: input number (default 30)
- cleanup_interval_hours: input number (default 24)
- disk_limit_percent: slider (0-100, default 80)
- RecordingTab.tsx'i örnek al

---

## 9. Frontend: MediaTab'ı Settings.tsx'e ekle
**Dosya:** `ui/src/pages/Settings.tsx`
**Yapılacak:**
- Satır 15'e import: `import { MediaTab } from '../components/tabs/MediaTab';`
- Satır 70'e case: `case 'media': updates.media = localSettings.media;`
- Satır 164'e render ekle
- Sidebar.tsx satır 54'e ekle: `{ tab: 'media', label: t('media') }`

---

## 10. Frontend: api.ts DetectionConfig'e aspect_ratio ekle
**Dosya:** `ui/src/types/api.ts` (satır 5-12)
**Sorun:**
- Backend'de aspect_ratio_min, aspect_ratio_max var (app/models/config.py satır 12-56)
- Frontend type'da yok
**Yapılacak:**
```typescript
export interface DetectionConfig {
  model: string
  confidence_threshold: number
  nms_iou_threshold: number
  inference_resolution: [number, number]
  inference_fps: number
  aspect_ratio_min: number  // EKLE
  aspect_ratio_max: number  // EKLE
  enable_tracking: boolean
}
```

---

## 11. Frontend: DetectionTab'a inference_resolution ekle
**Dosya:** `ui/src/components/tabs/DetectionTab.tsx`
**Sorun:**
- Backend'de inference_resolution var (tuple: [width, height])
- Frontend'de type var ama UI input yok
**Yapılacak:**
- Satır 60 civarına ekle (inference_fps'den sonra):
```typescript
<div>
  <label>Width</label>
  <input type="number" value={config.inference_resolution[0]} 
    onChange={(e) => onChange({...config, inference_resolution: [parseInt(e.target.value), config.inference_resolution[1]]})} />
</div>
<div>
  <label>Height</label>
  <input type="number" value={config.inference_resolution[1]} 
    onChange={(e) => onChange({...config, inference_resolution: [config.inference_resolution[0], parseInt(e.target.value)]})} />
</div>
```

---

## 12. Frontend: DetectionTab'a aspect_ratio ekle
**Dosya:** `ui/src/components/tabs/DetectionTab.tsx`
**Sorun:**
- Backend'de aspect_ratio_min (0.3), aspect_ratio_max (3.0) var
- İnsan şekli filtrelemesi için (çok ince/geniş nesneleri eler)
- Frontend'de input yok
**Yapılacak:**
- Satır 95 civarına ekle (nms_iou_threshold'dan sonra):
```typescript
<div>
  <label>Aspect Ratio Min (0.05-1.0)</label>
  <input type="range" min="0.05" max="1.0" step="0.05" value={config.aspect_ratio_min} 
    onChange={(e) => onChange({...config, aspect_ratio_min: parseFloat(e.target.value)})} />
  <span>{config.aspect_ratio_min.toFixed(2)}</span>
</div>
<div>
  <label>Aspect Ratio Max (1.0-5.0)</label>
  <input type="range" min="1.0" max="5.0" step="0.1" value={config.aspect_ratio_max} 
    onChange={(e) => onChange({...config, aspect_ratio_max: parseFloat(e.target.value)})} />
  <span>{config.aspect_ratio_max.toFixed(2)}</span>
</div>
```

---

## 13. Frontend: DetectionTab'a enable_tracking ekle
**Dosya:** `ui/src/components/tabs/DetectionTab.tsx`
**Sorun:**
- Backend'de enable_tracking var (gelecek özellik)
- Frontend'de checkbox yok
**Yapılacak:**
- Satır 100 civarına ekle:
```typescript
<div className="flex items-center space-x-3">
  <input type="checkbox" id="enable-tracking" checked={config.enable_tracking} 
    onChange={(e) => onChange({...config, enable_tracking: e.target.checked})} 
    className="w-4 h-4" />
  <label htmlFor="enable-tracking">Enable Object Tracking (Beta)</label>
</div>
```

---

## 14. Frontend: TelegramTab'a rate_limit_seconds ekle
**Dosya:** `ui/src/components/tabs/TelegramTab.tsx`
**Sorun:**
- Backend'de rate_limit_seconds var (default 10)
- Aynı event için minimum bekleme süresi
- Frontend'de input yok
**Yapılacak:**
- Satır 204 civarına ekle (snapshot_quality'den sonra):
```typescript
<div>
  <label>Rate Limit (seconds)</label>
  <input type="number" min="0" max="300" value={config.rate_limit_seconds} 
    onChange={(e) => onChange({...config, rate_limit_seconds: parseInt(e.target.value) || 10})} 
    className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg" />
  <p className="text-xs text-muted">Minimum wait time between same event notifications</p>
</div>
```

---

## 15. Frontend: TelegramTab'a video_speed ekle
**Dosya:** `ui/src/components/tabs/TelegramTab.tsx`
**Sorun:**
- Backend'de video_speed var (default 2.0)
- Timelapse hızlandırma çarpanı
- Frontend'de slider yok
**Yapılacak:**
- Satır 210 civarına ekle:
```typescript
<div>
  <label>Video Speed: {config.video_speed}x</label>
  <input type="range" min="1" max="10" step="0.5" value={config.video_speed} 
    onChange={(e) => onChange({...config, video_speed: parseFloat(e.target.value)})} 
    className="w-full" />
  <p className="text-xs text-muted">Timelapse speed multiplier</p>
</div>
```

---

## 16. Frontend: TelegramTab'a event_types ekle
**Dosya:** `ui/src/components/tabs/TelegramTab.tsx`
**Sorun:**
- Backend'de event_types var (default: ["person", "vehicle", "animal", "other"])
- Hangi event tiplerinde bildirim gönderilecek
- Frontend'de multi-select yok
**Yapılacak:**
- Satır 215 civarına ekle:
```typescript
<div>
  <label>Event Types to Notify</label>
  <div className="space-y-2">
    {['person', 'vehicle', 'animal', 'other'].map((type) => (
      <label key={type} className="flex items-center gap-2">
        <input type="checkbox" 
          checked={config.event_types.includes(type)} 
          onChange={(e) => {
            const next = e.target.checked 
              ? [...config.event_types, type] 
              : config.event_types.filter(t => t !== type)
            onChange({...config, event_types: next})
          }} />
        <span className="capitalize">{type}</span>
      </label>
    ))}
  </div>
</div>
```

---

## 17. Frontend: TelegramTab'a cooldown_seconds ekle
**Dosya:** `ui/src/components/tabs/TelegramTab.tsx`
**Sorun:**
- Backend'de cooldown_seconds var (default 30)
- Herhangi bir bildirim için minimum bekleme süresi
- Frontend'de input yok
**Yapılacak:**
- Satır 230 civarına ekle:
```typescript
<div>
  <label>Cooldown (seconds)</label>
  <input type="number" min="0" max="600" value={config.cooldown_seconds} 
    onChange={(e) => onChange({...config, cooldown_seconds: parseInt(e.target.value) || 30})} 
    className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg" />
  <p className="text-xs text-muted">Minimum wait time between any notifications</p>
</div>
```

---

## 18. Frontend: TelegramTab'a max_messages_per_min ekle
**Dosya:** `ui/src/components/tabs/TelegramTab.tsx`
**Sorun:**
- Backend'de max_messages_per_min var (default 5)
- Dakikada maksimum bildirim sayısı (spam önleme)
- Frontend'de input yok
**Yapılacak:**
- Satır 240 civarına ekle:
```typescript
<div>
  <label>Max Messages Per Minute</label>
  <input type="number" min="1" max="60" value={config.max_messages_per_min} 
    onChange={(e) => onChange({...config, max_messages_per_min: parseInt(e.target.value) || 5})} 
    className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg" />
  <p className="text-xs text-muted">Rate limiting to prevent spam</p>
</div>
```

---

## 19. Frontend: RecordingTab'a cleanup_policy ekle
**Dosya:** `ui/src/components/tabs/RecordingTab.tsx`
**Sorun:**
- Backend'de cleanup_policy var (default "oldest_first")
- Disk dolunca hangi kayıtlar silinecek: oldest_first | lowest_confidence
- Frontend'de dropdown yok
**Yapılacak:**
- Satır 106 civarına ekle (record_segments_seconds'dan sonra):
```typescript
<div>
  <label>Cleanup Policy</label>
  <select value={config.cleanup_policy} 
    onChange={(e) => onChange({...config, cleanup_policy: e.target.value as 'oldest_first' | 'lowest_confidence'})} 
    className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg">
    <option value="oldest_first">Delete Oldest First</option>
    <option value="lowest_confidence">Delete Lowest Confidence First</option>
  </select>
  <p className="text-xs text-muted">Which recordings to delete when disk is full</p>
</div>
```

---

## 20. Frontend: RecordingTab'a delete_order ekle
**Dosya:** `ui/src/components/tabs/RecordingTab.tsx`
**Sorun:**
- Backend'de delete_order var (default ["mp4", "gif", "collage"])
- Hangi medya tiplerinin önce silineceği (sıralı liste)
- Frontend'de sıralanabilir liste yok
**Yapılacak:**
- Satır 115 civarına ekle:
```typescript
<div>
  <label>Delete Order (drag to reorder)</label>
  <div className="space-y-2">
    {config.delete_order.map((type, index) => (
      <div key={type} className="flex items-center gap-2 p-2 bg-surface2 rounded">
        <span className="text-muted">{index + 1}.</span>
        <span className="flex-1 capitalize">{type}</span>
        <button onClick={() => {
          if (index === 0) return
          const next = [...config.delete_order]
          ;[next[index], next[index - 1]] = [next[index - 1], next[index]]
          onChange({...config, delete_order: next})
        }} disabled={index === 0}>↑</button>
        <button onClick={() => {
          if (index === config.delete_order.length - 1) return
          const next = [...config.delete_order]
          ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
          onChange({...config, delete_order: next})
        }} disabled={index === config.delete_order.length - 1}>↓</button>
      </div>
    ))}
  </div>
  <p className="text-xs text-muted">Order in which media types are deleted (first = deleted first)</p>
</div>
```

---

## ÖZET
- **Toplam:** 20 görev
- **Backend:** 2 görev (bulk delete API, recordings API kontrol)
- **Frontend:** 18 görev (yeni sayfalar, tab'lar, form alanları)
- **Yeni Dosyalar:** 3 (Recordings.tsx, MotionTab.tsx, MediaTab.tsx)
- **Güncellenecek Dosyalar:** 8 (Events.tsx, main.py, api.ts, DetectionTab.tsx, TelegramTab.tsx, RecordingTab.tsx, Settings.tsx, Sidebar.tsx, App.tsx)
