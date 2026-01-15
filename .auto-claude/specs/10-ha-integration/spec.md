# 10 - Home Assistant Integration

## Overview
Home Assistant Add-on olarak tam entegrasyon. Options UI, ingress web arayüzü, supervisor API ve s6-overlay service management.

## Workflow Type
**feature** - HA entegrasyonu

## Task Scope
Add-on yapılandırması, s6-overlay servisleri ve HA-specific dosyalar.

### Add-on Config (Güncelleme)
```yaml
name: "Smart Motion Detector"
version: "1.0.0"
slug: "smart_motion_detector"
description: "AI-powered motion detection with YOLO and GPT-4 Vision"
url: "https://github.com/repo/smart-motion-detector"
arch:
  - amd64
  - aarch64
startup: application
boot: auto
init: false
options:
  camera_url: ""
  motion_sensitivity: 7
  openai_api_key: ""
  telegram_enabled: false
schema:
  camera_url: url
  motion_sensitivity: int(1,10)
  openai_api_key: password
  telegram_enabled: bool
ingress: true
ingress_port: 8099
panel_icon: "mdi:motion-sensor"
panel_title: "Smart Motion"
mqtt: true
```

### S6-Overlay Structure
```
rootfs/
├── etc/
│   ├── services.d/
│   │   └── smart-motion/
│   │       ├── run       # Service start script
│   │       └── finish    # Cleanup script
│   └── cont-init.d/
│       └── 01-init.sh    # Container init script
```

## Requirements
1. S6-overlay service scripts
2. Bashio config reading
3. Ingress URL handling
4. Supervisor API calls
5. Add-on documentation (DOCS.md)

## Files to Modify
- `config.yaml` - HA schema güncellemesi
- `Dockerfile` - s6-overlay eklenmesi

## Files to Reference
- `run.sh` - Mevcut entry point
- `src/config.py` - Config yapısı

## Success Criteria
- [ ] Add-on HA'da görünüyor
- [ ] Options UI çalışıyor
- [ ] Ingress erişimi var
- [ ] MQTT broker bağlantısı otomatik
- [ ] Logs HA'da görünüyor
- [ ] Supervisor API çalışıyor

## QA Acceptance Criteria
- HA Supervisor'da add-on yükleme testi
- Options değişikliği ve restart testi
- Ingress panel erişim testi

## Dependencies
- 01-project-structure
- 08-main-app

## Notes
- HA Add-on Development Guide takip edilecek
- Bashio functions kullanılacak
- Logo ve icon hazırlanacak
