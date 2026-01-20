# TEST PLAN — Phase 2 UI Save Verification

Bu doküman, **Save butonları ve ayarların kalıcılığı** için hızlı test planı ve rapor şablonu içerir.

---

## 1) Hızlı Test Planı (60–90 dk)

### A) UI Smoke (her sekme 1 kaydet)
1. **Detection** → model/confidence değiştir → Save → başarı mesajı
2. **Thermal** → enable_enhancement toggle → Save
3. **Stream** → buffer_size değiştir → Save
4. **Live Stream** → output_mode değiştir → Save
5. **Recording** → retention_days değiştir → Save
6. **Events** → cooldown_seconds değiştir → Save
7. **AI** → model/temperature değiştir → Save
8. **Telegram** → chat_ids ekle → Save
9. **Zones** → polygon oluştur → Save
10. **Cameras** → kamera ekle → Save

### B) API Doğrulama (GET/PUT eşleştir)
Her kaydetmeden sonra:
- `GET /api/settings` ile değişikliğin **gerçekten kaydedildiğini** doğrula.
- `PUT /api/settings` ile **tek alan** update testi yap (partial update).

### C) Persist Test (restart)
- API’yi yeniden başlat
- `GET /api/settings` ile değişikliklerin **kalıcı** olduğunu doğrula.

### D) Hata Testleri (en az 2 adet)
- Geçersiz değer (ör: `disk_limit_percent=999`) → **400 + VALIDATION_ERROR**
- Invalid enum (ör: `output_mode=webrtcx`) → **400 + VALIDATION_ERROR**

---

## 2) Rapor Şablonu

**Test Raporu — Phase 2 UI Save**
- Tarih:  
- Ortam: (local / docker / branch)  
- Test eden:  

**Özet**
- Toplam test: 12  
- Başarılı:  
- Başarısız:  
- Bloker:  

**Detay**
1. Detection Save → ✅/❌  
2. Thermal Save → ✅/❌  
3. Stream Save → ✅/❌  
4. Live Stream Save → ✅/❌  
5. Recording Save → ✅/❌  
6. Events Save → ✅/❌  
7. AI Save → ✅/❌  
8. Telegram Save → ✅/❌  
9. Zones Save → ✅/❌  
10. Cameras Save → ✅/❌  
11. Persist after restart → ✅/❌  
12. Validation error handling → ✅/❌  

**Hatalar**
- #1: (adım, beklenen, görülen, log/endpoint)
- #2: ...
