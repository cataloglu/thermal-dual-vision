# HA Güncelleme Görünmüyor / "audio" Hatası

Home Assistant Add-on Store'da yeni sürüm görünmüyorsa veya Supervisor loglarında `"audio"` ile ilgili hata çıkıyorsa, aşağıdaki adımları izleyin.

---

## Belirtiler

- Add-on Store'da yeni sürüm görünmüyor.
- Supervisor loglarında `"audio"` anahtarıyla ilgili schema/validation hatası var.

---

## Olası Nedenler

- Add-on repository cache'i güncel değil.
- Supervisor/HA sürümü eski ve manifest şemasıyla uyumsuz.

---

## Çözüm (Önerilen Sıra)

1. **Add-on Store → sağ üst `...` → Refresh/Reload** yapın.
2. Repository listesinde bu repo'yu **kaldırıp tekrar ekleyin**.
3. **Supervisor/HA yeniden başlatın** (Add-on Store cache'i yenilenir).
4. Tarayıcıda **hard refresh** yapın (Ctrl+F5).

---

## Hala Düzelmiyorsa

- **Supervisor ve Home Assistant güncellemesi** yapın.
- Repository URL'sinin doğru olduğunu kontrol edin:
  - `https://github.com/cataloglu/thermal-dual-vision`

---

## Doğrulama

- Add-on sayfasında **yeni sürüm** görünür (örn. `3.10.45`).
- Loglarda repo fetch/parse hatası kalmaz.
