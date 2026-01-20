# TODO - Smart Motion Detector v2

Yapılacak işler listesi (öncelik sırasına göre)

**Son Güncelleme**: 2026-01-20

---

## 🔴 Kritik (Hemen)

### 1. **AI Test Butonu** ⏳ (Developer yapıyor)
- Ayarlar → AI tab
- API key input altına [Test Connection] butonu
- POST /api/ai/test endpoint (backend)
- OpenAI bağlantı testi
- Success/error mesajı

**Tahmini**: 30 dakika

---

### 2. **Telegram Test Butonu** ⏳ (Developer yapıyor)
- Ayarlar → Telegram tab
- Bot token input altına [Test Connection] butonu
- POST /api/telegram/test endpoint (zaten var!)
- Test mesajı gönder
- Success/error mesajı

**Tahmini**: 20 dakika

---

### 3. **Model Seçimi UI Kontrolü** ✅ (Var ama görünmüyor mu?)
- Ayarlar → Algılama tab'ına git
- Model dropdown var mı kontrol et
- 4 seçenek: yolov8n-person, yolov8s-person, yolov9t, yolov9s
- Yoksa ekle!

**Durum**: Kontrol edilecek

---

## 🟡 Orta (Sonra)

### 4. **WebSocket Reconnect Loop** ⏳
- Sidebar'da sürekli connect/disconnect
- Backend endpoint çalışıyor
- Frontend bağlanamıyor
- Düzgün debug edilmeli

**Tahmini**: 1 saat

---

### 5. **Phase 16: Kolay İyileştirmeler**
- Settings ↔ Performance mapping
- Storage health (disk kullanımı)
- Event pinning (keep forever)
- Media watermark (event ID)

**Tahmini**: 5 saat

---

### 6. **Phase 17: Orta İyileştirmeler**
- Telemetry/metrics
- Zone visual debug
- Mobile UX

**Tahmini**: 10 saat

---

## 🟢 Düşük (İleride)

### 7. **Birdseye View**
- Tüm kameralar tek ekranda
- Live sayfasına ekle

**Tahmini**: 1 saat

---

### 8. **System Health Detail**
- CPU/Memory/Disk usage
- Diagnostics'e ekle

**Tahmini**: 30 dakika

---

### 9. **Sub-stream Support**
- Main stream (detect)
- Sub stream (live)
- Bandwidth tasarrufu

**Tahmini**: 2 saat

---

### 10. **Notification Rules**
- Gece kritik
- Gündüz normal
- Kamera bazında

**Tahmini**: 2 saat

---

## ⏸️ Atlandı (Gereksiz)

- ❌ Face recognition (zor)
- ❌ LPR (gereksiz)
- ❌ AI Search (pahalı)
- ❌ PTZ Control (sabit kameralar)
- ❌ Multi-tenant (gereksiz)
- ❌ Backup/Restore UI (manuel yeterli)

---

## 📊 Öncelik Sırası

**Bu hafta**:
1. ✅ AI Test butonu (developer yapıyor)
2. ✅ Telegram Test butonu (developer yapıyor)
3. ⏳ Model seçimi kontrol
4. ⏳ WebSocket düzelt

**Gelecek hafta**:
5. Phase 16 (kolay iyileştirmeler)
6. Phase 17 (orta iyileştirmeler)

---

**Bu dosya**: TODO.md (güncel tutulacak)
