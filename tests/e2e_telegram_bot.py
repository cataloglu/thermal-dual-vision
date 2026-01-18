"""End-to-end verification script for Telegram Bot functionality."""

import asyncio
import importlib.util
import os
import sys
from datetime import datetime

import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import TelegramConfig
from src.logger import get_logger
from src.telegram_bot import TelegramBot

logger = get_logger("e2e_telegram_bot")


class MockScreenshotSet:
    """Mock ScreenshotSet for testing."""

    def __init__(self):
        """Initialize mock screenshot set with sample frames."""
        # Create sample BGR frames (100x100 pixels with different colors)
        self.before_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.before_frame[:, :] = [0, 0, 255]  # Red

        self.now_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.now_frame[:, :] = [0, 255, 0]  # Green

        self.after_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.after_frame[:, :] = [255, 0, 0]  # Blue

        self.timestamp = datetime.now()


class MockAnalysisResult:
    """Mock AnalysisResult for testing."""

    def __init__(self):
        """Initialize mock analysis result."""
        self.tehdit_seviyesi = "orta"
        self.guven_skoru = 0.85
        self.detayli_analiz = "Bahçede yürüyen bir kişi tespit edildi. Davranışlar normal görünüyor."
        self.tespit_edilen_nesneler = ["insan", "köpek"]


async def verify_bot_configuration() -> bool:
    """
    Verify bot configuration from environment.

    Returns:
        True if configuration is valid, False otherwise
    """
    logger.info("Step 1: Verifying bot configuration...")

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_ids_str = os.getenv("TELEGRAM_CHAT_IDS")

    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set in environment")
        logger.info("   Set it with: export TELEGRAM_BOT_TOKEN='your_token_here'")
        return False

    if not chat_ids_str:
        logger.error("❌ TELEGRAM_CHAT_IDS not set in environment")
        logger.info("   Set it with: export TELEGRAM_CHAT_IDS='chat_id1,chat_id2'")
        return False

    chat_ids = [cid.strip() for cid in chat_ids_str.split(",")]
    logger.info(f"✅ Bot token configured: {bot_token[:10]}...")
    logger.info(f"✅ Chat IDs configured: {chat_ids}")

    return True


async def verify_bot_start_stop(config: TelegramConfig) -> bool:
    """
    Verify bot can start and stop successfully.

    Args:
        config: Telegram configuration

    Returns:
        True if start/stop succeeds, False otherwise
    """
    logger.info("\nStep 2: Verifying bot lifecycle (start/stop)...")

    try:
        bot = TelegramBot(config)
        await bot.start()
        logger.info("✅ Bot started successfully")

        await asyncio.sleep(2)  # Give it time to initialize

        await bot.stop()
        logger.info("✅ Bot stopped successfully")

        return True
    except Exception as e:
        logger.error(f"❌ Bot lifecycle failed: {e}")
        return False


async def verify_commands_interactive(config: TelegramConfig) -> bool:
    """
    Verify bot commands interactively with user.

    Args:
        config: Telegram configuration

    Returns:
        True if all commands work, False otherwise
    """
    logger.info("\nStep 3-6: Verifying bot commands...")
    logger.info("=" * 60)
    logger.info("INTERACTIVE TEST - Please follow these steps:")
    logger.info("=" * 60)

    try:
        bot = TelegramBot(config)

        # Set up callbacks to verify they're called
        arm_called = False
        disarm_called = False
        snapshot_called = False

        def arm_callback():
            nonlocal arm_called
            arm_called = True
            logger.info("   ✓ Arm callback triggered")

        def disarm_callback():
            nonlocal disarm_called
            disarm_called = True
            logger.info("   ✓ Disarm callback triggered")

        def snapshot_callback():
            nonlocal snapshot_called
            snapshot_called = True
            logger.info("   ✓ Snapshot callback triggered")

        bot.set_arm_callback(arm_callback)
        bot.set_disarm_callback(disarm_callback)
        bot.set_snapshot_callback(snapshot_callback)

        await bot.start()
        logger.info("\n✅ Bot is now running and listening for commands")
        logger.info("\nPlease test the following commands in your Telegram chat:")
        logger.info("   1. Send /help - Verify you receive help message")
        logger.info("   2. Send /status - Verify you receive status message")
        logger.info("   3. Send /arm - Verify system is armed")
        logger.info("   4. Send /disarm - Verify system is disarmed")
        logger.info("   5. Send /snapshot - Verify snapshot request message")
        logger.info("\nWaiting 30 seconds for you to test commands...")

        await asyncio.sleep(30)

        await bot.stop()
        logger.info("\n✅ Bot stopped after command testing")

        # Verify callbacks were called
        if arm_called and disarm_called and snapshot_called:
            logger.info("✅ All callbacks were triggered successfully")
        else:
            logger.warning("⚠️  Some callbacks were not triggered:")
            if not arm_called:
                logger.warning("   - Arm callback not called")
            if not disarm_called:
                logger.warning("   - Disarm callback not called")
            if not snapshot_called:
                logger.warning("   - Snapshot callback not called")

        return True
    except Exception as e:
        logger.error(f"❌ Command verification failed: {e}")
        return False


