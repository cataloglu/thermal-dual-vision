# 01 - Project Structure

## Overview
Proje temel yapısını ve dosya organizasyonunu oluştur. Home Assistant add-on formatında config.yaml, Dockerfile, run.sh, requirements.txt ve src/ modüllerini hazırla.


## Workflow Type
**feature** - Yeni proje altyapısı oluşturma

## Task Scope
Bu görev projenin temelini oluşturur. Tüm diğer görevler bu yapı üzerine inşa edilecektir.

### Oluşturulacak Dosyalar
| Dosya | Açıklama |
|-------|----------|
| `config.yaml` | Home Assistant add-on konfigürasyonu |
| `Dockerfile` | Container build dosyası |
| `run.sh` | Entry point script (bashio) |
| `requirements.txt` | Python bağımlılıkları |
| `src/__init__.py` | Package init |
| `src/config.py` | Konfigürasyon yönetimi (dataclasses) |
| `src/logger.py` | Loglama modülü |
| `src/utils.py` | Yardımcı fonksiyonlar |
| `tests/__init__.py` | Test package init |

## Requirements
1. Python 3.11+ uyumlu kod
2. Home Assistant add-on config.yaml formatı
3. Multi-arch Dockerfile (amd64, aarch64)
4. Bashio entegrasyonu (run.sh)
5. Type hints ve docstrings zorunlu

## Files to Modify
- Yok (yeni proje)

## Files to Reference
- `.auto-claude/CONTEXT.md` - Proje bağlamı
- `.auto-claude/test_data/sample_config.yaml` - Örnek konfigürasyon

## Success Criteria
- [ ] Tüm klasörler ve dosyalar oluşturuldu
- [ ] config.yaml Home Assistant formatında ve geçerli
- [ ] Dockerfile build edilebilir durumda
- [ ] requirements.txt temel bağımlılıkları içeriyor
- [ ] src/ modülleri import edilebilir
- [ ] Type hints ve docstrings mevcut

## QA Acceptance Criteria
- `python -c "from src import config, logger, utils"` başarılı
- `docker build .` hatasız tamamlanır
- config.yaml HA add-on validator'dan geçer

## Dependencies
Yok - Bu ilk görevdir.

## Notes
- cv2.createBackgroundSubtractorMOG2 motion detection için kullanılacak
- OpenAI GPT-4 Vision API entegrasyonu olacak
- MQTT Home Assistant auto-discovery desteklenecek
