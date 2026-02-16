# Plan: Surekli Kayit (Continuous Recording) Duzeltme

## Mevcut Durum
- `recorder.py` zaten FFmpeg ile 7/24 kayit yapiyor (60sn segmentler, `-c copy`)
- `main.py` startup'ta tum kameralar icin kayit baslatiliyor
- Ama **kritik hatalar** var ve clip extraction calismiyor

## Yapilacaklar

### 1. recorder.py - FFmpeg PIPE deadlock fix
- `stdout=subprocess.PIPE, stderr=subprocess.PIPE` yerine `subprocess.DEVNULL` kullan
- FFmpeg diske yaziyor, stdout'a bir sey gondermesine gerek yok
- PIPE buffer dolunca FFmpeg hang kaliyor

### 2. recorder.py - Process health monitoring
- `is_recording()` metodu ekle (process alive mi kontrol et)
- `_monitor_loop()` ile crashed processleri otomatik yeniden baslat
- Zombie process temizligi

### 3. recorder.py - Clip extraction duzelt
- `_find_recordings_in_range()` - dosya adlarindan timestamp parse et (YYYYMMDD_HHMMSS)
- `extract_clip()` - dogru `-ss` (seek) parametresi ekle
- Multi-segment concat desteği (ffmpeg concat demuxer)

### 4. recorder.py - Recording API entegrasyonu
- `start/stop` API endpointleri gercekten FFmpeg process baslat/durdursun
- Simdiki hali sadece DB state yazıyor, FFmpeg baslatmiyor

### 5. detector.py - Diger hata duzeltmeleri
- Frame referans race condition: `frame.copy()` ekle (satir 587)
- `_log_gate` closure'u dongu disina tasi
- Motion service dead code kaldir (kullanilmiyor)
- Zone cache 5sn -> 30sn (config ile ayni)