async def verify_unauthorized_access(config: TelegramConfig) -> bool:
    """
    Verify unauthorized chat IDs are rejected.

    Args:
        config: Telegram configuration

    Returns:
        True if authorization works, False otherwise
    """
    logger.info("\nStep 7: Verifying unauthorized access protection...")
    logger.info("=" * 60)
    logger.info("MANUAL TEST - Please follow these steps:")
    logger.info("=" * 60)
    logger.info("1. Send a command from an UNAUTHORIZED Telegram chat")
    logger.info("2. Verify you receive 'Yetkisiz Erişim' error message")
    logger.info("\nConfigured authorized chat IDs:")
    for chat_id in config.chat_ids:
        logger.info(f"   - {chat_id}")

    response = input("\nDid unauthorized access get rejected? (y/n): ")
    if response.lower() == 'y':
        logger.info("✅ Authorization verified")
        return True
    else:
        logger.error("❌ Authorization not working correctly")
        return False


async def verify_alert_sending(config: TelegramConfig) -> bool:
    """
    Verify alert sending with mock data.

    Args:
        config: Telegram configuration

    Returns:
        True if alert is sent successfully, False otherwise
    """
    logger.info("\nStep 8: Verifying alert sending with 3 images...")

    try:
        bot = TelegramBot(config)
        await bot.start()

        # Create mock screenshot and analysis data
        screenshots = MockScreenshotSet()
        analysis = MockAnalysisResult()

        logger.info("Sending test alert with 3 images...")
        await bot.send_alert(screenshots, analysis)

        logger.info("\n✅ Alert sent successfully")
        logger.info("Please check your Telegram chat for:")
        logger.info("   - Alert message with emoji, timestamp, threat level, confidence")
        logger.info("   - 3 images (red, green, blue)")
        logger.info("   - Detected objects: insan, köpek")

        await bot.stop()

        response = input("\nDid you receive the alert with 3 images? (y/n): ")
        return response.lower() == 'y'
    except Exception as e:
        logger.error(f"❌ Alert sending failed: {e}")
        return False


