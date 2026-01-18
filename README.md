# Thermal Dual Vision - Home Assistant Add-on

AI-powered motion detection with YOLO + GPT-4 Vision. This repository ships a Home Assistant add-on package and a runtime that exposes health endpoints.

## Kurulum
1) Home Assistant > Settings > Add-ons > Add-on Store.
2) Sağ üstteki menüden **Repositories** bölümünü açın.
3) Bu repo URL’sini ekleyin ve kaydedin.
4) Add-on listesinde **Thermal Dual Vision**’ı bulun, yükleyin.
5) Add-on yapılandırmasını kaydedin.
6) Add-on’u başlatın.

## Konfigürasyon
Aşağıdaki örnekler `config.yaml` seçeneklerine göre hazırlanmıştır.

### Color kamera örneği
```yaml
camera_url: "rtsp://user:pass@192.168.1.10:554/stream1"
camera_fps: 5
motion_sensitivity: 7
motion_min_area: 500
motion_cooldown: 5
yolo_model: "yolov8n"
yolo_confidence: 0.5
openai_api_key: "sk-***"
telegram_enabled: false
mqtt_topic_prefix: "smart_motion"
log_level: "INFO"
```

### Thermal kamera örneği
```yaml
camera_url: "rtsp://user:pass@192.168.1.20:554/thermal"
camera_type: "thermal"
camera_fps: 5
motion_sensitivity: 7
motion_min_area: 500
motion_cooldown: 5
yolo_model: "yolov8n"
yolo_confidence: 0.5
openai_api_key: "sk-***"
telegram_enabled: false
mqtt_topic_prefix: "smart_motion"
log_level: "INFO"
```

### Dual (thermal + color) örneği
```yaml
camera_type: "dual"
color_camera_url: "rtsp://user:pass@192.168.1.10:554/stream1"
thermal_camera_url: "rtsp://user:pass@192.168.1.20:554/thermal"
camera_fps: 5
motion_sensitivity: 7
motion_min_area: 500
motion_cooldown: 5
yolo_model: "yolov8n"
yolo_confidence: 0.5
openai_api_key: "sk-***"
telegram_enabled: false
mqtt_topic_prefix: "smart_motion"
log_level: "INFO"
```

### RTSP format
```
rtsp://<username>:<password>@<ip>:<port>/<path>
```

### Sync strategy
Detaylar icin `SYNC_STRATEGY.md` dokumanina bakabilirsiniz.

### MQTT opsiyonları
- `mqtt_topic_prefix`: Topic prefix (örn. `smart_motion`)
- `mqtt_discovery`: Home Assistant discovery aç/kapat

### Telegram opsiyonları
- `telegram_enabled`: Telegram bot kullanımı
- `telegram_bot_token`: Bot token
- `telegram_chat_id`: Yetkili chat ID (virgülle çoklu)

## Health/Ready kontrolü
- `GET /api/health`: sistem durum raporu
- `GET /ready`: readiness kontrolü (200 döner, body içindeki `ready` ile durum verilir)

Örnek:
```
curl http://<addon-host>:8000/api/health
curl -i http://<addon-host>:8000/ready
```

## Docker Desktop (standalone)
Repo root'unda `Dockerfile` bulunduğundan build context doğrudan repo root olmalıdır.

Build:
```
docker build --no-cache -t thermal-dual-vision .
```

Çalıştırma:
```
docker run --rm -p 8000:8000 \
  -e CAMERA_TYPE=color \
  -e CAMERA_URL="rtsp://user:pass@192.168.1.10:554/stream1" \
  -e MQTT_DISCOVERY=false \
  thermal-dual-vision
```

Health/UI kontrolü:
```
curl http://localhost:8000/api/health
curl -i http://localhost:8000/ready
curl -i http://localhost:8000/
```

Dual çalışma örneği:
```
docker run --rm -p 8000:8000 \
  -e CAMERA_TYPE="dual" \
  -e COLOR_CAMERA_URL="rtsp://user:pass@192.168.1.10:554/stream1" \
  -e THERMAL_CAMERA_URL="rtsp://user:pass@192.168.1.20:554/thermal" \
  -e MQTT_DISCOVERY=false \
  thermal-dual-vision
```

## Release Notu
Known issue: `pytest` sırasında `openai` bağımlılığı eksik olduğu için test collection hatası alınabilir.
