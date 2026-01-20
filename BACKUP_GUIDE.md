# Backup Guide - Smart Motion Detector v2

Verilerinizi nasıl yedekler ve geri yüklersiniz.

---

## 📦 Yedeklenecek Dosyalar

### 1. **Kameralar + Event'ler** (SQLite)
```
data/app.db
```

### 2. **Ayarlar** (JSON)
```
data/config.json
```

### 3. **Event Medya** (Opsiyonel)
```
data/media/
  ├─ evt-1/
  │   ├─ collage.jpg
  │   ├─ preview.gif
  │   └─ timelapse.mp4
  └─ ...
```

---

## 💾 Manuel Backup

### Windows:
```powershell
# Backup folder oluştur
mkdir backups

# Database backup
copy data\app.db backups\app_%date%.db

# Config backup
copy data\config.json backups\config_%date%.json

# Media backup (opsiyonel)
xcopy data\media backups\media_%date%\ /E /I
```

### Linux/Mac:
```bash
# Backup folder
mkdir -p backups

# Database
cp data/app.db backups/app_$(date +%Y%m%d).db

# Config
cp data/config.json backups/config_$(date +%Y%m%d).json

# Media (optional)
cp -r data/media backups/media_$(date +%Y%m%d)/
```

---

## 🔄 Restore (Geri Yükle)

### 1. Docker'ı Durdur
```bash
docker-compose down
```

### 2. Dosyaları Geri Yükle
```bash
# Database
copy backups\app_20260120.db data\app.db

# Config
copy backups\config_20260120.json data\config.json
```

### 3. Docker'ı Başlat
```bash
docker-compose up -d
```

**Kameralar + ayarlar geri geldi!** ✅

---

## 🔒 Otomatik Backup Script

### backup.bat (Windows):
```batch
@echo off
set BACKUP_DIR=backups\%date:~-4,4%%date:~-10,2%%date:~-7,2%
mkdir %BACKUP_DIR%

copy data\app.db %BACKUP_DIR%\app.db
copy data\config.json %BACKUP_DIR%\config.json
xcopy data\media %BACKUP_DIR%\media\ /E /I /Q

echo Backup complete: %BACKUP_DIR%
```

**Kullanım**:
```
backup.bat
```

---

## 📅 Backup Stratejisi

### Günlük (Otomatik):
```
Windows Task Scheduler:
  - Her gece 03:00
  - backup.bat çalıştır
  - Son 7 gün sakla
```

### Manuel (Önemli Değişikliklerden Önce):
```
# Kamera eklemeden önce
backup.bat

# Ayar değişikliğinden önce
backup.bat
```

---

## 🎯 Docker ile Güvenlik

**docker-compose.yml**:
```yaml
volumes:
  - ./data:/app/data  # Data DIŞARIDA!
```

**Anlam**:
- Docker rebuild → Kod değişir
- `data/` folder → DOKUNULMAZ! ✅

**Yani**: Update yapsan bile kameralar/ayarlar korunur!

---

## ⚠️ Dikkat!

**Şunları YEDEKLEME**:
- `dist/` (frontend build - yeniden oluşturulur)
- `node_modules/` (paketler - yeniden indirilir)
- `__pycache__/` (Python cache)
- `.pytest_cache/` (test cache)

**Sadece `data/` yedekle!** ✅

---

## 🎯 Senin İçin

**Her gün**:
```
backup.bat
```

**Güvende!** 🔒
