# 🎯 YAPILACAK İŞ: Live Stream İyileştirme (go2rtc Entegrasyonu)

## 📋 MEVCUT DURUM

**Şu an:** OpenCV + MJPEG (2-5s latency)
**Hedef:** go2rtc + WebRTC (0.5-1s latency)
**Sebep:** Multi-browser optimize (her browser ayrı RTSP connection açmasın, kamera yükü azalsın)

---

## 🚀 GÖREV 1: Docker Compose'a go2rtc Ekle

**Dosya:** `docker-compose.yml`

```yaml
version: "3.9"

services:
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    image: smart-motion-detector:dev
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - GO2RTC_URL=http://go2rtc:1984  # EKLE
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    networks:
      - app-network  # EKLE
    depends_on:
      - go2rtc  # EKLE
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/ready"]
      interval: 30s
      timeout: 10s
      retries: 3

  ui:
    build:
      context: .
      dockerfile: docker/Dockerfile.ui
    image: smart-motion-ui:dev
    ports:
      - "5173:5173"
    volumes:
      - ./ui:/ui
    environment:
      - VITE_API_BASE=http://localhost:8000
      - VITE_GO2RTC_URL=http://localhost:1984  # EKLE
    restart: unless-stopped
    networks:
      - app-network  # EKLE

  # YENİ SERVİS
  go2rtc:
    image: alexxit/go2rtc:latest
    container_name: go2rtc
    ports:
      - "1984:1984"  # WebRTC UI + API
    volumes:
      - ./go2rtc.yaml:/config/go2rtc.yaml
    restart: unless-stopped
    networks:
      - app-network  # EKLE
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:1984/api"]
      interval: 30s
      timeout: 5s
      retries: 3

networks:
  app-network:  # EKLE
    driver: bridge
```

