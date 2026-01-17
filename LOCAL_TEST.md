# Local Test Guide

## Özet Değişiklikler

### ✅ Tamamlanan Özellikler

1. **Dummy RTSP Support**: RTSP_URL environment variable yoksa otomatik olarak dummy test video üretir
2. **Web UI**: Home Assistant Ingress ile çalışan web arayüzü hazır
3. **MJPEG Stream**: `/stream.mjpeg` endpoint'inde canlı video stream
4. **API Endpoints**: `/api/status` ve `/api/health` endpoint'leri

## Docker ile Test

### Build
```bash
docker compose build
```

veya

```bash
docker build -t smart-motion-detector:local --build-arg BUILD_FROM=alpine:latest .
```

### Run (Dummy Mode - RTSP_URL yoksa)
```bash
docker compose up
```

veya

```bash
docker run -d \
  -p 8099:8099 \
  -e LOG_LEVEL=INFO \
  --name smart-motion-detector \
  smart-motion-detector:local
```

### Run (RTSP URL ile)
```bash
docker run -d \
  -p 8099:8099 \
  -e RTSP_URL=rtsp://your-camera-ip:554/stream \
  -e LOG_LEVEL=INFO \
  --name smart-motion-detector \
  smart-motion-detector:local
```

## Web UI Test

1. Container başladıktan sonra: http://localhost:8099
2. Web UI'da görmeniz gerekenler:
   - Camera Status: Connected (dummy mode'da bile)
   - Live video stream (dummy mode'da hareket eden test pattern)
   - FPS counter

## Log Kontrolü

```bash
# Docker Compose
docker compose logs -f

# Docker Run
docker logs -f smart-motion-detector
```

### Beklenen Log Çıktıları

**Dummy Mode'da:**
```
INFO: No RTSP URL provided, using dummy test video generator
INFO: Dummy camera started successfully
INFO: Web server started on 0.0.0.0:8099
```

**RTSP Mode'da:**
```
INFO: Connecting to RTSP stream: rtsp://...
INFO: RTSP stream connected successfully
INFO: Web server started on 0.0.0.0:8099
```

## Hata Kontrolü

Eğer hata varsa:

1. **Build hataları**: Dockerfile ve dependencies kontrol edin
2. **Runtime hataları**: Logları kontrol edin
3. **Web UI açılmıyor**: Port 8099'un açık olduğunu kontrol edin
4. **Stream görünmüyor**: Dummy mode çalışıyor mu kontrol edin

## API Endpoints

- `GET /` - Web UI
- `GET /stream.mjpeg` - MJPEG video stream
- `GET /api/status` - Camera connection status
- `GET /api/health` - Health check
- `GET /health` - Health check (legacy)
- `GET /ready` - Readiness check (legacy)

## Test Checklist

- [ ] Docker build başarılı
- [ ] Container başlatıldı
- [ ] Web UI açılıyor (http://localhost:8099)
- [ ] Dummy video stream görünüyor
- [ ] API status endpoint çalışıyor
- [ ] Loglar hatasız
