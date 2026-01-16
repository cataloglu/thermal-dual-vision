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
        self._should_reconnect = True
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
        if aiomqtt is None:
            logger.error("asyncio-mqtt is not installed. Install with: pip install asyncio-mqtt")
            raise RuntimeError("asyncio-mqtt is not installed")

        if self._connected:
            logger.warning("Already connected to MQTT broker")
            return

        try:
            logger.info(f"Connecting to MQTT broker at {self.config.host}:{self.config.port}")

            # Create LWT (Last Will Testament) for unavailable state
            availability_topic = f"{self.config.topic_prefix}/availability"
            will_message = aiomqtt.Will(
                topic=availability_topic,
                payload="offline",
                qos=self.config.qos,
                retain=True
            )

            # Create client with connection parameters
            self._client = aiomqtt.Client(
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username if self.config.username else None,
                password=self.config.password if self.config.password else None,
                will=will_message
            )

            # Connect to broker
            await self._client.__aenter__()

            # Update connection state
            self._connected = True
            logger.info("Successfully connected to MQTT broker")

            # Publish online availability status
            await self._client.publish(
                availability_topic,
                payload="online",
                qos=self.config.qos,
                retain=True
            )

            # Trigger on_connect callbacks
            for callback in self._on_connect_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Error in on_connect callback: {e}")

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self._connected = False
            self._client = None

            # Start reconnect task if auto-reconnect is enabled
            if self._should_reconnect and not self._reconnect_task:
                logger.info("Scheduling automatic reconnection")
                self._reconnect_task = asyncio.create_task(self._reconnect_loop())
            else:
                raise

    async def disconnect(self) -> None:
        """
        Disconnect from MQTT broker.

        Cleanly closes connection and cancels reconnection attempts.
        """
        # Disable auto-reconnect for intentional disconnections
        self._should_reconnect = False

        if not self._connected:
            logger.debug("Already disconnected from MQTT broker")
            return

        try:
            # Cancel any ongoing reconnection attempts
            if self._reconnect_task and not self._reconnect_task.done():
                logger.debug("Cancelling reconnect task")
                self._reconnect_task.cancel()
                try:
                    await self._reconnect_task
                except asyncio.CancelledError:
                    pass
                self._reconnect_task = None

            # Publish offline status before disconnecting
            if self._client:
                try:
                    availability_topic = f"{self.config.topic_prefix}/availability"
                    await self._client.publish(
                        availability_topic,
                        payload="offline",
                        qos=self.config.qos,
                        retain=True
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish offline status: {e}")

                # Disconnect from broker
                try:
                    await self._client.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Error during client disconnect: {e}")

            # Update connection state
            self._connected = False
            self._client = None
            logger.info("Disconnected from MQTT broker")

            # Trigger on_disconnect callbacks
            for callback in self._on_disconnect_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Error in on_disconnect callback: {e}")

        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            self._connected = False
            self._client = None
            raise

    def _build_binary_sensor_discovery(self) -> Dict[str, Any]:
        """
        Build Home Assistant discovery payload for binary_sensor (motion).

        Returns:
            Discovery configuration dictionary for motion binary sensor
        """
        device_id = f"{self.config.topic_prefix}_detector"

        return {
            "name": "Smart Motion",
            "unique_id": f"{device_id}_motion",
            "state_topic": f"{self.config.topic_prefix}/motion/state",
            "device_class": "motion",
            "availability_topic": f"{self.config.topic_prefix}/availability",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device": {
                "identifiers": [device_id],
                "name": "Smart Motion Detector",
                "model": "v1.0",
                "manufacturer": "Custom"
            }
        }

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
            callback: Function to call when connected (can be sync or async)
        """
        if callback not in self._on_connect_callbacks:
            self._on_connect_callbacks.append(callback)
            logger.debug("Registered on_connect callback")

    def on_disconnect(self, callback: Callable) -> None:
        """
        Register callback for disconnection events.

        Args:
            callback: Function to call when disconnected (can be sync or async)
        """
        if callback not in self._on_disconnect_callbacks:
            self._on_disconnect_callbacks.append(callback)
            logger.debug("Registered on_disconnect callback")

    async def _reconnect_loop(self) -> None:
        """
        Automatic reconnection loop with exponential backoff.

        Attempts to reconnect to MQTT broker with increasing delays
        between attempts until successful or cancelled.
        """
        delay = 1.0  # Initial delay in seconds
        max_delay = 60.0  # Maximum delay in seconds
        backoff = 2.0  # Backoff multiplier
        attempt = 1

        logger.info("Starting automatic reconnection loop")

        while self._should_reconnect and not self._connected:
            try:
                logger.info(
                    f"Reconnection attempt {attempt} in {delay:.1f} seconds..."
                )
                await asyncio.sleep(delay)

                # Attempt to reconnect
                logger.info(f"Attempting to reconnect to MQTT broker...")
                await self.connect()

                if self._connected:
                    logger.info("Successfully reconnected to MQTT broker")
                    self._reconnect_task = None
                    return

            except asyncio.CancelledError:
                logger.info("Reconnection loop cancelled")
                raise
            except Exception as e:
                logger.warning(
                    f"Reconnection attempt {attempt} failed: {e}"
                )
                # Increase delay with exponential backoff
                delay = min(delay * backoff, max_delay)
                attempt += 1

        logger.info("Reconnection loop ended")
        self._reconnect_task = None

    @property
    def is_connected(self) -> bool:
        """Check if client is connected to broker."""
        return self._connected
