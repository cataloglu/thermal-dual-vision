# 07 - Telegram Bot

## Overview
Telegram bot ile alarm bildirimi ve uzaktan kontrol. Hareket algılandığında 3 görüntü ve analiz sonucunu gönderecek. Komutlar ile sistem durumu sorgulanabilecek.

## Workflow Type
**feature** - Yeni modül geliştirme

## Task Scope
Telegram bot bağlantısı, bildirim gönderme ve komut işleme.

### Teknik Detaylar
```python
class TelegramBot:
    def __init__(self, config: TelegramConfig)
    async def start(self) -> None
    async def stop(self) -> None
    async def send_alert(self, screenshots: ScreenshotSet, analysis: AnalysisResult) -> None
    async def send_message(self, text: str) -> None
    def set_arm_callback(self, callback: Callable) -> None
    def set_disarm_callback(self, callback: Callable) -> None
    def set_snapshot_callback(self, callback: Callable) -> None
```

### Komutlar
| Komut | Açıklama |
|-------|----------|
| `/status` | Sistem durumu (armed, last detection, uptime) |
| `/arm` | Algılamayı aktif et |
| `/disarm` | Algılamayı pasif et |
| `/snapshot` | Anlık görüntü al ve gönder |
| `/help` | Yardım mesajı |

### Bildirim Formatı
```
🚨 HAREKET ALGILANDI

📅 Zaman: 2024-01-15 14:30:25
⚠️ Tehdit: Orta
🎯 Güven: %85

📝 Analiz:
Bahçede yürüyen bir kişi tespit edildi...

🏷️ Tespit: insan, köpek
```

### Konfigürasyon
```yaml
telegram:
  enabled: true
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  chat_ids:
    - "123456789"
  rate_limit_seconds: 5
  send_images: true
```

## Requirements
1. python-telegram-bot v20+ (async)
2. Media group ile 3 görüntü gönderme
3. Command handlers
4. Chat ID whitelist (authorization)
5. Rate limiting
6. Error handling

## Files to Modify
- Yok

## Files to Reference
- `src/config.py` - TelegramConfig dataclass
- `src/utils.py` - RateLimiter
- `src/screenshot_manager.py` - ScreenshotSet
- `src/llm_analyzer.py` - AnalysisResult

## Success Criteria
- [ ] Bot başlatılıyor ve bağlanıyor
- [ ] Alarm bildirimi gönderiliyor
- [ ] 3 görüntü media group olarak gönderiliyor
- [ ] Tüm komutlar çalışıyor
- [ ] Rate limiting aktif
- [ ] Unauthorized chat'ler engelleniyor

## QA Acceptance Criteria
- Unit test: Mock bot ile command handling
- Integration test: Gerçek bot ile mesaj gönderme
- Security test: Unauthorized chat testi

## Dependencies
- 01-project-structure
- 04-screenshot-system
- 05-llm-vision

## Notes
- Bot token'ı BotFather'dan alınacak
- Görüntüler InputMediaPhoto olarak gönderilecek
- Callback'ler main app'den set edilecek
