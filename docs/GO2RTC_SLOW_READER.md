# go2rtc "Reader is too slow, discarding N frames" Uyarısı

## Ne Anlama Geliyor?

go2rtc / FFmpeg katmanı, RTSP stream'den gelen frame'leri **tüketicilere** (Live View, detection restream vb.) iletir. Bir tüketici (reader), kameranın üretim hızına yetişemediğinde buffer doluyor ve frame'ler atılır. Bu uyarı bu durumda loglanır. **CPU/ağ sorunu değil** — güçlü cihazlarda da görülür; tasarım gereği detection düşük FPS kullanır.

---

## Bizim Sistemdeki Buffer Değerleri (Detaylı)

### 1. OpenCV VideoCapture Buffer (RTSP Okuma)

| Konum | Değer | Açıklama |
|-------|-------|----------|
| `config.stream.buffer_size` | **1** (varsayılan) | OpenCV iç kuyrukta tutulacak frame sayısı |
| `detector.py` satır 948 | `config.stream.buffer_size` | Config'ten okur → genelde 1 |
| `detector_mp.py` satır 326 | `config.stream.buffer_size` | Config ile uyumlu |
| `main.py` satır 1252 | `config.stream.buffer_size` | Live MJPEG için |
| `camera.py` satır 94 | **1** (sabit) | Snapshot için |

**buffer_size = 1** anlamı: Sadece en son frame tutulur. Okumada gecikme yok; düşük latency.

### 2. Olay / Collage Buffer'lar

| Parametre | Değer | Açıklama |
|-----------|-------|----------|
| `config.event.frame_buffer_size` | **10** | Collage için önbellek frame sayısı |
| `SharedFrameBuffer` (detector_mp) | **100** frame | Event clip + collage için circular buffer |
| `prebuffer_seconds` | **5 sn** | Olaydan önce tutulacak süre |
| `postbuffer_seconds` | **15 sn** | Olaydan sonra tutulacak süre |

### 3. go2rtc / FFmpeg Katmanı

go2rtc ve altındaki FFmpeg, kendi buffer'larını kullanır. **Bu değerleri biz ayarlayamıyoruz.** `go2rtc.yaml` içinde buffer süresi/boyutu config'i yok. "reader is too slow" mesajı bu katmandan gelir.

---

## Buffer Düşürmek Performansı Düşürür mü?

### OpenCV buffer_size (stream.buffer_size)

| buffer_size | Etki | Öneri |
|-------------|------|-------|
| **1** | En düşük gecikme, en güncel frame. Detection için en uygun. | ✅ Önerilen |
| 3–5 | Biraz daha kuyruk; geçici network gecikmelerini tolere eder. | Network'te sorun varsa düşünülebilir |
| 10+ | Yüksek latency; işlenen frame eski olur. Detection kalitesi düşer. | ❌ Önerilmez |

**Sonuç:** `buffer_size = 1` detection için doğru tercih. Daha da düşürmek (örn. 0) mümkün değil; minimum 1. Artırmak latency'yi artırır, performansı düşürür.

### go2rtc Tarafı

go2rtc'nin output buffer'ı bizde konfigüre edilmiyor. Bizim yaptığımız: Sadece inference_fps (örn. 5 fps) ile okuyoruz. Kamera ~25 fps üretiyor; biz kasıtlı olarak yavaş tüketiciyiz. Bu yüzden buffer dolup frame'ler atılıyor. CPU/ağ yeterli olsa bile bu mesaj görülebilir — bu beklenen bir durum.

---

## Neden Diğer Yazılımlarda Görülmüyor Olabilir?

1. **Doğrudan kameraya bağlanma** – Restream/proxy yok; FFmpeg/go2rtc katmanı yok.
2. **Full FPS tüketim** – 25 fps'i okuyup sonra decimate ediyorlar; tüketim hızı yüksek.
3. **Farklı mimari** – Örn. kamera tarafında motion detection; bizim gibi central AI yok.
4. **Log seviyesi** – go2rtc `log.level: warn`/`error` ile bu mesajlar gizlenmiş olabilir.

---

## Bizim Sistemde Neden Görüyoruz?

1. **Detection** – inference_fps (örn. 3–7 fps) ile kasıtlı düşük hızda okuyoruz.
2. **Live View** – 4 kamera MJPEG ile açıksa, go2rtc birden fazla consumer'a dağıtıyor; tüketim hızı sınırlı.

Bu davranış **beklenen** bir durumdur.

---

## Çözüm Önerileri

| Öneri | Açıklama |
|-------|----------|
| **1. Kamera substream** | Düşük FPS/çözünürlüklü substream (örn. 640x480 @ 5–10 fps). URL'de substream path kullanın. |
| **2. Direct RTSP** | Sistem zaten direct kameraya bağlanmayı tercih ediyor. Detection mümkünse go2rtc kullanmaz. |
| **3. Log seviyesi** | `go2rtc.yaml`: `log.level: warn` veya `error` — mesajları azaltır, sorunu değiştirmez. |
| **4. Kamera FPS** | Kamerada stream FPS'i düşürün (25 → 10 fps). go2rtc'ye giren veri azalır. |

---

## Kaynaklar

- [go2rtc GitHub Issues](https://github.com/AlexxIT/go2rtc/issues)
- [Frigate go2rtc config](https://docs.frigate.video/guides/configuring_go2rtc)
- FFmpeg: `-rtbufsize`, `-fflags nobuffer -flags low_delay`
