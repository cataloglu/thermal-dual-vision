# 11 - Documentation

## Overview
Kapsamlı kullanıcı ve geliştirici dokümantasyonu. README, kurulum, konfigürasyon ve troubleshooting.

## Workflow Type
**simple** - Dokümantasyon yazımı

## Task Scope
Tüm dokümantasyon dosyalarının oluşturulması.

### Doküman Yapısı
```
docs/
├── README.md           # Ana dokümantasyon
├── INSTALL.md          # Kurulum rehberi
├── CONFIGURATION.md    # Ayarlar detayı
├── API.md              # API referansı
└── TROUBLESHOOTING.md  # Sorun giderme
```

### README İçeriği
1. Proje açıklaması ve özellikler
2. Hızlı başlangıç (Quick Start)
3. Ekran görüntüleri
4. Konfigürasyon özeti
5. Gereksinimler
6. Katkıda bulunma

### INSTALL.md İçeriği
1. Gereksinimler
2. Home Assistant Add-on kurulumu
3. Manuel Docker kurulumu
4. İlk yapılandırma
5. Test etme

### CONFIGURATION.md İçeriği
- Tüm config seçenekleri tablo halinde
- Örnek konfigürasyonlar
- Best practices

## Requirements
1. Türkçe + İngilizce
2. Markdown formatı
3. Code blocks with syntax highlighting
4. Görsel destekli (screenshots)

## Files to Modify
- Yok

## Files to Reference
- `config.yaml` - Config seçenekleri
- `src/` - API referansı için

## Success Criteria
- [ ] README.md tamamlandı
- [ ] Kurulum adımları açık ve test edilmiş
- [ ] Tüm config seçenekleri belgelendi
- [ ] Troubleshooting bölümü var
- [ ] İki dilde mevcut

## QA Acceptance Criteria
- Dokümantasyon takip edilerek kurulum yapılabilmeli
- Tüm linkler çalışmalı
- Code örnekleri hatasız

## Dependencies
- 08-main-app
- 10-ha-integration

## Notes
- GitHub-flavored Markdown
- Badge'ler eklenebilir
- Screenshots docs/images/ içinde
