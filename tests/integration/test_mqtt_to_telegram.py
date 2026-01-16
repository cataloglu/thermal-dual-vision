"""Integration tests for MQTT to Telegram notification flow."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest

from src.config import MQTTConfig, TelegramConfig
from src.llm_analyzer import AnalysisResult, ScreenshotSet
from src.mqtt_client import MQTTClient
from src.telegram_bot import TelegramBot
from tests.mocks.mock_mqtt import MockMQTT


@pytest.mark.integration
class TestMQTTToTelegramIntegration:
    """Integration tests for MQTT to Telegram notification pipeline."""

    @pytest.mark.asyncio
    async def test_complete_mqtt_to_telegram_flow(
        self,
        mqtt_config,
        telegram_config,
        sample_screenshot_set
    ):
        """Test complete flow from MQTT motion event to Telegram notification."""
        # Setup mock MQTT broker
        mock_mqtt_module = MockMQTT()

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            # Create MQTT client and connect
            mqtt_client = MQTTClient(mqtt_config)
            await mqtt_client.connect()

            # Verify MQTT connected
            assert mqtt_client.is_connected is True

            # Setup mock Telegram bot
            with patch("src.telegram_bot.TELEGRAM_AVAILABLE", True):
                with patch("src.telegram_bot.Application") as mock_app_class:
                    # Create mock Telegram application
                    mock_app = AsyncMock()
                    mock_app.bot.send_media_group = AsyncMock()
                    mock_app_builder = MagicMock()
                    mock_app_builder.token.return_value = mock_app_builder
                    mock_app_builder.build.return_value = mock_app
                    mock_app_class.builder.return_value = mock_app_builder

                    # Create Telegram bot
                    telegram_bot = TelegramBot(telegram_config)
                    telegram_bot.application = mock_app

                    # Create analysis result
                    analysis = AnalysisResult(
                        gercek_hareket=True,
                        guven_skoru=0.92,
                        degisiklik_aciklamasi="Bir insan görüntüye girdi",
                        tespit_edilen_nesneler=["insan"],
                        tehdit_seviyesi="dusuk",
                        onerilen_aksiyon="İzlemeye devam et",
                        detayli_analiz="Bir kişi bahçeden geçiyor",
                        raw_response={},
                        processing_time=1.23
                    )

                    # Step 1: Publish motion detection to MQTT
                    await mqtt_client.publish_motion(detected=True, analysis=analysis)

                    # Verify MQTT messages were published
                    mqtt_broker = mock_mqtt_module.get_last_client()
                    assert mqtt_broker is not None

                    motion_messages = mqtt_broker.get_messages_by_topic(
                        f"{mqtt_config.topic_prefix}/motion/state"
                    )
                    assert len(motion_messages) > 0
                    assert motion_messages[-1].payload == "ON"

                    threat_messages = mqtt_broker.get_messages_by_topic(
                        f"{mqtt_config.topic_prefix}/threat_level/state"
                    )
                    assert len(threat_messages) > 0
                    assert threat_messages[-1].payload == "dusuk"

                    # Step 2: Send alert via Telegram
                    await telegram_bot.send_alert(sample_screenshot_set, analysis)

                    # Verify Telegram alert was sent
                    mock_app.bot.send_media_group.assert_called()
                    call_args = mock_app.bot.send_media_group.call_args

                    # Verify alert was sent to all configured chat IDs
                    assert call_args.kwargs["chat_id"] in [
                        int(cid) for cid in telegram_config.chat_ids
                    ]

                    # Verify media group contains 3 photos
                    media_group = call_args.kwargs["media"]
                    assert len(media_group) == 3

                    # Verify first photo has caption with alert message
                    first_photo_caption = media_group[0].caption
                    assert "HAREKET ALGILANDI" in first_photo_caption
                    assert "dusuk" in first_photo_caption.lower() or "Düşük" in first_photo_caption

            # Cleanup: Disconnect MQTT
            await mqtt_client.disconnect()
            assert mqtt_client.is_connected is False

    @pytest.mark.asyncio
    async def test_mqtt_publishes_and_telegram_receives_high_threat(
        self,
        mqtt_config,
        telegram_config,
        sample_screenshot_set
    ):
        """Test high threat level propagation from MQTT to Telegram."""
        # Setup mock MQTT broker
        mock_mqtt_module = MockMQTT()

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            mqtt_client = MQTTClient(mqtt_config)
            await mqtt_client.connect()

            # Setup mock Telegram bot
            with patch("src.telegram_bot.TELEGRAM_AVAILABLE", True):
                with patch("src.telegram_bot.Application") as mock_app_class:
                    mock_app = AsyncMock()
                    mock_app.bot.send_media_group = AsyncMock()
                    mock_app_builder = MagicMock()
                    mock_app_builder.token.return_value = mock_app_builder
                    mock_app_builder.build.return_value = mock_app
                    mock_app_class.builder.return_value = mock_app_builder

                    telegram_bot = TelegramBot(telegram_config)
                    telegram_bot.application = mock_app

                    # Create high threat analysis
                    analysis = AnalysisResult(
                        gercek_hareket=True,
                        guven_skoru=0.98,
                        degisiklik_aciklamasi="Şüpheli bir durum tespit edildi",
                        tespit_edilen_nesneler=["insan", "silah"],
                        tehdit_seviyesi="yuksek",
                        onerilen_aksiyon="Acil müdahale gerekli",
                        detayli_analiz="Silahlı bir kişi görüldü",
                        raw_response={},
                        processing_time=1.5
                    )

                    # Publish to MQTT
                    await mqtt_client.publish_motion(detected=True, analysis=analysis)

                    # Verify MQTT published high threat
                    mqtt_broker = mock_mqtt_module.get_last_client()
                    threat_messages = mqtt_broker.get_messages_by_topic(
                        f"{mqtt_config.topic_prefix}/threat_level/state"
                    )
                    assert threat_messages[-1].payload == "yuksek"

                    confidence_messages = mqtt_broker.get_messages_by_topic(
                        f"{mqtt_config.topic_prefix}/confidence/state"
                    )
                    assert confidence_messages[-1].payload == "98"

                    # Send alert via Telegram
                    await telegram_bot.send_alert(sample_screenshot_set, analysis)

                    # Verify Telegram received high threat alert
                    mock_app.bot.send_media_group.assert_called()
                    media_group = mock_app.bot.send_media_group.call_args.kwargs["media"]
                    alert_caption = media_group[0].caption

                    assert "yuksek" in alert_caption.lower() or "Yüksek" in alert_caption
                    assert "98" in alert_caption

            await mqtt_client.disconnect()

    @pytest.mark.asyncio
    async def test_mqtt_publishes_no_motion_and_telegram_not_alerted(
        self,
        mqtt_config,
        telegram_config
    ):
        """Test that no Telegram alert is sent when LLM determines no real motion."""
        # Setup mock MQTT broker
        mock_mqtt_module = MockMQTT()

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            mqtt_client = MQTTClient(mqtt_config)
            await mqtt_client.connect()

            # Setup mock Telegram bot
            with patch("src.telegram_bot.TELEGRAM_AVAILABLE", True):
                with patch("src.telegram_bot.Application") as mock_app_class:
                    mock_app = AsyncMock()
                    mock_app.bot.send_media_group = AsyncMock()
                    mock_app_builder = MagicMock()
                    mock_app_builder.token.return_value = mock_app_builder
                    mock_app_builder.build.return_value = mock_app
                    mock_app_class.builder.return_value = mock_app_builder

                    telegram_bot = TelegramBot(telegram_config)
                    telegram_bot.application = mock_app

                    # Create no motion analysis (false positive)
                    analysis = AnalysisResult(
                        gercek_hareket=False,
                        guven_skoru=0.95,
                        degisiklik_aciklamasi="Gölge hareketi veya ışık değişimi",
                        tespit_edilen_nesneler=[],
                        tehdit_seviyesi="yok",
                        onerilen_aksiyon="Hiçbir şey yapma",
                        detayli_analiz="Gerçek bir hareket tespit edilmedi",
                        raw_response={},
                        processing_time=0.8
                    )

                    # Publish to MQTT with detected=False
                    await mqtt_client.publish_motion(detected=False, analysis=analysis)

                    # Verify MQTT published OFF state
                    mqtt_broker = mock_mqtt_module.get_last_client()
                    motion_messages = mqtt_broker.get_messages_by_topic(
                        f"{mqtt_config.topic_prefix}/motion/state"
                    )
                    assert motion_messages[-1].payload == "OFF"

                    threat_messages = mqtt_broker.get_messages_by_topic(
                        f"{mqtt_config.topic_prefix}/threat_level/state"
                    )
                    assert threat_messages[-1].payload == "yok"

                    # Verify Telegram alert was NOT sent (no call to send_alert in this scenario)
                    # In real application, send_alert would only be called for real motion
                    mock_app.bot.send_media_group.assert_not_called()

            await mqtt_client.disconnect()

    @pytest.mark.asyncio
    async def test_mqtt_connection_failure_does_not_break_telegram(
        self,
        mqtt_config,
        telegram_config,
        sample_screenshot_set
    ):
        """Test that MQTT connection failure doesn't prevent Telegram alerts."""
        # Setup mock MQTT broker that fails to connect
        mock_mqtt_module = MockMQTT(fail_connect=True)

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            mqtt_client = MQTTClient(mqtt_config)

            # MQTT connection should fail but not raise (auto-reconnect scheduled)
            await mqtt_client.connect()

            # Verify MQTT is not connected
            assert mqtt_client.is_connected is False

            # Setup mock Telegram bot (should still work)
            with patch("src.telegram_bot.TELEGRAM_AVAILABLE", True):
                with patch("src.telegram_bot.Application") as mock_app_class:
                    mock_app = AsyncMock()
                    mock_app.bot.send_media_group = AsyncMock()
                    mock_app_builder = MagicMock()
                    mock_app_builder.token.return_value = mock_app_builder
                    mock_app_builder.build.return_value = mock_app
                    mock_app_class.builder.return_value = mock_app_builder

                    telegram_bot = TelegramBot(telegram_config)
                    telegram_bot.application = mock_app

                    # Create analysis
                    analysis = AnalysisResult(
                        gercek_hareket=True,
                        guven_skoru=0.85,
                        degisiklik_aciklamasi="Test motion",
                        tespit_edilen_nesneler=["insan"],
                        tehdit_seviyesi="dusuk",
                        onerilen_aksiyon="Monitor",
                        detayli_analiz="Person detected",
                        raw_response={},
                        processing_time=1.0
                    )

                    # MQTT publish should fail
                    with pytest.raises(RuntimeError, match="Not connected to MQTT broker"):
                        await mqtt_client.publish_motion(detected=True, analysis=analysis)

                    # But Telegram should still be able to send alerts independently
                    await telegram_bot.send_alert(sample_screenshot_set, analysis)

                    # Verify Telegram alert was sent despite MQTT failure
                    mock_app.bot.send_media_group.assert_called()

    @pytest.mark.asyncio
    async def test_multiple_mqtt_events_to_telegram_with_rate_limiting(
        self,
        mqtt_config,
        telegram_config,
        sample_screenshot_set
    ):
        """Test multiple MQTT motion events and Telegram rate limiting."""
        # Setup mock MQTT broker
        mock_mqtt_module = MockMQTT()

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            mqtt_client = MQTTClient(mqtt_config)
            await mqtt_client.connect()

            # Setup mock Telegram bot
            with patch("src.telegram_bot.TELEGRAM_AVAILABLE", True):
                with patch("src.telegram_bot.Application") as mock_app_class:
                    mock_app = AsyncMock()
                    mock_app.bot.send_media_group = AsyncMock()
                    mock_app_builder = MagicMock()
                    mock_app_builder.token.return_value = mock_app_builder
                    mock_app_builder.build.return_value = mock_app
                    mock_app_class.builder.return_value = mock_app_builder

                    # Use short rate limit for testing
                    telegram_config_fast = TelegramConfig(
                        bot_token=telegram_config.bot_token,
                        chat_ids=telegram_config.chat_ids,
                        rate_limit_seconds=0.1  # Fast for testing
                    )

                    telegram_bot = TelegramBot(telegram_config_fast)
                    telegram_bot.application = mock_app

                    # Publish multiple motion events
                    for i in range(3):
                        analysis = AnalysisResult(
                            gercek_hareket=True,
                            guven_skoru=0.85 + (i * 0.05),
                            degisiklik_aciklamasi=f"Motion event {i+1}",
                            tespit_edilen_nesneler=["insan"],
                            tehdit_seviyesi="dusuk",
                            onerilen_aksiyon="Monitor",
                            detayli_analiz=f"Detection {i+1}",
                            raw_response={},
                            processing_time=1.0
                        )

                        # Publish to MQTT
                        await mqtt_client.publish_motion(detected=True, analysis=analysis)

                        # Send to Telegram (rate limiter will control frequency)
                        await telegram_bot.send_alert(sample_screenshot_set, analysis)

                    # Verify all MQTT messages were published
                    mqtt_broker = mock_mqtt_module.get_last_client()
                    motion_messages = mqtt_broker.get_messages_by_topic(
                        f"{mqtt_config.topic_prefix}/motion/state"
                    )
                    assert len(motion_messages) >= 3

                    # Verify Telegram alerts were sent (rate limiter allows all with 0.1s delay)
                    assert mock_app.bot.send_media_group.call_count == 3

            await mqtt_client.disconnect()

    @pytest.mark.asyncio
    async def test_mqtt_discovery_before_motion_events(
        self,
        mqtt_config,
        telegram_config,
        sample_screenshot_set
    ):
        """Test that MQTT discovery is published before motion events are sent."""
        # Setup mock MQTT broker
        mock_mqtt_module = MockMQTT()

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            mqtt_client = MQTTClient(mqtt_config)
            await mqtt_client.connect()

            # Publish discovery configurations
            await mqtt_client.publish_discovery()

            # Verify discovery messages were published
            mqtt_broker = mock_mqtt_module.get_last_client()
            all_messages = mqtt_broker.get_published_messages()

            # Find discovery config messages
            discovery_messages = [
                msg for msg in all_messages
                if "/config" in msg.topic and msg.retain
            ]
            assert len(discovery_messages) >= 4  # binary_sensor + 3 sensors

            # Verify discovery message contains proper configuration
            motion_discovery = next(
                (msg for msg in discovery_messages if "motion/config" in msg.topic),
                None
            )
            assert motion_discovery is not None
            config_data = json.loads(motion_discovery.payload)
            assert config_data["device_class"] == "motion"
            assert config_data["state_topic"] == f"{mqtt_config.topic_prefix}/motion/state"

            # Now publish motion event
            analysis = AnalysisResult(
                gercek_hareket=True,
                guven_skoru=0.9,
                degisiklik_aciklamasi="Test",
                tespit_edilen_nesneler=["insan"],
                tehdit_seviyesi="dusuk",
                onerilen_aksiyon="Monitor",
                detayli_analiz="Test analysis",
                raw_response={},
                processing_time=1.0
            )

            await mqtt_client.publish_motion(detected=True, analysis=analysis)

            # Verify motion state was published after discovery
            motion_messages = mqtt_broker.get_messages_by_topic(
                f"{mqtt_config.topic_prefix}/motion/state"
            )
            assert len(motion_messages) > 0
            assert motion_messages[-1].payload == "ON"

            await mqtt_client.disconnect()

    @pytest.mark.asyncio
    async def test_mqtt_to_telegram_with_all_chat_ids(
        self,
        mqtt_config,
        sample_screenshot_set
    ):
        """Test that Telegram alerts are sent to all configured chat IDs."""
        # Setup mock MQTT broker
        mock_mqtt_module = MockMQTT()

        # Configure multiple chat IDs
        telegram_config_multi = TelegramConfig(
            bot_token="test_token",
            chat_ids=["111111111", "222222222", "333333333"],
            rate_limit_seconds=0.1
        )

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            mqtt_client = MQTTClient(mqtt_config)
            await mqtt_client.connect()

            # Setup mock Telegram bot
            with patch("src.telegram_bot.TELEGRAM_AVAILABLE", True):
                with patch("src.telegram_bot.Application") as mock_app_class:
                    mock_app = AsyncMock()
                    mock_app.bot.send_media_group = AsyncMock()
                    mock_app_builder = MagicMock()
                    mock_app_builder.token.return_value = mock_app_builder
                    mock_app_builder.build.return_value = mock_app
                    mock_app_class.builder.return_value = mock_app_builder

                    telegram_bot = TelegramBot(telegram_config_multi)
                    telegram_bot.application = mock_app

                    # Create analysis
                    analysis = AnalysisResult(
                        gercek_hareket=True,
                        guven_skoru=0.88,
                        degisiklik_aciklamasi="Test",
                        tespit_edilen_nesneler=["insan"],
                        tehdit_seviyesi="orta",
                        onerilen_aksiyon="Alert",
                        detayli_analiz="Test",
                        raw_response={},
                        processing_time=1.0
                    )

                    # Publish to MQTT
                    await mqtt_client.publish_motion(detected=True, analysis=analysis)

                    # Send alert to all chat IDs
                    await telegram_bot.send_alert(sample_screenshot_set, analysis)

                    # Verify Telegram was called for each chat ID
                    assert mock_app.bot.send_media_group.call_count == 3

                    # Verify all chat IDs received the alert
                    sent_chat_ids = [
                        call.kwargs["chat_id"]
                        for call in mock_app.bot.send_media_group.call_args_list
                    ]
                    assert 111111111 in sent_chat_ids
                    assert 222222222 in sent_chat_ids
                    assert 333333333 in sent_chat_ids

            await mqtt_client.disconnect()
