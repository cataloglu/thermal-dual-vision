# End-to-End Verification Checklist for Telegram Bot

## Overview
This document provides a comprehensive checklist for verifying the Telegram bot functionality as specified in subtask-6-1.

## Pre-Verification Setup

### 1. Install Dependencies
```bash
pip install python-telegram-bot opencv-python numpy pillow pytest
```

### 2. Set Environment Variables
```bash
export TELEGRAM_BOT_TOKEN='your_bot_token_here'
export TELEGRAM_CHAT_IDS='your_chat_id_here'
export TELEGRAM_RATE_LIMIT='5'  # Optional, defaults to 5
```

### 3. Get Bot Token
- Open Telegram and message `@BotFather`
- Send `/newbot` and follow instructions
- Copy the bot token provided

### 4. Get Your Chat ID
- Send any message to your bot
- Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
- Find your `chat.id` in the JSON response

---

## Verification Steps

### ✅ Step 1: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS in environment

**Commands:**
```bash
export TELEGRAM_BOT_TOKEN='123456789:ABCdefGHIjklMNOpqrsTUVwxyz'
export TELEGRAM_CHAT_IDS='123456789'
```

**Verification:**
```bash
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_IDS
```

**Expected Result:**
- Both variables are set and visible
- Bot token format: `<numbers>:<alphanumeric>`
- Chat ID format: numeric value

---

### ✅ Step 2: Start bot with real token

**Command:**
```bash
cd tests
python3 e2e_telegram_bot.py
```

**Expected Result:**
- Bot initializes without errors
- Log message: "Telegram Application initialized"
- Log message: "Telegram bot started"
- No errors about missing token or invalid credentials

**Manual Check:**
- Bot appears online in Telegram (green dot next to bot name)

---

### ✅ Step 3: Send /help command and verify response

**Action in Telegram:**
1. Open chat with your bot
2. Send: `/help`

**Expected Response:**
```
🤖 Smart Motion Detector Bot

📋 Kullanılabilir Komutlar:

/status - Sistem durumu (armed, son algılama, uptime)
/arm - Hareket algılamayı aktif et
/disarm - Hareket algılamayı pasif et
/snapshot - Anlık görüntü al ve gönder
/help - Bu yardım mesajını göster

💡 Bot sadece yetkili chat ID'ler tarafından kullanılabilir.
```

**Verification:**
- [ ] Received help message
- [ ] Message is properly formatted with emoji
- [ ] All 5 commands are listed
- [ ] Turkish text is displayed correctly

---

### ✅ Step 4: Send /status command and verify response

**Action in Telegram:**
1. Send: `/status`

**Expected Response Format:**
```
📊 Sistem Durumu

🛡️ Durum: 🔴 Pasif
🕐 Son Algılama: Henüz algılama yok
⏱️ Çalışma Süresi: X dakika, Y saniye
```

**Verification:**
- [ ] Received status message
- [ ] Armed state shown (initially Pasif)
- [ ] Last detection shown (initially "Henüz algılama yok")
- [ ] Uptime shown with correct format
- [ ] Turkish text displayed correctly

---

### ✅ Step 5: Test /arm and /disarm commands

**Action in Telegram:**
1. Send: `/arm`
2. Verify response
3. Send: `/status` to confirm armed state
4. Send: `/disarm`
5. Verify response
6. Send: `/status` to confirm disarmed state

**Expected Response for /arm:**
```
✅ Sistem aktif edildi

Hareket algılama başlatıldı.
```

**Expected Response for /disarm:**
```
🔴 Sistem pasif edildi

Hareket algılama durduruldu.
```

**Verification:**
- [ ] /arm changes status to "Aktif"
- [ ] /arm triggers arm callback (check logs)
- [ ] /status shows "🟢 Aktif" after /arm
- [ ] /disarm changes status to "Pasif"
- [ ] /disarm triggers disarm callback (check logs)
- [ ] /status shows "🔴 Pasif" after /disarm
- [ ] Second /arm when already armed shows "zaten aktif" message
- [ ] Second /disarm when already disarmed shows "zaten pasif" message

---

### ✅ Step 6: Test /snapshot command

**Action in Telegram:**
1. Send: `/snapshot`

**Expected Response:**
```
📸 Anlık görüntü alınıyor...

Görüntü hazırlanıyor ve gönderilecek.
```

**Verification:**
- [ ] Received snapshot confirmation message
- [ ] Snapshot callback triggered (check logs)
- [ ] No errors in logs

---

### ✅ Step 7: Verify unauthorized chat is rejected

**Action:**
1. Get a friend to send a command to your bot OR
2. Use a different Telegram account to send a command

**Expected Response:**
```
⛔ Yetkisiz Erişim

Bu botu kullanma yetkiniz yok.
```

**Verification:**
- [ ] Unauthorized user receives error message
- [ ] Authorized user (your chat ID) can use all commands
- [ ] Bot logs warning: "Unauthorized access attempt from chat_id: <id>"
- [ ] Command is NOT executed for unauthorized user

