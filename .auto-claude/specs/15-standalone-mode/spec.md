# 15 - Standalone Mode

## Overview
Home Assistant olmadan bağımsız çalışma modu. Docker Compose ile deployment, environment variables ile konfigürasyon, doğrudan port expose.

## Workflow Type
**feature** - Standalone deployment

## Task Scope
HA_MODE=false ile çalışan bağımsız mod. Docker Compose, .env dosyası, ve HA-bağımsız config yönetimi.

### Environment Variable
```
HA_MODE=true   → Home Assistant Add-on modu
HA_MODE=false  → Standalone Docker modu (varsayılan)
```

### Docker Compose Yapısı
```yaml
version: '3.8'
services:
  thermal-vision:
    build: .
    ports:
      - "8099:8099"      # Web UI
    environment:
      - HA_MODE=false
      - CAMERA_URL=rtsp://...
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
    volumes:
      - ./data:/data     # Screenshots
      - ./config:/config # Config files
    restart: unless-stopped
```

### Config Kaynakları (Öncelik Sırası)
1. Environment variables
2. config/config.yaml dosyası
3. Default values

## Requirements
1. HA_MODE environment variable kontrolü
2. Docker Compose dosyası
3. .env.example template
4. Bashio olmadan config okuma
5. Doğrudan port expose (ingress yok)
6. MQTT broker bağımsız (opsiyonel)

## Files to Create
```
docker-compose.yml        # Standalone deployment
.env.example              # Environment template
config/config.yaml        # Standalone config file
```

## Files to Modify
```
src/config.py             # HA_MODE switch eklenmesi
src/web_server.py         # Ingress/direct mode switch
src/mqtt_client.py        # Auto-discovery opsiyonel
Dockerfile                # Standalone entrypoint
```

## Success Criteria
- [ ] HA_MODE=false ile başlatılabiliyor
- [ ] Docker Compose ile ayağa kalkıyor
- [ ] Web UI doğrudan port üzerinden erişilebilir
- [ ] Config dosyasından ayar okunuyor
- [ ] MQTT opsiyonel çalışıyor (broker yoksa skip)
- [ ] Telegram bağımsız çalışıyor

## QA Acceptance Criteria
- `docker-compose up` ile başlatma testi
- Environment variable override testi
- Config file okuma testi
- HA_MODE=true/false geçiş testi

## Dependencies
- 01-project-structure
- 08-main-app
- 14-web-ui

## Notes
- Standalone mod varsayılan olacak
- HA modu sadece HA ortamında aktif
- MQTT broker yoksa sessizce skip edilecek
