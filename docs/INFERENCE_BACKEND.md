# Inference backend (parametrik – Scrypted gibi)

Detection için backend Ayarlar → Kamera Ayarları → **Inference backend** ile seçilir. Addon yeniden başlatıldıktan sonra geçerli olur.

## Seçenekler

| Backend | Donanım | Açıklama |
|--------|---------|----------|
| **Auto** | - | TensorRT varsa → ONNX varsa → PyTorch (mevcut mantık) |
| **OpenVINO** | Intel i7 dahili ekran kartı (iGPU), NPU veya CPU | Scrypted’teki gibi Intel ile düşük CPU. İlk seçimde model export 1–2 dk sürebilir. |
| **TensorRT** | NVIDIA GPU | CUDA + .engine dosyası gerekir. |
| **ONNX** | CPU | ONNX Runtime ile CPU inference. |
| **CPU** | CPU | PyTorch ile CPU (fallback). |

## Intel i7 dahili ekran kartı (OpenVINO)

- **OpenVINO** seç; kaydet ve addon’u yeniden başlat.
- İlk açılışta model OpenVINO formatına export edilir (bir kerelik, 1–2 dk).
- Sonraki açılışlarda `intel:gpu` ile inference çalışır; CPU yükü azalır.

Gerekirse Ultralytics/OpenVINO bağımlılığı ortamda yüklü olmalı (Docker imajında genelde vardır).

## Pi nedir?

**Raspberry Pi** = Küçük tek kart bilgisayar (ARM). Sen i7 kullanıyorsun; addon **aynı makinede** (i7’nin olduğu bilgisayar/HA host) çalışıyor. OpenVINO seçtiğinde inference i7’nin dahili ekran kartına gider.
