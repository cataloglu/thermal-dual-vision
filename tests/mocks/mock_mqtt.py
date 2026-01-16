"""Mock MQTT broker for testing MQTT client functionality."""

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock


class MockMQTTMessage:
    """
    Represents a single MQTT message published to the broker.

    Stores all message details for verification in tests.
    """

    def __init__(
        self,
        topic: str,
        payload: Any,
        qos: int = 0,
        retain: bool = False
    ):
        """
        Initialize MQTT message.

        Args:
            topic: Message topic
            payload: Message payload (can be str, bytes, or dict)
            qos: Quality of Service level (0, 1, or 2)
            retain: Whether message should be retained
        """
        self.topic = topic
        self.payload = payload
        self.qos = qos
        self.retain = retain


class MockMQTTClient:
    """
    Mock MQTT client that simulates asyncio_mqtt.Client for testing.

    Provides async context manager protocol and tracks published messages
    for verification in tests.
    """

    def __init__(
        self,
        hostname: str,
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        will: Optional[Any] = None,
        fail_connect: bool = False,
        fail_publish: bool = False
    ):
        """
        Initialize mock MQTT client.

        Args:
            hostname: MQTT broker hostname
            port: MQTT broker port
            username: Username for authentication
            password: Password for authentication
            will: Last Will Testament message
            fail_connect: If True, connection will fail
            fail_publish: If True, publish operations will fail
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.will = will
        self.fail_connect = fail_connect
        self.fail_publish = fail_publish

        self._connected = False
        self._published_messages: List[MockMQTTMessage] = []

        # Create async mock for publish
        self.publish = AsyncMock(side_effect=self._publish)

    async def __aenter__(self):
        """
        Enter async context (connect to broker).

        Returns:
            Self for use in async with statement

        Raises:
            ConnectionError: If fail_connect is True
        """
        if self.fail_connect:
            raise ConnectionError("Failed to connect to MQTT broker")

        self._connected = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit async context (disconnect from broker).

        Args:
            exc_type: Exception type if error occurred
            exc_val: Exception value if error occurred
            exc_tb: Exception traceback if error occurred
        """
        self._connected = False
        return None

    async def _publish(
        self,
        topic: str,
        payload: Any = None,
        qos: int = 0,
        retain: bool = False
    ) -> None:
        """
        Publish a message to the broker.

        Args:
            topic: Message topic
            payload: Message payload
            qos: Quality of Service level
            retain: Whether message should be retained

        Raises:
            RuntimeError: If fail_publish is True or client not connected
        """
        if not self._connected:
            raise RuntimeError("Client not connected")

        if self.fail_publish:
            raise RuntimeError("Failed to publish message")

        # Store message for verification
        message = MockMQTTMessage(
            topic=topic,
            payload=payload,
            qos=qos,
            retain=retain
        )
        self._published_messages.append(message)

    def get_published_messages(self) -> List[MockMQTTMessage]:
        """
        Get all messages published to this broker.

        Returns:
            List of published messages
        """
        return self._published_messages.copy()

    def get_messages_by_topic(self, topic: str) -> List[MockMQTTMessage]:
        """
        Get all messages published to a specific topic.

        Args:
            topic: Topic to filter by

        Returns:
            List of messages published to the topic
        """
        return [msg for msg in self._published_messages if msg.topic == topic]

    def get_last_message(self, topic: Optional[str] = None) -> Optional[MockMQTTMessage]:
        """
        Get the most recent published message.

        Args:
            topic: Optional topic to filter by

        Returns:
            Most recent message, or None if no messages
        """
        messages = self.get_messages_by_topic(topic) if topic else self._published_messages
        return messages[-1] if messages else None

    def clear_published_messages(self) -> None:
        """Clear all stored published messages."""
        self._published_messages.clear()

    def is_connected(self) -> bool:
        """
        Check if client is connected.

        Returns:
            True if connected, False otherwise
        """
        return self._connected


class MockMQTTWill:
    """
    Mock Last Will Testament message for MQTT.

    Stores LWT configuration for verification in tests.
    """

    def __init__(
        self,
        topic: str,
        payload: Any,
        qos: int = 0,
        retain: bool = False
    ):
        """
        Initialize LWT message.

        Args:
            topic: Topic for LWT message
            payload: Payload for LWT message
            qos: Quality of Service level
            retain: Whether LWT should be retained
        """
        self.topic = topic
        self.payload = payload
        self.qos = qos
        self.retain = retain


class MockMQTT:
    """
    Mock MQTT broker module that simulates asyncio_mqtt for testing.

    Provides Client and Will classes that match the asyncio_mqtt API.
    Use this to replace the aiomqtt module in tests via mocking.
    """

    def __init__(
        self,
        fail_connect: bool = False,
        fail_publish: bool = False
    ):
        """
        Initialize mock MQTT broker.

        Args:
            fail_connect: If True, connections will fail
            fail_publish: If True, publish operations will fail
        """
        self.fail_connect = fail_connect
        self.fail_publish = fail_publish
        self._clients: List[MockMQTTClient] = []

        # Expose Client and Will as attributes
        self.Client = self._create_client
        self.Will = MockMQTTWill

    def _create_client(self, **kwargs: Any) -> MockMQTTClient:
        """
        Create a new mock MQTT client.

        Args:
            **kwargs: Client configuration parameters

        Returns:
            New MockMQTTClient instance
        """
        # Inject failure modes
        kwargs['fail_connect'] = self.fail_connect
        kwargs['fail_publish'] = self.fail_publish

        client = MockMQTTClient(**kwargs)
        self._clients.append(client)
        return client

    def get_all_clients(self) -> List[MockMQTTClient]:
        """
        Get all clients created by this broker.

        Returns:
            List of all mock clients
        """
        return self._clients.copy()

    def get_last_client(self) -> Optional[MockMQTTClient]:
        """
        Get the most recently created client.

        Returns:
            Most recent client, or None if no clients created
        """
        return self._clients[-1] if self._clients else None

    def get_all_published_messages(self) -> List[MockMQTTMessage]:
        """
        Get all messages published across all clients.

        Returns:
            List of all published messages from all clients
        """
        messages = []
        for client in self._clients:
            messages.extend(client.get_published_messages())
        return messages

    def set_error_mode(
        self,
        fail_connect: bool = False,
        fail_publish: bool = False
    ) -> None:
        """
        Configure which operations should fail.

        Args:
            fail_connect: If True, future connections will fail
            fail_publish: If True, future publish operations will fail
        """
        self.fail_connect = fail_connect
        self.fail_publish = fail_publish
