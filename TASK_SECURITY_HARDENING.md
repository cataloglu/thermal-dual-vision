# 🛡️ GÖREV: Güvenlik ve Performans İyileştirmeleri (Security & Performance Hardening)

Bu belge, yapılan kod denetimi sonucunda tespit edilen **P0 (Kritik)** ve **P1 (Önemli)** seviyesindeki güvenlik ve performans açıklarını kapatmak için hazırlanmış teknik uygulama planıdır.

---

## 📋 ÖZET
**Hedef:** API güvenliğini sağlamak (Auth), Path Traversal riskini kapatmak ve Worker/OpenAI tarafındaki performans darboğazlarını (Blocking/Hang) gidermek.
**Öncelik:** Yüksek (P0)

---

## 🚀 GÖREV 0: Eksik Bağımlılıklar (Hazırlık)

**Sorun:** Proje kodlarında `openai` kütüphanesi kullanılıyor (import ediliyor) ancak `requirements.txt` dosyasında bu kütüphane yer almıyor.
**Risk:** Yeni kurulumlarda proje çalışmayacak (ModuleNotFoundError).

### Yapılacak İşler:
1.  **Dosya:** `requirements.txt`
2.  **Aksiyon:** Dosyaya `openai>=1.0.0` satırını ekle.

---

## 🚀 GÖREV 1: Path Traversal & ID Validasyonu (Güvenlik)

**Sorun:** `app/services/media.py` içinde `event_id` parametresi sanitize edilmeden dosya yoluna ekleniyor.
**Risk:** Saldırgan `../../etc/passwd` gibi ID'ler göndererek sistem dosyalarına erişebilir.

### Yapılacak İşler:
1.  **Dosya:** `app/services/media.py`
2.  **Aksiyon:** `get_media_path` metoduna ID validasyonu ekle.
3.  **Kural:** `event_id` sadece **UUID formatında** veya **Alfanümerik** karakterlerden oluşmalıdır.

**Örnek İmplementasyon:**
```python
import re

def validate_id(self, id_str: str) -> bool:
    # Sadece a-z, A-Z, 0-9 ve tire (-) karakterlerine izin ver
    if not re.match(r'^[a-zA-Z0-9-]+$', id_str):
        return False
    # Path traversal kontrolü
    if ".." in id_str or "/" in id_str or "\\" in id_str:
        return False
    return True

def get_media_path(self, event_id: str, media_type: str) -> Optional[Path]:
    if not self.validate_id(event_id):
        logger.warning(f"Invalid event_id detected: {event_id}")
        return None
    
    # ... mevcut kod ...
```

---

## 🚀 GÖREV 2: Worker Hang & Timeout Yönetimi (Performans)

**Sorun:** `app/workers/detector.py` dosyasında `cv2.VideoCapture` timeout olmadan çağrılıyor.
**Risk:** RTSP sunucusu yanıt vermezse (TCP handshake asılı kalırsa), worker thread sonsuza kadar bekler (Zombie Thread) ve o kamera devre dışı kalır.

### Yapılacak İşler:
1.  **Dosya:** `app/workers/detector.py`
2.  **Fonksiyon:** `_open_capture`
3.  **Aksiyon:**
    *   OpenCV'yi timeout parametreleriyle yapılandır (backend destekliyorsa).
    *   **VEYA** Capture açma işlemini `threading.Thread` ile wrap et ve `join(timeout=5)` ile bekle. Eğer 5 saniyede açılmazsa işlemi iptal et.

**Örnek İmplementasyon (Wrapper Yaklaşımı):**
```python
def _open_capture_safe(self, url: str, timeout: int = 5):
    cap = None
    
    def target():
        nonlocal cap
        # FFMPEG timeout options (backend specific)
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;5000"
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    
    t = threading.Thread(target=target)
    t.daemon = True
    t.start()
    t.join(timeout)
    
    if t.is_alive():
        logger.error(f"Camera connection timeout: {url}")
        return None  # Timeout
        
    if cap and cap.isOpened():
        return cap
    return None
```

---

## 🚀 GÖREV 3: Async OpenAI & Event Loop (Performans)

**Sorun:** `app/services/ai.py` ve `app/services/ai_test.py` içinde `async def` fonksiyonlarda **senkron** `client.chat.completions.create` kullanılıyor.
**Risk:** OpenAI yanıt verene kadar (2-5 saniye) tüm API (FastAPI Event Loop) donuyor. Başka hiçbir istek işlenemiyor.

### Yapılacak İşler:
1.  **Bağımlılık:** `openai` paketinin `AsyncOpenAI` sınıfını import et.
2.  **Dosyalar:**
    *   `app/services/ai.py` -> `analyze_event` metodu
    *   `app/services/ai_test.py` -> `test_openai_connection` fonksiyonu
3.  **Aksiyon:**
    *   `client = OpenAI(...)` yerine `client = AsyncOpenAI(...)` kullan.
    *   Çağrıları `await client.chat.completions.create(...)` şeklinde güncelle.

**Örnek Değişiklik:**
```python
from openai import AsyncOpenAI

# app/services/ai.py
async def analyze_event(self, ...):
    # ...
    client = AsyncOpenAI(api_key=config.ai.api_key)
    
    # AWAIT eklendi
    response = await client.chat.completions.create(
        model=config.ai.model,
        messages=...,
        # ...
    )
```

---

## 🚀 GÖREV 4: Global State İzolasyonu (Mimari)

**Sorun:** `app/main.py` içinde `recording_state` global bir `dict` olarak tutuluyor.
**Risk:** Çoklu worker (Gunicorn) ile çalışıldığında her process'in state'i farklı olur. Kayıt durumu tutarsızlaşır.

### Yapılacak İşler:
1.  **Dosya:** `app/services/camera_crud.py` (veya yeni bir `StateService`)
2.  **Aksiyon:** Kayıt durumunu geçici olarak veritabanında (`Camera` tablosunda yeni bir `is_recording` kolonu) veya mevcut `CameraStatus` mantığına benzer bir yapıda tut.
3.  **Alternatif (Hızlı Çözüm):** Şimdilik tek worker (`workers=1`) ile çalışılacağı varsayılıyorsa bu madde **P2** olarak ertelenebilir; ancak koda `TODO: Move to Redis/DB` notu eklenmeli.

---

## ✅ KONTROL LİSTESİ (DOD - Definition of Done)

- [ ] `requirements.txt` dosyasına `openai` kütüphanesi eklendi.
- [ ] `get_media_path` artık `../` veya geçersiz karakter içeren ID'leri reddediyor.
- [ ] Kamera bağlantısı kopsa bile Worker thread'i en fazla 5 saniye bloklanıyor (asılı kalmıyor).
- [ ] AI analizi yapılırken `/api/health` ve diğer endpointler yanıt vermeye devam ediyor (Async kontrolü).
- [ ] Kodda `os.environ` veya `AsyncOpenAI` değişiklikleri yapıldı.
- [ ] Tüm testler (özellikle timeout ve path traversal senaryoları) manuel olarak doğrulandı.
