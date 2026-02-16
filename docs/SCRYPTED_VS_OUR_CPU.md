# Scrypted Neden Düşük CPU ile 10 Kamera Çalıştırıyor?

Resmi doküman ve mimariye göre Scrypted’in farkı iki ana noktada.

---

## 1. Detection sürekli değil, motion ile tetikleniyor

**Scrypted:**
- Object detection **sadece motion olduğunda** çalışıyor.
- Önce kameranın **donanım motion sensörü** (veya yazılım motion eklentisi) hareket algılıyor.
- Motion event gelince o an için object detection devreye giriyor; hareket yokken **inference yok**, CPU boşta.
- Kaynak: [Motion Detection](https://docs.scrypted.app/detection/motion-detection.html), [Object Detection](https://docs.scrypted.app/detection/object-detection.html) – “camera’s hardware motion sensor triggers object detection”, “keeps the server idle otherwise”.

**Bizim sistem:**
- Her kamerada **sabit FPS** (örn. inference_fps = 3) ile sürekli frame okuyup motion (MOG2) + YOLO çalıştırıyoruz.
- Hareket olsun olmasın: 3 fps × N kamera = sürekli decode + motion + inference.
- Yani **sürekli çalışan detection**; Scrypted’teki gibi “sadece motion anında” değil.

Bu fark tek başına büyük CPU farkı yaratır: Scrypted’te boşta 0 inference, bizde 7/24 inference.

---

## 2. Inference donanım hızlandırıcıda (CPU’da değil)

**Scrypted:**
- Object detection eklentileri **Coral EdgeTPU, Intel OpenVINO (NPU/iGPU), Apple CoreML, NVIDIA ONNX (GPU)** kullanıyor.
- YOLO benzeri modeller bu donanıma taşınıyor; CPU sadece koordinasyon/az iş.
- Kaynak: [Object Detection](https://docs.scrypted.app/detection/object-detection.html), [Features](https://docs.scrypted.app/scrypted-nvr/features.html) – “Hardware Accelerated AI”, Coral/OpenVINO/CoreML/ONNX.

**Bizim sistem:**
- ONNX/TensorRT kullanıyoruz; Raspberry Pi’de genelde **TensorRT yok**, tamamen **CPU inference**.
- YOLO yükü doğrudan CPU’ya biniyor.

Yani: Scrypted “10 kamera” derken inference’ı TPU/NPU/GPU’ya veriyor; biz Pi’de CPU’da çalıştırıyoruz.

---

## Özet tablo

| | Scrypted | Bizim sistem |
|---|----------|--------------|
| **Ne zaman inference?** | Sadece motion event’inde | Sürekli (inference_fps × N kamera) |
| **Inference nerede?** | Coral / OpenVINO / CoreML / GPU | Pi’de çoğunlukla CPU |
| **Boşta CPU** | ~0 (idle) | Sürekli decode + motion + YOLO |

Bu yüzden Scrypted “substream + 10 kamera + düşük CPU” diyebiliyor: hem detection sadece motion’da çalışıyor hem de çalıştığında işlem CPU’da değil donanım hızlandırıcıda yapılıyor.

---

## Bizde benzer davranış için (referans)

- **Motion-triggered detection:** Şu an sürekli inference var; istenirse “sadece motion algılandığında YOLO çalıştır” şeklinde bir mod eklenebilir (mimari değişiklik).
- **Donanım hızlandırma:** Pi’de Coral TPU veya Intel NUC + OpenVINO kullanılırsa inference CPU’dan çıkar; mevcut ONNX/TensorRT/Coral desteği bu yönde genişletilebilir.

Bu doküman Scrypted’in nasıl düşük CPU ile çalıştığını netleştirmek için yazıldı; projede substream zaten kullanılıyor, ayrı URL önerilmez.
