# ROADMAP

## Proje amaci
Thermal ve color RTSP akisini tek bir catida birlestiren, Home Assistant add-on olarak calisabilen, yerel ve guvenli bir video analiz altyapisi sunmak.

## Mimari vizyon
- Multi-camera destek: `cameras[]` ile birden fazla thermal/color kaynak yonetimi.
- Pipeline arayuzu: `BasePipeline` ile tutarli stage yapisi ve genisletilebilirlik.
- Ortak event modeli: tum pipeline ve bildirimler icin tek tip event semasi.
- Gozlemlenebilirlik: health/ready, metrikler ve standart log formatlari.

## MoSCoW
### MUST
- Multi-camera `cameras[]` konfigurasyonu ve runtime yonetimi
- `BasePipeline` arayuzu ve temel thermal/color pipeline iskeleti
- Ortak event modeli ve temel event sozlesmesi
- Home Assistant add-on hedefi icin minimum calisan paketleme

### SHOULD
- Thermal/color zaman senkronizasyonu icin temel strateji
- Basit UI ile event listesi ve durum gorunumu
- Health/ready genisletmeleri (camera/mqtt/telegram)
- CI baslangici (lint + tests)

### COULD
- Pipeline plugin sistemi ve stage registry
- Event kurallari ve filtreleme motoru
- Edge cihaz optimizasyon profilleri
- Opsiyonel dis sistem entegrasyonlari

## Sprint ozeti
### Sprint 1
- Multi-camera `cameras[]` konfigurasyonu ve yasam dongusu
- `BasePipeline` arayuzu ve thermal/color skeleton
- Ortak event modeli ve basit UI event listesi
- Health/ready genisletmeleri ve temel CI (lint + tests)

### Sprint 2
- Thermal + color RTSP birlestirme MVP
- Event uretimi ve bildirim akislari (MQTT/Telegram)
- Home Assistant add-on paketleme ve dokumantasyon

### Sprint 3
- Pipeline plugin altyapisi ve gelismis event kurallari
- Web UI genisletmeleri (kamera listesi, timeline)
- Performans, kaynak ve gozlemlenebilirlik iyilestirmeleri
