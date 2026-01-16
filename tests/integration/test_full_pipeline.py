"""Integration tests for full motion detection pipeline."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.config import LLMConfig, MQTTConfig, TelegramConfig
from src.llm_analyzer import AnalysisResult, LLMAnalyzer, ScreenshotSet
from src.mqtt_client import MQTTClient
from src.telegram_bot import TelegramBot
from tests.mocks.mock_camera import MockCamera
from tests.mocks.mock_mqtt import MockMQTT
from tests.mocks.mock_openai import MockOpenAI


@pytest.mark.integration
class TestFullPipeline:
    """Integration tests for complete motion detection pipeline."""

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_complete_end_to_end_pipeline(
        self,
        mock_openai_class,
        llm_config,
        mqtt_config,
        telegram_config
    ):
        """
        Test complete end-to-end pipeline from motion detection to notifications.

        Flow:
        1. Capture frames from camera (before, now, after)
        2. Analyze frames with LLM
        3. Publish motion event to MQTT
        4. Send alert via Telegram
        """
        # Step 1: Setup camera and capture motion frames
        camera = MockCamera(width=1280, height=720)

        # Capture screenshot set (simulate motion detection)
        success1, before_frame = camera.read()
        assert success1 is True
        now_frame = camera.generate_motion_frame(motion_type="person")
        after_frame = camera.generate_motion_frame(motion_type="person")

        screenshot_set = ScreenshotSet(
            before=before_frame,
            now=now_frame,
            after=after_frame,
            timestamp=datetime.now()
        )

        # Step 2: Setup LLM analyzer with mock OpenAI
        mock_response_json = MockOpenAI.create_valid_motion_response(
            gercek_hareket=True,
            guven_skoru=0.92,
            nesneler=["insan"],
            tehdit="dusuk"
        )
        mock_client = MockOpenAI(response_json=mock_response_json)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        analysis = await analyzer.analyze(screenshot_set)

        # Verify LLM analysis
        assert isinstance(analysis, AnalysisResult)
        assert analysis.gercek_hareket is True
        assert analysis.guven_skoru == 0.92
        assert "insan" in analysis.tespit_edilen_nesneler
        assert analysis.tehdit_seviyesi == "dusuk"

        # Step 3: Setup MQTT client and publish motion event
        mock_mqtt_module = MockMQTT()

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            mqtt_client = MQTTClient(mqtt_config)
            await mqtt_client.connect()
            assert mqtt_client.is_connected is True

            # Publish motion event
            await mqtt_client.publish_motion(detected=True, analysis=analysis)

            # Verify MQTT messages
            mqtt_broker = mock_mqtt_module.get_last_client()
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

            # Step 4: Setup Telegram bot and send alert
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

                    # Send alert
                    await telegram_bot.send_alert(screenshot_set, analysis)

                    # Verify Telegram alert
                    mock_app.bot.send_media_group.assert_called()
                    call_args = mock_app.bot.send_media_group.call_args

                    # Verify alert sent to configured chat IDs
                    assert call_args.kwargs["chat_id"] in [
                        int(cid) for cid in telegram_config.chat_ids
                    ]

                    # Verify media group contains 3 photos
                    media_group = call_args.kwargs["media"]
                    assert len(media_group) == 3

                    # Verify first photo has caption with alert details
                    first_photo_caption = media_group[0].caption
                    assert "HAREKET ALGILANDI" in first_photo_caption
                    assert "dusuk" in first_photo_caption.lower() or "Düşük" in first_photo_caption
                    assert "insan" in first_photo_caption.lower()

            # Cleanup
            await mqtt_client.disconnect()
            assert mqtt_client.is_connected is False

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_pipeline_with_high_threat_detection(
        self,
        mock_openai_class,
        llm_config,
        mqtt_config,
        telegram_config
    ):
        """Test full pipeline with high threat level detection."""
        # Setup camera with motion
        camera = MockCamera()
        screenshot_set = ScreenshotSet(
            before=camera.read()[1],
            now=camera.generate_motion_frame(motion_type="person"),
            after=camera.generate_motion_frame(motion_type="person"),
            timestamp=datetime.now()
        )

        # Setup LLM with high threat response
        mock_response_json = MockOpenAI.create_valid_motion_response(
            gercek_hareket=True,
            guven_skoru=0.98,
            nesneler=["insan", "silah"],
            tehdit="yuksek"
        )
        mock_client = MockOpenAI(response_json=mock_response_json)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        analysis = await analyzer.analyze(screenshot_set)

        # Verify high threat analysis
        assert analysis.gercek_hareket is True
        assert analysis.guven_skoru == 0.98
        assert analysis.tehdit_seviyesi == "yuksek"
        assert "insan" in analysis.tespit_edilen_nesneler
        assert "silah" in analysis.tespit_edilen_nesneler

        # Setup MQTT and publish
        mock_mqtt_module = MockMQTT()

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            mqtt_client = MQTTClient(mqtt_config)
            await mqtt_client.connect()
            await mqtt_client.publish_motion(detected=True, analysis=analysis)

            # Verify MQTT published high threat
            mqtt_broker = mock_mqtt_module.get_last_client()
            threat_messages = mqtt_broker.get_messages_by_topic(
                f"{mqtt_config.topic_prefix}/threat_level/state"
            )
            assert threat_messages[-1].payload == "yuksek"

            # Setup Telegram and send alert
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

                    await telegram_bot.send_alert(screenshot_set, analysis)

                    # Verify high threat alert sent
                    mock_app.bot.send_media_group.assert_called()
                    media_group = mock_app.bot.send_media_group.call_args.kwargs["media"]
                    alert_caption = media_group[0].caption

                    assert "yuksek" in alert_caption.lower() or "Yüksek" in alert_caption
                    assert "98" in alert_caption

            await mqtt_client.disconnect()

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_pipeline_with_false_positive_motion(
        self,
        mock_openai_class,
        llm_config,
        mqtt_config
    ):
        """Test pipeline when LLM determines motion is false positive."""
        # Setup camera with similar frames (no real motion)
        camera = MockCamera()
        screenshot_set = ScreenshotSet(
            before=camera.read()[1],
            now=camera.read()[1],
            after=camera.read()[1],
            timestamp=datetime.now()
        )

        # Setup LLM to return no motion
        mock_response_json = MockOpenAI.create_no_motion_response()
        mock_client = MockOpenAI(response_json=mock_response_json)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        analysis = await analyzer.analyze(screenshot_set)

        # Verify LLM determined no real motion
        assert analysis.gercek_hareket is False
        assert analysis.tespit_edilen_nesneler == []
        assert analysis.tehdit_seviyesi == "yok"

        # Setup MQTT and publish
        mock_mqtt_module = MockMQTT()

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            mqtt_client = MQTTClient(mqtt_config)
            await mqtt_client.connect()
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

            await mqtt_client.disconnect()

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_pipeline_with_multiple_motion_events(
        self,
        mock_openai_class,
        llm_config,
        mqtt_config,
        telegram_config
    ):
        """Test pipeline processing multiple motion events in sequence."""
        camera = MockCamera()
        mock_mqtt_module = MockMQTT()

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            mqtt_client = MQTTClient(mqtt_config)
            await mqtt_client.connect()

            with patch("src.telegram_bot.TELEGRAM_AVAILABLE", True):
                with patch("src.telegram_bot.Application") as mock_app_class:
                    mock_app = AsyncMock()
                    mock_app.bot.send_media_group = AsyncMock()
                    mock_app_builder = MagicMock()
                    mock_app_builder.token.return_value = mock_app_builder
                    mock_app_builder.build.return_value = mock_app
                    mock_app_class.builder.return_value = mock_app_builder

                    telegram_config_fast = TelegramConfig(
                        bot_token=telegram_config.bot_token,
                        chat_ids=telegram_config.chat_ids,
                        rate_limit_seconds=0.1
                    )
                    telegram_bot = TelegramBot(telegram_config_fast)
                    telegram_bot.application = mock_app

                    # Process 3 motion events
                    for i in range(3):
                        # Create screenshot set
                        screenshot_set = ScreenshotSet(
                            before=camera.read()[1],
                            now=camera.generate_motion_frame(motion_type="person"),
                            after=camera.generate_motion_frame(motion_type="person"),
                            timestamp=datetime.now()
                        )

                        # Setup LLM response
                        mock_response_json = MockOpenAI.create_valid_motion_response(
                            gercek_hareket=True,
                            guven_skoru=0.85 + (i * 0.05),
                            nesneler=["insan"],
                            tehdit="dusuk"
                        )
                        mock_client = MockOpenAI(response_json=mock_response_json)
                        mock_openai_class.return_value = mock_client

                        # Analyze
                        analyzer = LLMAnalyzer(llm_config)
                        analysis = await analyzer.analyze(screenshot_set)

                        # Publish to MQTT
                        await mqtt_client.publish_motion(detected=True, analysis=analysis)

                        # Send to Telegram
                        await telegram_bot.send_alert(screenshot_set, analysis)

                    # Verify all events were processed
                    mqtt_broker = mock_mqtt_module.get_last_client()
                    motion_messages = mqtt_broker.get_messages_by_topic(
                        f"{mqtt_config.topic_prefix}/motion/state"
                    )
                    assert len(motion_messages) >= 3

                    # Verify all Telegram alerts sent (rate limiter allows with delay)
                    assert mock_app.bot.send_media_group.call_count == 3

            await mqtt_client.disconnect()

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_pipeline_with_mqtt_discovery(
        self,
        mock_openai_class,
        llm_config,
        mqtt_config,
        telegram_config
    ):
        """Test pipeline with MQTT Home Assistant discovery."""
        camera = MockCamera()
        screenshot_set = ScreenshotSet(
            before=camera.read()[1],
            now=camera.generate_motion_frame(motion_type="person"),
            after=camera.generate_motion_frame(motion_type="person"),
            timestamp=datetime.now()
        )

        # Setup LLM
        mock_response_json = MockOpenAI.create_valid_motion_response()
        mock_client = MockOpenAI(response_json=mock_response_json)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        analysis = await analyzer.analyze(screenshot_set)

        # Setup MQTT
        mock_mqtt_module = MockMQTT()

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            mqtt_client = MQTTClient(mqtt_config)
            await mqtt_client.connect()

            # Publish discovery first
            await mqtt_client.publish_discovery()

            # Verify discovery messages
            mqtt_broker = mock_mqtt_module.get_last_client()
            all_messages = mqtt_broker.get_published_messages()
            discovery_messages = [
                msg for msg in all_messages
                if "/config" in msg.topic and msg.retain
            ]
            assert len(discovery_messages) >= 4

            # Verify motion sensor discovery
            motion_discovery = next(
                (msg for msg in discovery_messages if "motion/config" in msg.topic),
                None
            )
            assert motion_discovery is not None
            config_data = json.loads(motion_discovery.payload)
            assert config_data["device_class"] == "motion"
            assert config_data["state_topic"] == f"{mqtt_config.topic_prefix}/motion/state"

            # Now publish motion event
            await mqtt_client.publish_motion(detected=True, analysis=analysis)

            # Verify motion state published
            motion_messages = mqtt_broker.get_messages_by_topic(
                f"{mqtt_config.topic_prefix}/motion/state"
            )
            assert len(motion_messages) > 0
            assert motion_messages[-1].payload == "ON"

            await mqtt_client.disconnect()

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_pipeline_resilience_to_component_failures(
        self,
        mock_openai_class,
        llm_config,
        mqtt_config,
        telegram_config
    ):
        """Test pipeline resilience when individual components fail."""
        camera = MockCamera()
        screenshot_set = ScreenshotSet(
            before=camera.read()[1],
            now=camera.generate_motion_frame(motion_type="person"),
            after=camera.generate_motion_frame(motion_type="person"),
            timestamp=datetime.now()
        )

        # LLM analysis succeeds
        mock_response_json = MockOpenAI.create_valid_motion_response()
        mock_client = MockOpenAI(response_json=mock_response_json)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        analysis = await analyzer.analyze(screenshot_set)
        assert analysis.gercek_hareket is True

        # MQTT connection fails
        mock_mqtt_module = MockMQTT(fail_connect=True)

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            mqtt_client = MQTTClient(mqtt_config)
            await mqtt_client.connect()

            # MQTT not connected
            assert mqtt_client.is_connected is False

            # MQTT publish should fail
            with pytest.raises(RuntimeError, match="Not connected to MQTT broker"):
                await mqtt_client.publish_motion(detected=True, analysis=analysis)

            # But Telegram should still work independently
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

                    # Telegram alert succeeds despite MQTT failure
                    await telegram_bot.send_alert(screenshot_set, analysis)
                    mock_app.bot.send_media_group.assert_called()

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_pipeline_with_different_camera_resolutions(
        self,
        mock_openai_class,
        llm_config,
        mqtt_config
    ):
        """Test pipeline works with different camera resolutions."""
        resolutions = [
            (640, 480),    # VGA
            (1280, 720),   # HD
            (1920, 1080),  # Full HD
        ]

        mock_mqtt_module = MockMQTT()

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            mqtt_client = MQTTClient(mqtt_config)
            await mqtt_client.connect()

            for width, height in resolutions:
                # Setup camera with specific resolution
                camera = MockCamera(width=width, height=height)
                screenshot_set = ScreenshotSet(
                    before=camera.read()[1],
                    now=camera.generate_motion_frame(motion_type="person"),
                    after=camera.generate_motion_frame(motion_type="person"),
                    timestamp=datetime.now()
                )

                # Setup LLM
                mock_response_json = MockOpenAI.create_valid_motion_response()
                mock_client = MockOpenAI(response_json=mock_response_json)
                mock_openai_class.return_value = mock_client

                # Analyze
                analyzer = LLMAnalyzer(llm_config)
                analysis = await analyzer.analyze(screenshot_set)
                assert analysis.gercek_hareket is True

                # Publish to MQTT
                await mqtt_client.publish_motion(detected=True, analysis=analysis)

                # Verify MQTT published
                mqtt_broker = mock_mqtt_module.get_last_client()
                motion_messages = mqtt_broker.get_messages_by_topic(
                    f"{mqtt_config.topic_prefix}/motion/state"
                )
                assert len(motion_messages) > 0

            await mqtt_client.disconnect()

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_pipeline_with_multiple_chat_ids(
        self,
        mock_openai_class,
        llm_config,
        mqtt_config
    ):
        """Test pipeline sends alerts to multiple Telegram chat IDs."""
        camera = MockCamera()
        screenshot_set = ScreenshotSet(
            before=camera.read()[1],
            now=camera.generate_motion_frame(motion_type="person"),
            after=camera.generate_motion_frame(motion_type="person"),
            timestamp=datetime.now()
        )

        # Setup LLM
        mock_response_json = MockOpenAI.create_valid_motion_response()
        mock_client = MockOpenAI(response_json=mock_response_json)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        analysis = await analyzer.analyze(screenshot_set)

        # Setup MQTT
        mock_mqtt_module = MockMQTT()

        with patch("src.mqtt_client.aiomqtt", mock_mqtt_module):
            mqtt_client = MQTTClient(mqtt_config)
            await mqtt_client.connect()
            await mqtt_client.publish_motion(detected=True, analysis=analysis)

            # Setup Telegram with multiple chat IDs
            telegram_config_multi = TelegramConfig(
                bot_token="test_token",
                chat_ids=["111111111", "222222222", "333333333"],
                rate_limit_seconds=0.1
            )

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

                    # Send alert
                    await telegram_bot.send_alert(screenshot_set, analysis)

                    # Verify alert sent to all 3 chat IDs
                    assert mock_app.bot.send_media_group.call_count == 3

                    sent_chat_ids = [
                        call.kwargs["chat_id"]
                        for call in mock_app.bot.send_media_group.call_args_list
                    ]
                    assert 111111111 in sent_chat_ids
                    assert 222222222 in sent_chat_ids
                    assert 333333333 in sent_chat_ids

            await mqtt_client.disconnect()

    @pytest.mark.asyncio
    @patch("src.llm_analyzer.AsyncOpenAI")
    async def test_pipeline_end_to_end_timing(
        self,
        mock_openai_class,
        llm_config,
        mqtt_config,
        telegram_config
    ):
        """Test pipeline captures timing information correctly."""
        import time

        start_time = time.time()

        # Setup camera and capture frames
        camera = MockCamera()
        screenshot_set = ScreenshotSet(
            before=camera.read()[1],
            now=camera.generate_motion_frame(motion_type="person"),
            after=camera.generate_motion_frame(motion_type="person"),
            timestamp=datetime.now()
        )

        # Setup LLM
        mock_response_json = MockOpenAI.create_valid_motion_response()
        mock_client = MockOpenAI(response_json=mock_response_json)
        mock_openai_class.return_value = mock_client

        analyzer = LLMAnalyzer(llm_config)
        analysis = await analyzer.analyze(screenshot_set)

        # Verify timing is tracked
        assert analysis.processing_time > 0
        assert isinstance(analysis.processing_time, float)

        # Verify timestamp is in screenshot set
        assert screenshot_set.timestamp is not None
        assert isinstance(screenshot_set.timestamp, datetime)

        # Verify total pipeline time is reasonable
        total_time = time.time() - start_time
        assert total_time < 10  # Should complete quickly with mocks
