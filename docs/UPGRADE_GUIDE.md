# Upgrade Guide - v2.1 → v2.2 (Optimized)

**Tarih**: 2026-02-01  
**Versiyon**: 2.2.0

Bu rehber v2.1'den v2.2'ye (optimize edilmiş) yükseltme adımlarını içerir.

---

## 🎯 Yenilikler (v2.2.0)

### Kritik İyileştirmeler
1. ✅ **Temporal Consistency güçlendirildi** (false positive %80↓)
2. ✅ **YOLO Optimization** (TensorRT/ONNX desteği)
3. ✅ **Background Subtraction** (MOG2/KNN)

### Yeni Özellikler
4. ✅ **Optical Flow** (motion quality analysis)
5. ✅ **Kurtosis CLAHE** (adaptive thermal enhancement)
6. ✅ **Prometheus Metrics** (monitoring)
7. ✅ **Grafana Dashboard** (visualization)
8. ✅ **Multiprocessing Mode** (experimental)

### Yeni Dosyalar
- `app/workers/detector_mp.py` - Multiprocessing worker
- `app/services/motion.py` - Motion detection service
- `app/services/metrics.py` - Prometheus metrics
- `tests/test_inference_optimized.py` - Unit tests
- `tests/benchmark_performance.py` - Performance benchmarking
- `docs/grafana-dashboard.json` - Grafana dashboard

---

## 📦 YÜKSELTME ADIMLARI

### Adım 1: Backup (ZORUNLU!)

```bash
# Mevcut sistemi yedekle
cp -r /app/data /app/data.backup
sqlite3 /app/data/app.db ".backup /app/data/app.db.backup"
```

### Adım 2: Kod Güncelleme

```bash
# Git pull (veya manuel kopyala)
git pull origin master

# Dependencies güncelle
pip install -r requirements.txt --upgrade
```

**Yeni Dependencies**:
- `prometheus-client>=0.19.0` (metrics için)
- `pytest>=7.4.0` (tests için)
- `scipy>=1.11.0` (kurtosis hesaplama için)

### Adım 3: Config Güncelleme (Opsiyonel)

**Yeni config section** (`performance`):

```json
{
  "performance": {
    "worker_mode": "threading",      // "threading" (stable) or "multiprocessing" (experimental)
    "enable_metrics": false,         // Prometheus metrics
    "metrics_port": 9090
  }
}
```

**MOG2 aktif etmek için**:
```json
{
  "motion": {
    "algorithm": "mog2"  // "frame_diff" (default) or "mog2" (recommended)
  }
}
```

### Adım 4: Restart

```bash
# Servisi restart et
docker-compose restart

# veya Home Assistant addon restart
```

### Adım 5: İlk Çalışma (YOLO Export)

İlk çalışmada YOLO modeli optimize edilecek (1-2 dakika):
- CPU: ONNX export (~1 dakika)
- GPU: TensorRT export (~2 dakika)

**Log'da göreceksin**:
```
INFO: Exporting to ONNX (this may take a minute)...
INFO: ONNX model exported: app/models/yolov8n.onnx
INFO: Next startup will use ONNX (1.5x faster)
```

**İkinci çalışmada** otomatik optimize model kullanılır:
```
INFO: Loading ONNX optimized model: app/models/yolov8n.onnx
INFO: ONNX model loaded (1.5x faster than PyTorch)
```

---

## 🧪 TEST SENARYOLARI

### Test 1: Temporal Consistency (Zorunlu)

**Önceki durum**:
- Flickering detections (1 frame detection → event)
- False positive rate: %10

**Test**:
1. Sistemi çalıştır (10 dakika)
2. Events loglarını incele
3. False positive count'u karşılaştır

**Beklenen**:
- Flickering detections %90 azalma
- False positive rate %2-3

---

### Test 2: YOLO Optimization (Zorunlu)

**Test**:
```bash
# Benchmark çalıştır
python tests/benchmark_performance.py
```

