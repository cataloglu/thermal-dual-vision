"""Unit tests for MQTT client with mock broker."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.config import MQTTConfig
from src.mqtt_client import MQTTClient


@pytest.fixture
def mqtt_config() -> MQTTConfig:
    """Create test MQTT configuration."""
    return MQTTConfig(
        host="test-broker",
        port=1883,
        username="test_user",
        password="test_pass",
        topic_prefix="test_motion",
        discovery=True,
        discovery_prefix="homeassistant",
        qos=1
    )


@pytest.fixture
def mock_aiomqtt():
    """Mock asyncio_mqtt module."""
    with patch("src.mqtt_client.aiomqtt") as mock:
        # Create mock client
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.publish = AsyncMock()

        # Create mock Will class
        mock_will = Mock()
        mock.Will = Mock(return_value=mock_will)

        # Mock Client constructor
        mock.Client = Mock(return_value=mock_client)

        yield mock


@pytest.fixture
def mqtt_client(mqtt_config: MQTTConfig) -> MQTTClient:
    """Create MQTT client instance."""
    return MQTTClient(mqtt_config)


class TestMQTTClientInit:
    """Test MQTT client initialization."""

    def test_init_creates_client(self, mqtt_config: MQTTConfig):
        """Test that initialization creates client with correct config."""
        client = MQTTClient(mqtt_config)

        assert client.config == mqtt_config
        assert client._client is None
        assert client._connected is False
        assert client._should_reconnect is True
        assert client._on_connect_callbacks == []
        assert client._on_disconnect_callbacks == []

    def test_init_logs_broker_info(self, mqtt_config: MQTTConfig):
        """Test that initialization logs broker information."""
        with patch("src.mqtt_client.logger") as mock_logger:
            MQTTClient(mqtt_config)
            mock_logger.info.assert_called_once()
            assert "test-broker:1883" in str(mock_logger.info.call_args)


class TestMQTTClientConnect:
    """Test MQTT client connection."""

    @pytest.mark.asyncio
    async def test_connect_without_aiomqtt_raises_error(
        self, mqtt_client: MQTTClient
    ):
        """Test that connect raises error when asyncio-mqtt is not available."""
        with patch("src.mqtt_client.aiomqtt", None):
            with pytest.raises(RuntimeError, match="asyncio-mqtt is not installed"):
                await mqtt_client.connect()

    @pytest.mark.asyncio
    async def test_connect_already_connected_returns_early(
        self, mqtt_client: MQTTClient, mock_aiomqtt
    ):
        """Test that connect returns early if already connected."""
        mqtt_client._connected = True

        with patch("src.mqtt_client.logger") as mock_logger:
            await mqtt_client.connect()
            mock_logger.warning.assert_called_once()
            assert "Already connected" in str(mock_logger.warning.call_args)

    @pytest.mark.asyncio
    async def test_connect_success(
        self, mqtt_client: MQTTClient, mqtt_config: MQTTConfig, mock_aiomqtt
    ):
        """Test successful connection to MQTT broker."""
        await mqtt_client.connect()

        # Verify client was created with correct parameters
        mock_aiomqtt.Client.assert_called_once()
        call_kwargs = mock_aiomqtt.Client.call_args.kwargs

        assert call_kwargs["hostname"] == mqtt_config.host
        assert call_kwargs["port"] == mqtt_config.port
        assert call_kwargs["username"] == mqtt_config.username
        assert call_kwargs["password"] == mqtt_config.password
        assert call_kwargs["will"] is not None

        # Verify connection state
        assert mqtt_client._connected is True
        assert mqtt_client._client is not None

        # Verify LWT was created
        mock_aiomqtt.Will.assert_called_once()
        will_kwargs = mock_aiomqtt.Will.call_args.kwargs
        assert will_kwargs["topic"] == f"{mqtt_config.topic_prefix}/availability"
        assert will_kwargs["payload"] == "offline"
        assert will_kwargs["qos"] == mqtt_config.qos
        assert will_kwargs["retain"] is True

        # Verify online availability was published
        mock_client = mock_aiomqtt.Client.return_value
        publish_calls = [call for call in mock_client.publish.call_args_list]
        assert len(publish_calls) >= 1

        # Check first publish call is availability
        first_call = publish_calls[0]
        assert first_call[0][0] == f"{mqtt_config.topic_prefix}/availability"
        assert first_call.kwargs["payload"] == "online"

    @pytest.mark.asyncio
    async def test_connect_triggers_callbacks(
        self, mqtt_client: MQTTClient, mock_aiomqtt
    ):
        """Test that connect triggers on_connect callbacks."""
        callback_sync = Mock()
        callback_async = AsyncMock()

        mqtt_client.on_connect(callback_sync)
        mqtt_client.on_connect(callback_async)

        await mqtt_client.connect()

        callback_sync.assert_called_once()
        callback_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure_schedules_reconnect(
        self, mqtt_client: MQTTClient, mock_aiomqtt
    ):
        """Test that connection failure schedules automatic reconnection."""
        # Make connection fail
        mock_client = mock_aiomqtt.Client.return_value
        mock_client.__aenter__.side_effect = Exception("Connection failed")

        # Start connection (should not raise, but schedule reconnect)
        with patch.object(mqtt_client, "_reconnect_loop") as mock_reconnect:
            mock_reconnect_task = AsyncMock()
            with patch("asyncio.create_task", return_value=mock_reconnect_task):
                await mqtt_client.connect()

        # Verify reconnect was scheduled
        assert mock_reconnect.called
        assert mqtt_client._connected is False
        assert mqtt_client._reconnect_task is not None


class TestMQTTClientDisconnect:
    """Test MQTT client disconnection."""

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self, mqtt_client: MQTTClient):
        """Test disconnect when not connected."""
        await mqtt_client.disconnect()
        assert mqtt_client._connected is False

    @pytest.mark.asyncio
    async def test_disconnect_success(
        self, mqtt_client: MQTTClient, mqtt_config: MQTTConfig, mock_aiomqtt
    ):
        """Test successful disconnection."""
        # First connect
        await mqtt_client.connect()
        mock_client = mqtt_client._client

        # Then disconnect
        await mqtt_client.disconnect()

        # Verify offline status was published
        publish_calls = [call for call in mock_client.publish.call_args_list]
        offline_call = [
            call for call in publish_calls
            if call.kwargs.get("payload") == "offline"
        ]
        assert len(offline_call) >= 1

        # Verify client was disconnected
        mock_client.__aexit__.assert_called()

        # Verify state
        assert mqtt_client._connected is False
        assert mqtt_client._client is None
        assert mqtt_client._should_reconnect is False

    @pytest.mark.asyncio
    async def test_disconnect_cancels_reconnect_task(
        self, mqtt_client: MQTTClient, mock_aiomqtt
    ):
        """Test that disconnect cancels ongoing reconnection attempts."""
        # First connect to establish connection
        await mqtt_client.connect()

        # Create a real async task that we can track
        task_cancelled = False

        async def fake_reconnect_loop():
            nonlocal task_cancelled
            try:
                await asyncio.sleep(100)  # Sleep for a long time
            except asyncio.CancelledError:
                task_cancelled = True
                raise

        # Create a real asyncio task
        reconnect_task = asyncio.create_task(fake_reconnect_loop())
        mqtt_client._reconnect_task = reconnect_task

        # Disconnect should cancel the task
        await mqtt_client.disconnect()

        # Verify task was cancelled
        assert reconnect_task.cancelled() or task_cancelled
        assert mqtt_client._reconnect_task is None

    @pytest.mark.asyncio
    async def test_disconnect_triggers_callbacks(
        self, mqtt_client: MQTTClient, mock_aiomqtt
    ):
        """Test that disconnect triggers on_disconnect callbacks."""
        callback_sync = Mock()
        callback_async = AsyncMock()

        mqtt_client.on_disconnect(callback_sync)
        mqtt_client.on_disconnect(callback_async)

        # Connect first
        await mqtt_client.connect()

        # Then disconnect
        await mqtt_client.disconnect()

        callback_sync.assert_called_once()
        callback_async.assert_called_once()


class TestMQTTClientDiscovery:
    """Test Home Assistant auto-discovery."""

    @pytest.mark.asyncio
    async def test_publish_discovery_not_connected_raises_error(
        self, mqtt_client: MQTTClient
    ):
        """Test that publish_discovery raises error when not connected."""
        with pytest.raises(RuntimeError, match="Not connected to MQTT broker"):
            await mqtt_client.publish_discovery()

    @pytest.mark.asyncio
    async def test_publish_discovery_disabled_skips(
        self, mqtt_client: MQTTClient, mock_aiomqtt
    ):
        """Test that discovery is skipped when disabled in config."""
        mqtt_client.config.discovery = False
        await mqtt_client.connect()

        await mqtt_client.publish_discovery()

        # Verify no discovery messages were published (only availability)
        mock_client = mqtt_client._client
        assert mock_client.publish.call_count == 1  # Only availability

    @pytest.mark.asyncio
    async def test_publish_discovery_success(
        self, mqtt_client: MQTTClient, mqtt_config: MQTTConfig, mock_aiomqtt
    ):
        """Test successful publishing of discovery messages."""
        await mqtt_client.connect()
        await mqtt_client.publish_discovery()

        mock_client = mqtt_client._client
        publish_calls = [call for call in mock_client.publish.call_args_list]

        # Should have 5 publishes: 1 availability + 4 discovery configs
        assert len(publish_calls) >= 5

        # Extract discovery publishes (skip first availability)
        discovery_calls = publish_calls[1:]

        # Verify topics
        topics = [call[0][0] for call in discovery_calls]
        device_id = f"{mqtt_config.topic_prefix}_detector"

        expected_topics = [
            f"{mqtt_config.discovery_prefix}/binary_sensor/{device_id}/motion/config",
            f"{mqtt_config.discovery_prefix}/sensor/{device_id}/threat_level/config",
            f"{mqtt_config.discovery_prefix}/sensor/{device_id}/confidence/config",
            f"{mqtt_config.discovery_prefix}/sensor/{device_id}/last_analysis/config",
        ]

        for expected_topic in expected_topics:
            assert expected_topic in topics

    @pytest.mark.asyncio
    async def test_discovery_payloads_valid_json(
        self, mqtt_client: MQTTClient, mock_aiomqtt
    ):
        """Test that discovery payloads are valid JSON."""
        await mqtt_client.connect()
        await mqtt_client.publish_discovery()

        mock_client = mqtt_client._client
        publish_calls = [call for call in mock_client.publish.call_args_list]

        # Check discovery messages (skip availability)
        for call in publish_calls[1:]:
            payload = call.kwargs["payload"]
            # Should be valid JSON
            parsed = json.loads(payload)
            assert isinstance(parsed, dict)
            assert "name" in parsed
            assert "unique_id" in parsed
            assert "device" in parsed


class TestMQTTClientPublishMotion:
    """Test motion event publishing."""

    @pytest.mark.asyncio
    async def test_publish_motion_not_connected_raises_error(
        self, mqtt_client: MQTTClient
    ):
        """Test that publish_motion raises error when not connected."""
        with pytest.raises(RuntimeError, match="Not connected to MQTT broker"):
            await mqtt_client.publish_motion(True)

    @pytest.mark.asyncio
    async def test_publish_motion_detected_on(
        self, mqtt_client: MQTTClient, mqtt_config: MQTTConfig, mock_aiomqtt
    ):
        """Test publishing motion detected (ON) state."""
        await mqtt_client.connect()
        await mqtt_client.publish_motion(True)

        mock_client = mqtt_client._client
        publish_calls = [call for call in mock_client.publish.call_args_list]

        # Find motion state publish
        motion_calls = [
            call for call in publish_calls
            if f"{mqtt_config.topic_prefix}/motion/state" in str(call)
        ]

        assert len(motion_calls) >= 1
        motion_call = motion_calls[0]
        assert motion_call.kwargs["payload"] == "ON"

    @pytest.mark.asyncio
    async def test_publish_motion_detected_off(
        self, mqtt_client: MQTTClient, mqtt_config: MQTTConfig, mock_aiomqtt
    ):
        """Test publishing motion not detected (OFF) state."""
        await mqtt_client.connect()
        await mqtt_client.publish_motion(False)

        mock_client = mqtt_client._client
        publish_calls = [call for call in mock_client.publish.call_args_list]

        # Find motion state publish
        motion_calls = [
            call for call in publish_calls
            if f"{mqtt_config.topic_prefix}/motion/state" in str(call)
        ]

        assert len(motion_calls) >= 1
        motion_call = motion_calls[0]
        assert motion_call.kwargs["payload"] == "OFF"

    @pytest.mark.asyncio
    async def test_publish_motion_with_analysis(
        self, mqtt_client: MQTTClient, mqtt_config: MQTTConfig, mock_aiomqtt
    ):
        """Test publishing motion with analysis results."""
        # Create mock analysis result
        analysis = Mock()
        analysis.threat_level = "medium"
        analysis.confidence = 0.85
        analysis.timestamp = "2024-01-01T12:00:00"

        await mqtt_client.connect()
        await mqtt_client.publish_motion(True, analysis)

        mock_client = mqtt_client._client
        publish_calls = [call for call in mock_client.publish.call_args_list]

        # Verify motion state
        motion_calls = [
            call for call in publish_calls
            if f"{mqtt_config.topic_prefix}/motion/state" in str(call)
        ]
        assert len(motion_calls) >= 1

        # Verify threat level
        threat_calls = [
            call for call in publish_calls
            if f"{mqtt_config.topic_prefix}/threat_level/state" in str(call)
        ]
        assert len(threat_calls) >= 1
        assert threat_calls[0].kwargs["payload"] == "medium"

        # Verify confidence (should be converted to percentage)
        confidence_calls = [
            call for call in publish_calls
            if f"{mqtt_config.topic_prefix}/confidence/state" in str(call)
        ]
        assert len(confidence_calls) >= 1
        assert confidence_calls[0].kwargs["payload"] == "85"

        # Verify timestamp
        analysis_calls = [
            call for call in publish_calls
            if f"{mqtt_config.topic_prefix}/last_analysis/state" in str(call)
        ]
        assert len(analysis_calls) >= 1
        assert analysis_calls[0].kwargs["payload"] == "2024-01-01T12:00:00"


class TestMQTTClientPublishState:
    """Test generic state publishing."""

    @pytest.mark.asyncio
    async def test_publish_state_not_connected_raises_error(
        self, mqtt_client: MQTTClient
    ):
        """Test that publish_state raises error when not connected."""
        with pytest.raises(RuntimeError, match="Not connected to MQTT broker"):
            await mqtt_client.publish_state("custom/topic", {"key": "value"})

    @pytest.mark.asyncio
    async def test_publish_state_success(
        self, mqtt_client: MQTTClient, mqtt_config: MQTTConfig, mock_aiomqtt
    ):
        """Test successful state publishing."""
        state = {"sensor": "data", "value": 123}

        await mqtt_client.connect()
        await mqtt_client.publish_state("custom/sensor", state)

        mock_client = mqtt_client._client
        publish_calls = [call for call in mock_client.publish.call_args_list]

        # Find custom state publish
        custom_calls = [
            call for call in publish_calls
            if f"{mqtt_config.topic_prefix}/custom/sensor" in str(call)
        ]

        assert len(custom_calls) >= 1
        custom_call = custom_calls[0]

        # Verify payload is JSON
        payload = json.loads(custom_call.kwargs["payload"])
        assert payload == state


class TestMQTTClientCallbacks:
    """Test callback registration."""

    def test_on_connect_registers_callback(self, mqtt_client: MQTTClient):
        """Test on_connect callback registration."""
        callback = Mock()
        mqtt_client.on_connect(callback)

        assert callback in mqtt_client._on_connect_callbacks

    def test_on_connect_prevents_duplicates(self, mqtt_client: MQTTClient):
        """Test that same callback is not registered twice."""
        callback = Mock()
        mqtt_client.on_connect(callback)
        mqtt_client.on_connect(callback)

        assert mqtt_client._on_connect_callbacks.count(callback) == 1

    def test_on_disconnect_registers_callback(self, mqtt_client: MQTTClient):
        """Test on_disconnect callback registration."""
        callback = Mock()
        mqtt_client.on_disconnect(callback)

        assert callback in mqtt_client._on_disconnect_callbacks

    def test_on_disconnect_prevents_duplicates(self, mqtt_client: MQTTClient):
        """Test that same callback is not registered twice."""
        callback = Mock()
        mqtt_client.on_disconnect(callback)
        mqtt_client.on_disconnect(callback)

        assert mqtt_client._on_disconnect_callbacks.count(callback) == 1


class TestMQTTClientProperties:
    """Test client properties."""

    def test_is_connected_false_initially(self, mqtt_client: MQTTClient):
        """Test that is_connected is False initially."""
        assert mqtt_client.is_connected is False

    @pytest.mark.asyncio
    async def test_is_connected_true_after_connect(
        self, mqtt_client: MQTTClient, mock_aiomqtt
    ):
        """Test that is_connected is True after successful connection."""
        await mqtt_client.connect()
        assert mqtt_client.is_connected is True

    @pytest.mark.asyncio
    async def test_is_connected_false_after_disconnect(
        self, mqtt_client: MQTTClient, mock_aiomqtt
    ):
        """Test that is_connected is False after disconnection."""
        await mqtt_client.connect()
        await mqtt_client.disconnect()
        assert mqtt_client.is_connected is False


class TestMQTTClientReconnect:
    """Test automatic reconnection."""

    @pytest.mark.asyncio
    async def test_reconnect_loop_retries_connection(
        self, mqtt_client: MQTTClient, mock_aiomqtt
    ):
        """Test that reconnect loop retries connection."""
        # Track connection attempts
        connect_attempts = []

        original_connect = mqtt_client.connect

        async def mock_connect():
            connect_attempts.append(asyncio.get_event_loop().time())
            if len(connect_attempts) < 3:
                # Fail first 2 attempts
                raise Exception("Connection failed")
            # Succeed on 3rd attempt
            mqtt_client._connected = True

        # Reduce delays for faster testing
        mqtt_client._should_reconnect = True

        with patch.object(mqtt_client, "connect", side_effect=mock_connect):
            # Start reconnect loop
            reconnect_task = asyncio.create_task(mqtt_client._reconnect_loop())

            # Wait for connection to succeed (with timeout)
            try:
                await asyncio.wait_for(reconnect_task, timeout=5.0)
            except asyncio.TimeoutError:
                # If timeout, cancel the task
                reconnect_task.cancel()
                try:
                    await reconnect_task
                except asyncio.CancelledError:
                    pass

        # Verify multiple connection attempts were made
        assert len(connect_attempts) >= 2, f"Expected at least 2 connection attempts, got {len(connect_attempts)}"

    @pytest.mark.asyncio
    async def test_reconnect_loop_stops_when_connected(
        self, mqtt_client: MQTTClient, mock_aiomqtt
    ):
        """Test that reconnect loop stops when connection succeeds."""
        # Mock successful connection
        async def mock_connect():
            mqtt_client._connected = True

        with patch.object(mqtt_client, "connect", side_effect=mock_connect):
            # Start and complete reconnect loop
            await mqtt_client._reconnect_loop()

        # Loop should have exited naturally
        assert mqtt_client._reconnect_task is None

    @pytest.mark.asyncio
    async def test_reconnect_loop_stops_on_cancel(
        self, mqtt_client: MQTTClient, mock_aiomqtt
    ):
        """Test that reconnect loop handles cancellation."""
        # Mock connect to always fail
        async def mock_connect():
            raise Exception("Connection failed")

        with patch.object(mqtt_client, "connect", side_effect=mock_connect):
            # Start reconnect loop
            reconnect_task = asyncio.create_task(mqtt_client._reconnect_loop())

            # Let it run briefly
            await asyncio.sleep(0.05)

            # Cancel it
            reconnect_task.cancel()

            # Should handle cancellation gracefully
            with pytest.raises(asyncio.CancelledError):
                await reconnect_task


class TestMQTTClientQoS:
    """Test QoS settings."""

    @pytest.mark.asyncio
    async def test_publishes_use_configured_qos(
        self, mqtt_client: MQTTClient, mqtt_config: MQTTConfig, mock_aiomqtt
    ):
        """Test that all publishes use configured QoS."""
        await mqtt_client.connect()

        mock_client = mqtt_client._client
        publish_calls = [call for call in mock_client.publish.call_args_list]

        # All publishes should use configured QoS
        for call in publish_calls:
            assert call.kwargs["qos"] == mqtt_config.qos
