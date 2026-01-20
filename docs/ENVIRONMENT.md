# ENVIRONMENT — Smart Motion Detector (v2)

## Setup

1. Kök dizinde `.env` dosyası oluşturun:
```bash
cp env.example .env
```

2. Değerleri düzenleyin:
```bash
# Linux/Mac
nano .env

# Windows
notepad .env
```

## Environment Variables

### OpenAI (Optional)
- `OPENAI_API_KEY`: OpenAI API key (boş bırakılırsa AI disabled)

### Telegram (Optional)
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_CHAT_IDS`: Virgülle ayrılmış chat ID'ler

### System
- `DATA_DIR`: Data klasörü (default: `./data`)
- `LOG_LEVEL`: Log seviyesi (`debug`, `info`, `warning`, `error`)

### Stream
- `STREAM_MODE`: Stream modu (`mjpeg` veya `webrtc`)
- `GO2RTC_URL`: go2rtc URL (webrtc için gerekli)

### Retention
- `RECORD_RETENTION_DAYS`: Kayıt saklama süresi (gün)
- `RECORD_DISK_LIMIT_PERCENT`: Disk kullanım limiti (%)

## Example (env.example)

Proje kök dizininde `env.example` dosyasını kopyalayın:

```bash
cp env.example .env
```

Sonra değerleri düzenleyin.