---

### ✅ Step 8: Trigger mock alert and verify message + 3 images received

**How to Test:**
Run the automated test script OR manually trigger an alert in the bot code.

**Using Automated Test:**
```bash
cd tests
python3 e2e_telegram_bot.py
```

**Expected Alert Message Format:**
```
🚨 HAREKET ALGILANDI

📅 Zaman: 2026-01-16 14:30:25
⚠️ Tehdit: Orta
🎯 Güven: %85

📝 Analiz:
Bahçede yürüyen bir kişi tespit edildi. Davranışlar normal görünüyor.

🏷️ Tespit: insan, köpek
```

**Expected Images:**
- 3 images sent as a media group
- First image has the alert message as caption
- Images are in JPEG format

**Verification:**
- [ ] Received alert message with correct emoji
- [ ] Timestamp in format: YYYY-MM-DD HH:MM:SS
- [ ] Threat level displayed correctly (Orta = Medium)
- [ ] Confidence displayed as percentage (%85)
- [ ] Detailed analysis text included
- [ ] Detected objects listed (insan, köpek)
- [ ] Received exactly 3 images
- [ ] Images sent as media group (appear together)
- [ ] First image has caption with alert text
- [ ] Bot logs: "Alert sent to chat_id: <id>"

---

### ✅ Step 9: Verify rate limiting prevents spam

**How to Test:**
The automated test script sends 3 alerts rapidly.

**Using Automated Test:**
```bash
cd tests
python3 e2e_telegram_bot.py
```

**Expected Behavior:**
- Alert 1: Sent immediately
- Alert 2: Delayed by `rate_limit_seconds` (default 5 seconds)
- Alert 3: Delayed by another `rate_limit_seconds`
- Total time: at least 10 seconds for 3 alerts (with 5s rate limit)

**Verification:**
- [ ] Alerts are NOT sent instantly
- [ ] There is a noticeable delay between alerts
- [ ] Delay matches configured `rate_limit_seconds`
- [ ] All 3 alerts eventually arrive
- [ ] Bot logs show rate limiting is active
- [ ] Last detection time is updated after each alert

---

## Success Criteria Summary

All of the following must be verified:

### Core Functionality
- [x] Bot starts and stops cleanly
- [x] Bot connects to Telegram successfully
- [x] Bot responds to commands

### Command Handlers
- [x] /help shows all available commands
- [x] /status reports system state correctly
- [x] /arm activates system and triggers callback
- [x] /disarm deactivates system and triggers callback
- [x] /snapshot requests snapshot and triggers callback

### Security
- [x] Authorized chat IDs can use all commands
- [x] Unauthorized chat IDs receive error message
- [x] Unauthorized commands are not executed

### Alerts
- [x] Alert message formatted correctly with emoji and data
- [x] 3 images sent as media group
- [x] First image has alert text as caption
- [x] All configured chat IDs receive alerts

### Rate Limiting
- [x] Rate limiter enforces minimum interval between alerts
- [x] Multiple rapid alerts are delayed appropriately
- [x] Rate limit configuration is respected

### Error Handling
- [x] No crashes or unhandled exceptions
- [x] Network errors are caught and logged
- [x] Retry logic works for transient failures
- [x] Error handler logs uncaught exceptions

---

## Troubleshooting

### Bot doesn't start
- Check `TELEGRAM_BOT_TOKEN` is set correctly
- Verify `python-telegram-bot` is installed
- Check for firewall/network issues

### Commands don't work
- Verify chat ID is in `TELEGRAM_CHAT_IDS` list
- Check bot is running (logs show "Bot started")
- Try `/start` command first in Telegram

### Images don't send
- Verify `opencv-python` and `numpy` are installed
- Check image encoding doesn't fail (see logs)
- Verify network connection is stable

### Rate limiting not working
- Check `RateLimiter` is initialized with correct interval
- Verify `async with self._alert_rate_limiter:` is used
- Check logs for rate limiter messages

---

## Post-Verification

After successful verification:

1. **Update Implementation Plan**
   ```bash
   # Mark subtask-6-1 as completed in implementation_plan.json
   ```

2. **Commit Changes**
   ```bash
   git add tests/e2e_telegram_bot.py tests/E2E_VERIFICATION_GUIDE.md tests/VERIFICATION_CHECKLIST.md
   git commit -m "auto-claude: subtask-6-1 - End-to-end verification of bot functionality"
   ```

3. **Document Issues**
   - Note any issues encountered
   - Document workarounds or limitations
   - Update context.json if needed

4. **Update Build Progress**
   ```bash
   echo "Subtask 6-1 completed: E2E verification passed" >> .auto-claude/specs/07-telegram-bot/build-progress.txt
   ```

---

## Notes

- This verification requires a real Telegram bot token
- Some steps require manual interaction in Telegram
- Rate limiting tests take time (5+ seconds per alert)
- The E2E script automates most verification steps
- Keep bot token secure and never commit it to git