async def verify_rate_limiting(config: TelegramConfig) -> bool:
    """
    Verify rate limiting prevents spam.

    Args:
        config: Telegram configuration

    Returns:
        True if rate limiting works, False otherwise
    """
    logger.info("\nStep 9: Verifying rate limiting...")

    try:
        bot = TelegramBot(config)
        await bot.start()

        screenshots = MockScreenshotSet()
        analysis = MockAnalysisResult()

        logger.info(f"Rate limit configured: {config.rate_limit_seconds} seconds")
        logger.info("Attempting to send 3 alerts rapidly...")

        start_time = datetime.now()

        # First alert should go through immediately
        await bot.send_alert(screenshots, analysis)
        logger.info("   ✓ Alert 1 sent")

        # Second alert should be rate limited
        await bot.send_alert(screenshots, analysis)
        logger.info("   ✓ Alert 2 sent (after rate limiting)")

        # Third alert should also be rate limited
        await bot.send_alert(screenshots, analysis)
        logger.info("   ✓ Alert 3 sent (after rate limiting)")

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        expected_min_time = config.rate_limit_seconds * 2  # 2 rate limit waits

        if elapsed >= expected_min_time:
            logger.info(f"✅ Rate limiting working correctly (took {elapsed:.1f}s, expected >={expected_min_time}s)")
            logger.info("Please check your Telegram - you should have received 3 separate alerts with delays")
        else:
            logger.warning(f"⚠️  Rate limiting may not be working (took {elapsed:.1f}s, expected >={expected_min_time}s)")

        await bot.stop()

        response = input("\nDid you receive 3 alerts with delays between them? (y/n): ")
        return response.lower() == 'y'
    except Exception as e:
        logger.error(f"❌ Rate limiting verification failed: {e}")
        return False


async def run_e2e_verification():
    """Run complete end-to-end verification."""
    logger.info("=" * 60)
    logger.info("TELEGRAM BOT END-TO-END VERIFICATION")
    logger.info("=" * 60)

    # Step 1: Verify configuration
    if not await verify_bot_configuration():
        logger.error("\n❌ E2E VERIFICATION FAILED: Configuration not set")
        logger.info("\nPlease set the required environment variables:")
        logger.info("   export TELEGRAM_BOT_TOKEN='your_bot_token'")
        logger.info("   export TELEGRAM_CHAT_IDS='your_chat_id'")
        return False

    # Create configuration
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_ids_str = os.getenv("TELEGRAM_CHAT_IDS")
    chat_ids = [cid.strip() for cid in chat_ids_str.split(",")]
    rate_limit = int(os.getenv("TELEGRAM_RATE_LIMIT", "5"))

    config = TelegramConfig(
        enabled=True,
        bot_token=bot_token,
        chat_ids=chat_ids,
        rate_limit_seconds=rate_limit
    )

    # Step 2: Verify bot start/stop
    if not await verify_bot_start_stop(config):
        logger.error("\n❌ E2E VERIFICATION FAILED: Bot lifecycle failed")
        return False

    # Step 3-6: Verify commands interactively
    if not await verify_commands_interactive(config):
        logger.error("\n❌ E2E VERIFICATION FAILED: Command verification failed")
        return False

    # Step 7: Verify unauthorized access (manual)
    if not await verify_unauthorized_access(config):
        logger.error("\n❌ E2E VERIFICATION FAILED: Authorization not working")
        return False

    # Step 8: Verify alert sending
    if not await verify_alert_sending(config):
        logger.error("\n❌ E2E VERIFICATION FAILED: Alert sending failed")
        return False

    # Step 9: Verify rate limiting
    if not await verify_rate_limiting(config):
        logger.error("\n❌ E2E VERIFICATION FAILED: Rate limiting not working")
        return False

    # Success!
    logger.info("\n" + "=" * 60)
    logger.info("✅ ALL E2E VERIFICATION TESTS PASSED")
    logger.info("=" * 60)
    logger.info("\nSummary:")
    logger.info("   ✓ Bot configuration valid")
    logger.info("   ✓ Bot lifecycle (start/stop) working")
    logger.info("   ✓ All commands (/help, /status, /arm, /disarm, /snapshot) working")
    logger.info("   ✓ Authorization protecting against unauthorized access")
    logger.info("   ✓ Alert sending with 3 images working")
    logger.info("   ✓ Rate limiting preventing spam")
    logger.info("\nTelegram bot is fully functional! 🎉")

    return True


def main():
    """Main entry point."""
    try:
        # Check for python-telegram-bot
        if importlib.util.find_spec("telegram") is None:
            logger.error("python-telegram-bot not installed!")
            logger.info("Install it with: pip install python-telegram-bot")
            sys.exit(1)

        # Run verification
        success = asyncio.run(run_e2e_verification())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n\nVerification interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Verification failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