**⚠️ ÖNEMLİ:**
- `networks: app-network` ekle (container'lar birbirini görsün)
- `depends_on: go2rtc` ekle (api go2rtc'den sonra başlasın)
- Environment variable'lar ekle (hardcoded URL yok)

---

## 🚀 GÖREV 2: go2rtc Config Oluştur

**Dosya:** `go2rtc.yaml` (yeni dosya, root'ta)

```yaml
# go2rtc configuration
# Kameralar otomatik eklenecek (backend'den)

streams:
  # Örnek (UI'dan eklenince buraya yazılacak):
  # thermal_cam_1:
  #   - rtsp://admin:pass@192.168.1.100:554/stream1
  # color_cam_1:
  #   - rtsp://admin:pass@192.168.1.101:554/stream1

# API ayarları
api:
  listen: ":1984"

# Log seviyesi
log:
  level: info
```

**⚠️ ÖNEMLİ:**
- Boş başlat, backend otomatik dolduracak
- Credential'lar config'de (güvenli değil, production'da vault kullan)

---

## 🚀 GÖREV 3: Backend - go2rtc Sync Servisi

**Dosya:** `app/services/go2rtc.py` (yeni dosya)

```python
"""
go2rtc integration service.
Manages camera streams in go2rtc configuration.
"""
import os
import logging
from pathlib import Path
from typing import Optional
import yaml
import httpx

logger = logging.getLogger(__name__)


class Go2RTCService:
    """Service for go2rtc integration."""
    
    def __init__(self):
        self.config_path = Path("go2rtc.yaml")
        # Environment variable kullan (Docker için)
        self.api_url = os.getenv("GO2RTC_URL", "http://localhost:1984")
        self.enabled = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if go2rtc is available."""
        try:
            response = httpx.get(f"{self.api_url}/api", timeout=2.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"go2rtc not available: {e}")
            return False
    
    def add_camera(self, camera_id: str, rtsp_url: str) -> bool:
        """
        Add camera to go2rtc streams.
        
        Args:
            camera_id: Unique camera identifier
            rtsp_url: RTSP stream URL
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.warning("go2rtc not enabled, skipping camera add")
            return False
        
        try:
            # Load existing config
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}
            
            # Ensure streams section exists
            if 'streams' not in config:
                config['streams'] = {}
            
            # Add camera stream
            config['streams'][camera_id] = [rtsp_url]
            
            # Write config
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            logger.info(f"Camera {camera_id} added to go2rtc")
            
            # Reload go2rtc (API call)
            # NOT: go2rtc otomatik file watch yapıyor, reload gereksiz olabilir
            # Versiyona göre endpoint değişebilir: /api/config/reload veya /api/restart
            try:
                # go2rtc dosya değişikliğini otomatik algılar (file watch)
                # Manuel reload gerekirse:
                # httpx.post(f"{self.api_url}/api/config/reload", timeout=5.0)
                logger.info("go2rtc will auto-reload config (file watch)")
            except Exception as e:
                logger.warning(f"Failed to reload go2rtc: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add camera to go2rtc: {e}")
            return False
    
    def remove_camera(self, camera_id: str) -> bool:
        """
        Remove camera from go2rtc streams.
        
        Args:
            camera_id: Camera identifier to remove
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            if not self.config_path.exists():
                return True
            
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            
            if 'streams' in config and camera_id in config['streams']:
                del config['streams'][camera_id]
                
                with open(self.config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                
                logger.info(f"Camera {camera_id} removed from go2rtc")
                
                # Reload go2rtc
                try:
                    httpx.post(f"{self.api_url}/api/config/reload", timeout=5.0)
                except Exception as e:
                    logger.warning(f"Failed to reload go2rtc: {e}")
                
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove camera from go2rtc: {e}")
            return False
    
    def sync_all_cameras(self, cameras: list) -> None:
        """
        Sync all cameras to go2rtc (startup).
        
        Args:
            cameras: List of camera objects
        """
        if not self.enabled:
            logger.info("go2rtc disabled, skipping camera sync")
            return
        
        logger.info(f"Syncing {len(cameras)} cameras to go2rtc...")
        
        for camera in cameras:
            rtsp_url = camera.rtsp_url_thermal or camera.rtsp_url_color or camera.rtsp_url
            if rtsp_url:
                self.add_camera(camera.id, rtsp_url)
        
        logger.info("Camera sync complete")


# Singleton instance
_go2rtc_service: Optional[Go2RTCService] = None


def get_go2rtc_service() -> Go2RTCService:
    """Get or create go2rtc service instance."""
    global _go2rtc_service
    if _go2rtc_service is None:
        _go2rtc_service = Go2RTCService()
    return _go2rtc_service
```

**⚠️ ÖNEMLİ:**
- Environment variable kullanıyor (`GO2RTC_URL`)
- Availability check var (go2rtc yoksa çalışmaya devam eder)
- Error handling var (fallback to MJPEG)

---

## 🚀 GÖREV 4: Backend - go2rtc Entegrasyonu

**Dosya:** `app/main.py`

**4.1. Import ekle (satır 30 civarı):**
```python
from app.services.go2rtc import get_go2rtc_service

go2rtc_service = get_go2rtc_service()
```

**4.1b. Config model güncelle (app/models/config.py satır 190 civarı):**
```python
class LiveConfig(BaseModel):
    """Live view output configuration (backend → browser)."""
    
    output_mode: Literal["mjpeg", "webrtc"] = Field(
        default="mjpeg",
        description="Live stream output mode"
    )
    webrtc: WebRTCConfig = Field(
        default_factory=WebRTCConfig,
        description="WebRTC configuration"
    )
```

**NOT:** Zaten var, sadece kontrol et.

**4.2. Startup'a sync ekle (satır 123 civarı, @app.on_event("startup") içine):**
```python
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    import asyncio
    
    logger.info("Starting Smart Motion Detector v2")
    
    # Start retention worker
    retention_worker.start()
    logger.info("Retention worker started")
    
    # Wait for services
    logger.info("Waiting 10 seconds for services to initialize...")
    await asyncio.sleep(10)
    logger.info("Services initialized")
    
    # Start detector worker
    detector_worker.start()
    logger.info("Detector worker started")
    
    # EKLE: Sync cameras to go2rtc
    db = next(get_session())
    try:
        cameras = camera_crud_service.get_all_cameras(db)
        go2rtc_service.sync_all_cameras(cameras)
        logger.info("Cameras synced to go2rtc")
    finally:
        db.close()
```

**4.3. Kamera ekle endpoint'ine ekle (POST /api/cameras, satır ~600):**
```python
@app.post("/api/cameras")
async def create_camera(...):
    # ... mevcut kod ...
    
    # Kamera oluşturulduktan sonra EKLE:
    rtsp_url = new_camera.rtsp_url_thermal or new_camera.rtsp_url_color or new_camera.rtsp_url
    if rtsp_url:
        go2rtc_service.add_camera(new_camera.id, rtsp_url)
    
    return camera_response
```

**4.4. Kamera sil endpoint'ine ekle (DELETE /api/cameras/{camera_id}, satır ~650):**
```python
@app.delete("/api/cameras/{camera_id}")
async def delete_camera(...):
    # Silmeden önce EKLE:
    go2rtc_service.remove_camera(camera_id)
    
    # ... mevcut silme kodu ...
```

**⚠️ ÖNEMLİ:**
- go2rtc yoksa hata vermesin (service içinde check var)
- Fallback to MJPEG otomatik

---

## 🚀 GÖREV 5: Frontend - WebRTC Player

**Dosya:** `ui/src/components/StreamViewer.tsx`

**5.1. Environment variable oku (satır 20 civarı):**
```typescript
const GO2RTC_URL = import.meta.env.VITE_GO2RTC_URL || 'http://localhost:1984';
```

**5.2. go2rtc availability check ekle:**
```typescript
const [go2rtcAvailable, setGo2rtcAvailable] = useState(false);

useEffect(() => {
  const checkGo2rtc = async () => {
    try {
      const response = await fetch(`${GO2RTC_URL}/api`, { mode: 'no-cors' });
      setGo2rtcAvailable(true);  // go2rtc yanıt verdi
    } catch {
      setGo2rtcAvailable(false);
    }
  };
  checkGo2rtc();
  const interval = setInterval(checkGo2rtc, 30000);  // 30 saniyede bir kontrol
  return () => clearInterval(interval);
}, []);
```

**5.3. Settings oku (mevcut useSettings hook'u kullan):**
```typescript
const { settings } = useSettings();
const outputMode = settings?.live?.output_mode || 'mjpeg';
```

**5.4. Player render (satır 200 civarı, mevcut img tag'inin yerine):**
```typescript
{/* Conditional render - iframe onError çalışmaz, health check kullan */}
{outputMode === 'webrtc' && go2rtcAvailable ? (
  // WebRTC player (go2rtc iframe)
  <iframe
    src={`${GO2RTC_URL}/stream.html?src=${cameraId}&mode=webrtc`}
    className="w-full h-full border-0"
    allow="autoplay"
    title="WebRTC Stream"
  />
) : (
  // MJPEG player (fallback veya default)
  <img
    src={`/api/cameras/${cameraId}/live`}
    alt="Live stream"
    className="w-full h-full object-contain"
    onError={() => {
      console.error('MJPEG stream failed');
      toast.error('Stream bağlantısı kesildi');
    }}
  />
)}

{/* Status indicator */}
{outputMode === 'webrtc' && !go2rtcAvailable && (
  <div className="absolute top-4 left-4 bg-error/90 text-white px-3 py-2 rounded-lg text-sm">
    go2rtc unavailable, using MJPEG fallback
  </div>
)}
```

**⚠️ ÖNEMLİ:**
- **iframe onError çalışmaz** (cross-origin)
- Conditional render kullan (health check'e göre)
- go2rtc yoksa otomatik MJPEG'e dön
- Status indicator göster

---

## 🚀 GÖREV 6: Frontend - MJPEG/WebRTC Toggle

**Dosya:** `ui/src/components/tabs/LiveTab.tsx`

**6.1. go2rtc status check ekle (satır 20 civarı):**
```typescript
const [go2rtcAvailable, setGo2rtcAvailable] = useState(false);

useEffect(() => {
  // Check go2rtc availability
  const checkGo2rtc = async () => {
    try {
      const GO2RTC_URL = import.meta.env.VITE_GO2RTC_URL || 'http://localhost:1984';
      const response = await fetch(`${GO2RTC_URL}/api`);
      setGo2rtcAvailable(response.ok);
    } catch {
      setGo2rtcAvailable(false);
    }
  };
  checkGo2rtc();
}, []);
```

**6.2. Output mode selector ekle (satır 50 civarı):**
```typescript
<div>
  <label className="block text-sm font-medium text-text mb-2">
    Output Mode
  </label>
  <select
    value={config.output_mode}
    onChange={(e) => onChange({ ...config, output_mode: e.target.value as 'mjpeg' | 'webrtc' })}
    className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
  >
    <option value="mjpeg">MJPEG (basit, her zaman çalışır)</option>
    <option value="webrtc" disabled={!go2rtcAvailable}>
      WebRTC (hızlı, go2rtc gerekli) {!go2rtcAvailable && '- Unavailable'}
    </option>
  </select>
  
  {/* Status indicator */}
  <div className="mt-2 flex items-center gap-2">
    <div className={`w-2 h-2 rounded-full ${go2rtcAvailable ? 'bg-success' : 'bg-error'}`} />
    <span className="text-xs text-muted">
      go2rtc: {go2rtcAvailable ? 'Available' : 'Not running'}
    </span>
  </div>
  
  <p className="text-xs text-muted mt-2">
    MJPEG: 2-5s latency, basit<br />
    WebRTC: 0.5s latency, go2rtc container gerekli
  </p>
</div>
```

**⚠️ ÖNEMLİ:**
- go2rtc yoksa WebRTC disabled
- Status indicator göster (yeşil/kırmızı dot)
- Kullanıcıya bilgi ver

---

## 🚀 GÖREV 7: Production Hazırlık (Opsiyonel)

### nginx Reverse Proxy (Önerilen)

**Dosya:** `nginx.conf` (yeni, production için)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Frontend
    location / {
        proxy_pass http://ui:5173;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://api:8000;
    }
    
    # go2rtc WebRTC (reverse proxy)
    location /go2rtc/ {
        proxy_pass http://go2rtc:1984/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Frontend'de URL değiştir:**
```typescript
// Development
const GO2RTC_URL = 'http://localhost:1984';

// Production
const GO2RTC_URL = window.location.origin + '/go2rtc';
```

**⚠️ ÖNEMLİ:**
- Production'da HTTPS gerekli (WebRTC için)
- Reverse proxy kullan (port expose etme)
- SSL certificate ekle (Let's Encrypt)

---

## ✅ TEST SENARYOSU

### Test 1: go2rtc Başlatma
```bash
# 1. Docker compose başlat
docker-compose up -d

# 2. go2rtc log kontrol
docker logs go2rtc

# Beklenen: "API listen on :1984"

# 3. go2rtc UI aç
http://localhost:1984

# Beklenen: go2rtc web UI açılmalı
```

### Test 2: Kamera Sync
```bash
# 1. Backend başlat
docker-compose up api

# 2. Log kontrol
docker logs api

# Beklenen:
# "Syncing X cameras to go2rtc..."
# "Camera sync complete"

# 3. go2rtc.yaml kontrol
cat go2rtc.yaml

# Beklenen: streams: { camera_id: [rtsp://...] }
```

### Test 3: Frontend WebRTC
```bash
# 1. UI başlat
docker-compose up ui

# 2. Tarayıcıda aç: http://localhost:5173

# 3. Settings > Live
# go2rtc status: Available (yeşil dot) ✅

# 4. Output Mode: WebRTC seç

# 5. Save

# 6. Live sayfasına git
# Stream görünüyor mu? ✅
# Latency düşük mü? (0.5-1s) ✅

# 7. Console kontrol (F12)
# Error yok mu? ✅
```

### Test 4: Fallback
```bash
# 1. go2rtc'yi durdur
docker-compose stop go2rtc

# 2. Settings > Live
# go2rtc status: Not running (kırmızı dot) ✅
# WebRTC option disabled ✅

# 3. Output Mode: MJPEG (otomatik fallback)

# 4. Live sayfası
# MJPEG stream çalışıyor mu? ✅
```

### Test 5: Kamera Ekle/Sil
```bash
# 1. UI'dan yeni kamera ekle

# 2. go2rtc.yaml kontrol
cat go2rtc.yaml
# Yeni kamera eklendi mi? ✅

# 3. go2rtc UI kontrol
http://localhost:1984
# Stream listesinde var mı? ✅

# 4. Kamerayı sil

# 5. go2rtc.yaml kontrol
# Kamera silindi mi? ✅
```

---

## ⚠️ ÖNEMLİ NOTLAR

### Docker Network
- **Zorunlu:** Tüm container'lar aynı network'te olmalı
- Container ismi kullan: `http://go2rtc:1984` (localhost değil!)
- `depends_on` ekle (başlatma sırası önemli)

### Development vs Production
**Development:**
- `http://localhost:1984` kullan
- HTTPS gereksiz
- Port expose et

**Production:**
- nginx reverse proxy kullan (`/go2rtc/`)
- HTTPS zorunlu (WebRTC için)
- SSL certificate ekle
- Port expose etme (güvenlik)

### Troubleshooting
**go2rtc başlamıyor:**
- `docker logs go2rtc` kontrol et
- Port 1984 boş mu? (`netstat -an | grep 1984`)
- go2rtc.yaml syntax hatası var mı?

**WebRTC stream görünmüyor:**
- go2rtc UI'da stream var mı? (`http://localhost:1984`)
- Browser console'da error var mı?
- Network tab'da WebSocket connection var mı?
- HTTPS kullanıyor musun? (production'da zorunlu)

**CORS hatası alıyorum:**
- Sebep: Frontend (localhost:5173) → go2rtc (localhost:1984) cross-origin
- Çözüm 1: nginx reverse proxy kullan (önerilen, production için)
- Çözüm 2: go2rtc.yaml'e CORS ayarı ekle:
```yaml
api:
  listen: ":1984"
  origin: "*"  # Development için, production'da spesifik origin
```

**MJPEG'e fallback olmuyor:**
- StreamViewer.tsx'de `go2rtcAvailable` prop geliyor mu?
- Health check çalışıyor mu? (30 saniyede bir)
- Conditional render doğru mu? (`outputMode === 'webrtc' && go2rtcAvailable`)

**iframe içi stream görünmüyor:**
- go2rtc.yaml'de kamera var mı?
- RTSP URL doğru mu?
- go2rtc log'da error var mı? (`docker logs go2rtc`)
- **NOT:** iframe onError eventi çalışmaz (cross-origin), health check kullan

### Güvenlik
- **Credential'lar:** go2rtc.yaml'de RTSP credential'lar var (güvensiz!)
- **Çözüm:** Production'da vault/secrets manager kullan
- **Alternatif:** Environment variable'dan oku, yaml'e yazma

---

## 🎯 BAŞARI KRİTERLERİ

### Her Görev İçin:
- [ ] Kod çalışıyor (error yok)
- [ ] Docker container başlıyor
- [ ] Log'da error yok
- [ ] Test senaryosu geçiyor

### Tüm Proje İçin:
- [ ] go2rtc container çalışıyor
- [ ] Kameralar otomatik sync ediliyor
- [ ] WebRTC stream görünüyor
- [ ] Latency düştü (2-5s → 0.5s)
- [ ] MJPEG fallback çalışıyor
- [ ] UI toggle çalışıyor
- [ ] Console'da error yok
- [ ] Production ready (nginx config hazır)

---

## 📦 GEREKSİNİMLER

### Backend:
**Dosya:** `requirements.txt`
```txt
# Mevcut dependencies...
pyyaml>=6.0
httpx>=0.24.0
```

**Kurulum:**
```bash
pip install pyyaml httpx
```

### Frontend:
- Yeni dependency yok (iframe kullanıyoruz)

### Docker:
- go2rtc image (alexxit/go2rtc:latest)

---

## 🚀 BAŞLAMA SIRASI

1. **Görev 1:** Docker compose güncelle (5 dk)
2. **Görev 2:** go2rtc.yaml oluştur (2 dk)
3. **Görev 3:** Backend go2rtc.py yaz (30 dk)
4. **Görev 4:** Backend entegrasyon (15 dk)
5. **Görev 5:** Frontend player (20 dk)
6. **Görev 6:** Frontend toggle (15 dk)
7. **Test:** Tüm senaryolar (30 dk)

**Toplam:** ~2 saat

---

**Başlayalım mı?** 🚀
