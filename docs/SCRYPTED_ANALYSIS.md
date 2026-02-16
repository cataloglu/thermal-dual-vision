# Scrypted Mimari Analizi

23+ kamera, düşük CPU, kaliteli kayıt – Scrypted nasıl yapıyor?

## Özet

Scrypted’ın temel sırrı: **tek bağlantı, tek decode, çok tüketici**. Prebuffer-mixin plugin’i her kamera stream’i için **tek bir parser session** tutuyor; HomeKit, NVR, Live, detection hepsi bu tek session’dan besleniyor.

---

## 1. Prebuffer / Rebroadcast Mimarisi

### Tek Session, Çok Client

```
Kamera RTSP ──► ParserSession (tek) ──┬─► Client 1 (HomeKit)
                                      ├─► Client 2 (NVR Recording)
                                      ├─► Client 3 (Live View)
                                      └─► Client 4 (Video Analysis)
```

- `PrebufferSession`: Her stream ID için **tek** `ParserSession`
- `ensurePrebufferSession()`: İlk client geldiğinde session başlatılıyor
- `rtspPrebuffer`: Son ~10 sn frame buffer (H.264 NAL chunks)
- Yeni client: prebuffer’dan başlayıp canlı stream’e katılıyor

### RTSP Rebroadcast URL

Her stream için internal RTSP server:

```
rtsp://localhost:{rebroadcastPort}/{rtspServerPath}
```

Tüm tüketiciler (HomeKit, NVR, vb.) bu URL’e bağlanıyor – kameraya direkt bağlanmıyor.

---

## 2. Parser Seçenekleri (CPU Etkisi)

Scrypted iki mod sunuyor:

| Parser            | Açıklama                          | CPU |
|-------------------|-----------------------------------|-----|
| **Scrypted (TCP)**| Kendi RTSP parser’ı, FFmpeg yok   | Düşük |
| **FFmpeg (TCP)**  | `-vcodec copy -acodec copy`       | Orta |

- **Scrypted Parser**: Node.js RTSP client (`startRtspSession`), demux/parse kendisi – FFmpeg spawn etmiyor
- **FFmpeg Parser**: `-vcodec copy` = decode yok, sadece remux (demux + mux)

Özet: Decode yok; ya native parser ya da copy. Bizde OpenCV/FFmpeg full decode var.

---

## 3. Stream Seçimi (High / Medium / Low)

README’den:

- **High** (1080p+, 2000 Kbps): Local Stream, Local Recording (NVR)
- **Medium** (720p, 500 Kbps): Remote Stream, HomeKit Secure Video
- **Low** (320p, 100 Kbps): Apple Watch, Video Analysis

Video analysis **low-res** stream kullanıyor → düşük CPU. Bizde detection için full-res decode ediyoruz.

---

## 4. Inactivity Timeout

```javascript
this.inactivityTimeout = setTimeout(() => {
  session.kill(new Error('killed: stream inactivity'));
}, 10000);
```

10 sn boyunca client yoksa session kapatılıyor. Kimse izlemiyorsa CPU kullanılmıyor.

---

## 5. go2rtc ile İlişki

- Scrypted’ın kendi rebroadcast’i var (prebuffer-mixin).
- go2rtc, dışarıya RTSP/WebRTC vermek için kullanılabiliyor; dahili tüketim için zorunlu değil.
- Bizim model: go2rtc tek giriş noktası, herkes oradan besleniyor. Scrypted ise kendi internal RTSP server’ını kullanıyor.

---

## 6. Bizim Sistem vs Scrypted

| Özellik         | Scrypted                    | Bizim Sistem              |
|-----------------|-----------------------------|---------------------------|
| Tek giriş       | Prebuffer-mixin RTSP        | go2rtc restream           |
| Decode          | Yok (copy) veya native parse| OpenCV/FFmpeg decode      |
| Detection input | Low-res stream              | Full-res (çoğunlukla)     |
| Inactivity      | 10 sn → session kill        | Sürekli açık              |
| Substream       | High/Med/Low ayrımı         | Genelde tek stream        |

---

## 7. Olası İyileştirmeler

1. **Substream for detection**: Detection için düşük çözünürlük (örn. 640x360) – YOLO için yeterli, CPU azalır.
2. **Inactivity timeout**: Kimse Live izlemiyorsa go2rtc tarafında stream’i dondurma/durdurma (go2rtc API ile).
3. **Copy vs decode**: Recorder zaten `-c copy`. Detector hâlâ OpenCV ile frame decode ediyor – bu değişmez (inference için gerekli), ama giriş stream’i düşük-res olabilir.
4. **go2rtc kullanımı**: Mimari doğru; tek merkez go2rtc, tüm tüketiciler oradan besleniyor.

---

## Kaynaklar

- [Scrypted GitHub](https://github.com/koush/scrypted)
- [prebuffer-mixin README](https://github.com/koush/scrypted/blob/main/plugins/prebuffer-mixin/README.md)
- [prebuffer-mixin src/main.ts](https://github.com/koush/scrypted/blob/main/plugins/prebuffer-mixin/src/main.ts)
- [ffmpeg-camera](https://github.com/koush/scrypted/tree/main/plugins/ffmpeg-camera)
- [rtsp plugin](https://github.com/koush/scrypted/tree/main/plugins/rtsp)