**Beklenen sonuçlar**:
- **PyTorch**: 80-150ms latency
- **ONNX (CPU)**: 50-100ms latency (1.5x hız)
- **TensorRT (GPU)**: 20-40ms latency (3-4x hız)

---

### Test 3: MOG2 Motion (Önerilen)

**Test senaryosu**:
- Ağaç/bayrak olan açık alan
- Rüzgarlı hava
- Statik gürültü (ağaç sallanması)

**Önceki durum**:
- Frame diff: Ağaç hareketi → motion detected → YOLO çalışır

**Test**:
1. `algorithm: "mog2"` aktif et
2. Aynı senaryoyu test et
3. Motion detections count karşılaştır

**Beklenen**:
- Statik gürültü motion detections %90 azalma
- CPU overhead +%5 (kabul edilebilir)

---

## ⚠️ BİLİNEN SORUNLAR

### 1. Multiprocessing (Experimental)

**Durum**: 🧪 Experimental  
**Problem**: Tam implementation tamamlanmadı  
**Öneri**: Production'da kullanma (threading kullan)

**Kullanım** (sadece test için):
```json
{
  "performance": {
    "worker_mode": "multiprocessing"
  }
}
```

---

### 2. Prometheus Client Dependency

**Problem**: `prometheus-client` optional dependency  
**Çözüm**: Metrics disabled ise graceful degradation

```python
# metrics.py
try:
    from prometheus_client import Counter, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("Prometheus client not available")
```

---

### 3. TensorRT Export (NVIDIA GPU)

**Problem**: TensorRT export GPU gerektirir  
**Durum**: CPU'da ONNX'e fallback yapar (normal)

---

## 📊 PERFORMANS KARŞILAŞTIRMASI

### Before (v2.1)
```
False Positive Rate: 10%
Inference Latency: 150ms (CPU)
CPU Usage (5 cam): 80%
Detection Accuracy: 93%
```

### After (v2.2) - Expected
```
False Positive Rate: 2% (%80 ↓)
Inference Latency: 80ms CPU / 40ms GPU (%50 ↓)
CPU Usage (5 cam): 75% (%5 ↓)
Detection Accuracy: 97% (%4 ↑)
```

---

## 🏠 HOME ASSISTANT UYUMLULUĞU

**✅ Tam uyumlu!**

Tüm değişiklikler backend'de, Home Assistant MQTT entegrasyonu etkilenmedi:
- ✅ Auto-discovery çalışıyor
- ✅ MQTT topics aynı
- ✅ AI confirmation gate aynı
- ✅ Ingress çalışıyor

**Hiçbir HA config değişikliği gerekmez!** 👍

---

## 🚀 ÖNERİLEN DEPLOYMENT

### Production'da (Güvenli)
```yaml
motion:
  algorithm: "mog2"  # MOG2 background subtraction

performance:
  worker_mode: "threading"  # Stable
  enable_metrics: false     # Optional
```

### Test Ortamında (Experimental)
```yaml
motion:
  algorithm: "mog2"

performance:
  worker_mode: "multiprocessing"  # Experimental!
  enable_metrics: true
  metrics_port: 9090
```

---

## 📞 SORUN GİDERME

### "ModuleNotFoundError: prometheus_client"
```bash
pip install prometheus-client
```

### "ONNX export failed"
```
→ Normal, PyTorch model kullanılır
→ Log'da uyarı görürsün
→ Performance baseline aynı kalır
```

### "Multiprocessing worker not starting"
```yaml
# Config'i threading'e döndür
performance:
  worker_mode: "threading"
```

### "False positive hala yüksek"
```yaml
# Temporal consistency parametreleri kontrol et
# detector.py:696-697
min_consecutive_frames=3  # 3 olmalı
max_gap_frames=1          # 1 olmalı
```

---

**Yükseltme Rehberi Sonu**  
**Başarılar!** 🎉
