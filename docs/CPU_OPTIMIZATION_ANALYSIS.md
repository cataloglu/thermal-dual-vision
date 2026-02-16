# CPU Optimizasyon Analizi

Scrypted ~%5.6 CPU ile 10 kamera + detection + recording + mesajlar yapıyor. Bizim sistemde CPU yüksek. Analiz:

## Mevcut Mimari (Sorun)

| Bileşen | Kaynak | Decode? | Açıklama |
|---------|--------|---------|----------|
| **detector_mp** | Direct RTSP (kamera) | ✅ Evet | Her kamera için OpenCV VideoCapture = N decode |
| **go2rtc** | Direct RTSP (kamera) | ✅ Evet | Live View için MJPEG/WebRTC = N decode |
| **recorder** | Direct RTSP (kamera) | ❌ Hayır | FFmpeg `-c copy` = sadece demux |
| **main.py Live** | go2rtc MJPEG proxy | ❌ Hayır | go2rtc'den stream alır, decode yok |

**Sonuç:** N kamera için **2N decode** (detection + go2rtc). Scrypted muhtemelen **1 decode/kamera** paylaşıyor.

## detector_mp Neden go2rtc Kullanmıyor?

- `detector_mp.py` satır 331: `rtsp_url = camera_config.get("rtsp_url") or camera_config.get("rtsp_url_thermal")`
- **Sadece direct RTSP** kullanıyor; go2rtc restream URL hiç denenmiyor!
- `detector.py` (threading) ise go2rtc restream'ı fallback olarak kullanıyor ama `prefer_direct=True` ile önce direct tercih ediyor.

## Önerilen Çözüm

**detector_mp'yi go2rtc restream ile besle** (go2rtc aktifse):

1. go2rtc zaten kamerayı decode ediyor (Live View için)
2. detector_mp `rtsp://127.0.0.1:8554/{camera_id}` veya `rtsp://127.0.0.1:8554/{camera_id}_thermal` kullanırsa
3. go2rtc'den okur = **0 ekstra decode**
4. Toplam: **N decode** (sadece go2rtc)

Bu Scrypted benzeri tek-decode mimarisine yaklaştırır. CPU ~%50 azalabilir (detection katmanı decode'dan kurtulur).

## Uygulama Adımları

1. detector_mp başlamadan önce go2rtc servisini kontrol et
2. go2rtc aktifse: `rtsp_url = f"rtsp://127.0.0.1:8554/{stream_name}"` (stream_name = camera_id veya camera_id_thermal)
3. go2rtc yoksa veya restream açılmazsa: mevcut direct RTSP fallback
4. Recorder: `-c copy` ile kalabilir; go2rtc restream veya direct RTSP ikisi de -c copy ile çalışır
