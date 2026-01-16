# Quick Start: E2E Verification

## Setup (5 minutes)

1. **Install dependencies:**
   ```bash
   pip install python-telegram-bot opencv-python numpy pillow
   ```

2. **Create a Telegram bot:**
   - Message `@BotFather` on Telegram
   - Send `/newbot`
   - Get your bot token

3. **Get your chat ID:**
   - Message your bot
   - Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Find `chat.id`

4. **Set environment:**
   ```bash
   export TELEGRAM_BOT_TOKEN='your_token_here'
   export TELEGRAM_CHAT_IDS='your_chat_id_here'
   ```

## Run Verification (5 minutes)

```bash
cd tests
python3 e2e_telegram_bot.py
```

Follow the on-screen instructions to test commands in Telegram.

## What Gets Tested

✅ Bot configuration and startup
✅ Command handlers (/help, /status, /arm, /disarm, /snapshot)
✅ Authorization (unauthorized users blocked)
✅ Alert sending (message + 3 images)
✅ Rate limiting (prevents spam)

## Expected Output

```
============================================================
✅ ALL E2E VERIFICATION TESTS PASSED
============================================================

Summary:
   ✓ Bot configuration valid
   ✓ Bot lifecycle (start/stop) working
   ✓ All commands working
   ✓ Authorization protecting against unauthorized access
   ✓ Alert sending with 3 images working
   ✓ Rate limiting preventing spam

Telegram bot is fully functional! 🎉
```

## Files Created

- **e2e_telegram_bot.py** - Automated E2E verification script
- **E2E_VERIFICATION_GUIDE.md** - Detailed verification guide
- **VERIFICATION_CHECKLIST.md** - Complete checklist with manual steps
- **QUICK_START_E2E.md** - This quick start guide

## For Full Details

See `VERIFICATION_CHECKLIST.md` for complete manual verification steps.
