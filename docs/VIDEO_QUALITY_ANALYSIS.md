# Event Video Kalite Analizi – Neden Bazen İyi Bazen Kötü?

## Video Özeti (timelapse 5.mp4)

| Özellik | Değer |
|---------|-------|
| Çözünürlük | 1280×720 |
| Süre | 3 saniye |
| Frame sayısı | 99 (~33 fps) |
| Codec | H.264, libx264 |
| Bitrate | ~1 Mbps |

---

## Kalite Değişkenliğinin Nedenleri

### 1. Frame kaynağı: Recording vs Buffer

| Kaynak | Ne zaman kullanılır? | Kalite |
|--------|---------------------|--------|
| **Recording extract** | Recording açıksa + ilgili segment bulunursa | Daha yüksek, sürekli stream |
| **SharedFrameBuffer** | Recording kapalı veya segment yoksa | record_fps (varsayılan 10 FPS) örnek |

Buffer **record_fps** ile çalışıyor (varsayılan 10 FPS, config'ten 1–30 arası). Kamera 25 fps üretse bile biz record_fps kadar frame/sn alıyoruz. Daha yüksek = daha akıcı video, biraz daha CPU.

### 2. Hareket bulanıklığı (motion blur)

- Buffer’daki frame’ler **record_fps** (1/record_fps sn) aralıklarla yazılıyor.
- Kişi hareketsizken → net frame’ler.
- Kişi hızlı hareket ederken → blur / bulanıklık.

Olay hızlı hareket sırasında tetiklenirse, penceredeki frame’lerin çoğu bulanık olabilir.

### 3. Frame seçimi – blur filtresi yok

`_select_indices_by_time` frame’leri **zamana göre** eşit dağıtarak seçiyor. Blur’lu frame’leri elemek için ek bir filtre yok. Bu yüzden:

- Net anlar çoksa → video iyi,
- Blur’lu frame’ler çoksa → video kötü görünüyor.

### 4. Olay zamanlaması

- Prebuffer: 5 sn önce
- Postbuffer: 15 sn sonra
- Toplam ~20 sn pencere

Olay ne zaman tetiklenirse, bu pencere o anki sahneye göre değişir. Hızlı yürüyüş/koşu anında tetiklenirse → daha fazla blur, yavaş/durağan anlarda → daha net video.

### 5. Encoder fallback zinciri

| Sıra | Encoder | Kalite |
|------|---------|--------|
| 1 | FFmpeg libx264 (CRF 15) | En iyi |
| 2 | imageio-ffmpeg | Orta |
| 3 | OpenCV mp4v | Daha düşük |

FFmpeg kullanılamazsa (PATH, hata vb.) ikinci/üçüncü seçenek devreye giriyor → kalite düşebilir.

---

## Özet

| Sebep | Etki |
|-------|------|
| **record_fps buffer** | Saniyede record_fps frame (varsayılan 10); düşükse ara anlar kaçar |
| **Hareket blur** | Yürüyüş/koşuda frame’ler bulanık olabilir |
| **Blur filtresi yok** | Kötü frame’ler elenmiyor |
| **Recording yoksa** | Buffer fallback daha düşük kalite |
| **Olay zamanlaması** | Hareketsiz an = iyi, hareket anı = kötü |

---

## İyileştirme Önerileri

1. **Recording’i aç** – MP4 için recording extract kullan; buffer fallback’e düşme.
2. **record_fps artır** – Ayarlar → Events → Frame rate (record_fps). Varsayılan 10; 15–20 daha akıcı video.
3. **Blur filtresi** – Laplacian variance vb. ile bulanık frame’leri tespit edip çıkar.
4. **Substream** – Daha düşük FPS/çözünürlüklü substream kullan; hareket daha az blur yapabilir.
