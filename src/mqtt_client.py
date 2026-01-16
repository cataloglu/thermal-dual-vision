"""MQTT client for Home Assistant integration."""

import asyncio
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    import asyncio_mqtt as aiomqtt
else:
    try:
        import asyncio_mqtt as aiomqtt
    except ImportError:
        aiomqtt = None  # type: ignore

from src.config import MQTTConfig
from src.logger import get_logger

logger = get_logger("mqtt")


class MQTTClient:
    """
    MQTT client for Home Assistant auto-discovery and state publishing.

    Handles connection lifecycle, auto-discovery messages, and state publishing
    for motion detection events and analysis results.
    """

    def __init__(self, config: MQTTConfig) -> None:
        """
        Initialize MQTT client.

        Args:
            config: MQTT configuration
        """
        self.config = config
        self._client: Optional[Any] = None  # aiomqtt.Client when available
        self._connected = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._on_connect_callbacks: List[Callable] = []
        self._on_disconnect_callbacks: List[Callable] = []

        logger.info(
            f"MQTT client initialized for broker {config.host}:{config.port}"
        )

    async def connect(self) -> None:
        """
        Connect to MQTT broker.

        Establishes connection with configured broker and sets up Last Will Testament.
        """
        raise NotImplementedError("connect() will be implemented in subtask-1-2")

    async def disconnect(self) -> None:
        """
        Disconnect from MQTT broker.

        Cleanly closes connection and cancels reconnection attempts.
        """
        raise NotImplementedError("disconnect() will be implemented in subtask-1-2")

    async def publish_discovery(self) -> None:
        """
        Publish Home Assistant auto-discovery messages.

        Sends discovery configuration for all entities (binary sensor and sensors)
        to enable automatic entity creation in Home Assistant.
        """
        raise NotImplementedError(
            "publish_discovery() will be implemented in phase-2-discovery"
        )

    async def publish_motion(
        self, detected: bool, analysis: Optional[Any] = None
    ) -> None:
        """
        Publish motion detection state and analysis results.

        Args:
            detected: Motion detected flag
            analysis: Optional analysis result from LLM (AnalysisResult type when available)
        """
        raise NotImplementedError(
            "publish_motion() will be implemented in phase-3-publishing"
        )

    async def publish_state(self, state: Dict[str, Any]) -> None:
        """
        Publish generic state to MQTT.

        Args:
            state: State dictionary to publish
        """
        raise NotImplementedError(
            "publish_state() will be implemented in phase-3-publishing"
        )

    def on_connect(self, callback: Callable) -> None:
        """
        Register callback for connection events.

        Args:
            callback: Function to call when connected
        """
        raise NotImplementedError(
            "on_connect() will be implemented in subtask-1-3"
        )

    def on_disconnect(self, callback: Callable) -> None:
        """
        Register callback for disconnection events.

        Args:
            callback: Function to call when disconnected
        """
        raise NotImplementedError(
            "on_disconnect() will be implemented in subtask-1-3"
        )

    @property
    def is_connected(self) -> bool:
        """Check if client is connected to broker."""
        return self._connected
