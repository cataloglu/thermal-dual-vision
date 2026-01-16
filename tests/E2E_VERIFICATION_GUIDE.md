# Telegram Bot End-to-End Verification Guide

This guide provides instructions for running complete end-to-end verification of the Telegram bot functionality.

## Prerequisites

1. **Install Dependencies**
   ```bash
   pip install python-telegram-bot opencv-python numpy pillow
   ```

2. **Create a Telegram Bot**
   - Open Telegram and search for `@BotFather`
   - Send `/newbot` command
   - Follow instructions to create your bot
   - Copy the bot token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

3. **Get Your Chat ID**
   - Send a message to your bot in Telegram
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find the `chat.id` field in the JSON response
   - This is your chat ID (numeric value)

## Environment Setup

Set the required environment variables:

```bash
# Required: Your bot token from BotFather
export TELEGRAM_BOT_TOKEN='123456789:ABCdefGHIjklMNOpqrsTUVwxyz'

# Required: Comma-separated list of authorized chat IDs
export TELEGRAM_CHAT_IDS='123456789,987654321'

# Optional: Rate limit in seconds (default: 5)
export TELEGRAM_RATE_LIMIT='5'
```

Or create a `.env` file:
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_IDS=123456789,987654321
TELEGRAM_RATE_LIMIT=5
```

## Running the Verification

Run the end-to-end verification script:

```bash
cd tests
python e2e_telegram_bot.py
```

## Verification Steps

The script will guide you through 9 verification steps:

### Step 1: Configuration Verification
- ✓ Verifies `TELEGRAM_BOT_TOKEN` is set
- ✓ Verifies `TELEGRAM_CHAT_IDS` is set

### Step 2: Bot Lifecycle
- ✓ Starts the bot successfully
- ✓ Stops the bot gracefully

### Step 3-6: Command Verification (Interactive)
You'll need to manually test these commands in Telegram:

1. **Send `/help`**
   - Expected: Help message with all available commands

2. **Send `/status`**
   - Expected: System status with armed state, last detection, uptime

3. **Send `/arm`**
   - Expected: Confirmation that system is armed
   - Expected: Bot callback is triggered

4. **Send `/disarm`**
   - Expected: Confirmation that system is disarmed
   - Expected: Bot callback is triggered

5. **Send `/snapshot`**
   - Expected: Snapshot request confirmation
   - Expected: Bot callback is triggered

### Step 7: Authorization Verification (Manual)
- Send a command from an **unauthorized** Telegram chat
- Expected: "⛔ Yetkisiz Erişim" error message
- Commands from authorized chats should work normally

### Step 8: Alert Sending Verification
- ✓ Bot sends test alert with 3 images
- Expected in Telegram:
  - Alert message with emoji 🚨
  - Timestamp in format: YYYY-MM-DD HH:MM:SS
  - Threat level: Orta
  - Confidence: %85
  - Detailed analysis text
  - 3 images (red, green, blue)
  - Detected objects: insan, köpek

### Step 9: Rate Limiting Verification
- ✓ Bot sends 3 alerts rapidly
- Expected: Alerts are delayed according to rate limit
- Expected: You receive 3 separate alerts with delays between them

## Expected Results

All verification steps should pass:

```
============================================================
✅ ALL E2E VERIFICATION TESTS PASSED
============================================================

Summary:
   ✓ Bot configuration valid
   ✓ Bot lifecycle (start/stop) working
   ✓ All commands (/help, /status, /arm, /disarm, /snapshot) working
   ✓ Authorization protecting against unauthorized access
   ✓ Alert sending with 3 images working
   ✓ Rate limiting preventing spam

Telegram bot is fully functional! 🎉
```

## Troubleshooting

### Bot Token Invalid
```
Error: Unauthorized
```
- Verify your bot token is correct
- Check for extra spaces or quotes in the environment variable

### Chat ID Not Working
```
Error: Chat not found
```
- Verify your chat ID is numeric
- Make sure you've sent at least one message to the bot
- Use the getUpdates API to get your correct chat ID

### Commands Not Responding
```
No response from bot
```
- Verify the bot is running (check logs)
- Verify your chat ID is in the authorized list
- Try restarting the bot

### Images Not Sending
```
Error: Failed to send media group
```
- Verify opencv-python is installed: `pip install opencv-python`
- Verify numpy is installed: `pip install numpy`
- Check network connection

### Rate Limiting Not Working
```
Alerts sent too quickly
```
- Check `TELEGRAM_RATE_LIMIT` environment variable
- Verify RateLimiter is properly initialized
- Check for any errors in bot logs

## Manual Testing Tips

1. **Use Telegram Desktop or Mobile**
   - Easier to verify image quality and message formatting

2. **Test with Multiple Chat IDs**
   - Add multiple chat IDs to verify broadcast functionality
   - Test that all authorized chats receive alerts

3. **Test Network Failures**
   - Disable network briefly to verify retry logic
   - Check that messages are eventually sent

4. **Test Rate Limiting Edge Cases**
   - Send multiple alerts in quick succession
   - Verify only one alert per rate_limit_seconds

5. **Check Logs**
   - Monitor console output for any errors
   - Verify all callbacks are triggered
   - Check for any network exceptions

## Success Criteria

The bot passes verification if:
- ✅ Bot starts and stops without errors
- ✅ All 5 commands work correctly
- ✅ Unauthorized chats are rejected
- ✅ Alerts send with proper formatting
- ✅ 3 images are received in media group
- ✅ Rate limiting prevents spam
- ✅ Callbacks are triggered for arm/disarm/snapshot
- ✅ No errors in logs during normal operation

## Next Steps

After successful verification:
1. Update `implementation_plan.json` to mark subtask-6-1 as completed
2. Commit changes with message: "auto-claude: subtask-6-1 - End-to-end verification of bot functionality"
3. Update QA sign-off in the implementation plan
4. Document any issues or limitations found during testing
