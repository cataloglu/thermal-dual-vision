# CPU düşürme (Scrypted benzeri)

**Not:** Bu projede detection için substream zaten kullanılıyor. Ayrı URL veya “substream ekle” önerilmez.

---

## Acil CPU düşürme (diğer sistemleri rahatlatmak için)

1. **Ayarlar → Kamera Ayarları:** **Ekonomik** presete tıkla veya manuel **FPS: 1**, **416×416**.
2. **Inference backend:** Intel i7 ise **OpenVINO** seç → addon yeniden başlat.
3. **Thermal enhancement** gereksizse kapat.
4. Gerekirse geçici olarak bazı kameralarda detection kapat.

Varsayılanlar artık 2 fps, 416px, motion 320px (yeni kurulumlar daha düşük CPU).

---

## Neden yüksek?

- go2rtc: kamera başına 1 decode (restream).
- Addon detection: kamera başına 1 RTSP istemcisi → decode + motion (MOG2) + YOLO.
- Kayıt: FFmpeg `-c copy` (hafif).

Kamera başına: 1 decode (biz) + motion + YOLO. 4 kamera = 4× bu yük.

---

## Yapılacaklar (substream dışında)

- **inference_fps:** 2 veya 3 (Ayarlar → Kamera Ayarları).
- **inference_resolution:** [416, 416] veya [480, 480]; 640+ kullanma.
- **Thermal enhancement:** Gereksizse kapat.
- **Kamera sayısı:** Pi’de 4 yerine 2–3 ile dene.
- **Worker modu:** Diagnostics → Worker; threading vs multiprocessing dene.
- **Continuous recording:** Gereksiz kamerada kapat.

---

## Kontrol listesi

| Ayar | Öneri |
|------|--------|
| inference_fps | 2 veya 3 |
| inference_resolution | [416, 416] veya [480, 480] |
| Thermal enhancement | Kapalı (gereksizse) |
| Kamera sayısı | 2–3 ile test |
| go2rtc | Açık |

Substream zaten kullanıldığı varsayılır; tekrar “substream kullan” önerilmez.
