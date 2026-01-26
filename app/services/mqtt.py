"""
MQTT Service for Home Assistant Integration.
Handles connection, discovery, and event publishing.
"""
import json
import logging
import threading
import time
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt
from app.models.config import MqttConfig
from app.services.settings import get_settings_service

logger = logging.getLogger(__name__)

class MqttService:
    """
    MQTT Service for Home Assistant Integration.
    """
    
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.settings_service = get_settings_service()
        self.connected = False
        self._lock = threading.Lock()
        self._loop_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._reconnect_lock = threading.Lock()
        self._reconnecting = False
        
        logger.info("MqttService initialized")

    def start(self):
        """Start MQTT client if enabled."""
        config = self.settings_service.load_config().mqtt
        if not config.enabled:
            logger.info("MQTT disabled, skipping start")
            return

        with self._lock:
            if self.client:
                return

            self._stop_event.clear()
            self._connect(config)

    def stop(self):
        """Stop MQTT client."""
        with self._lock:
            if self.client:
                logger.info("Stopping MQTT client...")
                self._stop_event.set()
                self.client.loop_stop()
                self.client.disconnect()
                self.client = None
                self.connected = False

    def restart(self):
        """Restart MQTT client (e.g. after config change)."""
        self.stop()
        self.start()

    def _connect(self, config: MqttConfig):
        """Internal connection logic."""
        try:
            client_id = f"thermal_vision_{int(time.time())}"
            self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
            
            if config.username:
                self.client.username_pw_set(config.username, config.password)
            else:
                logger.info("Connecting to MQTT anonymously (no username provided)")
            
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.reconnect_delay_set(min_delay=1, max_delay=30)
            
            logger.info(f"Connecting to MQTT broker at {config.host}:{config.port}...")
            self.client.connect(config.host, config.port, 60)
            self.client.loop_start()
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self.client = None

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker")
            self.connected = True
            # Publish discovery config on connect
            self.publish_discovery()
        else:
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
            self.connected = False

    def _on_disconnect(self, client, userdata, rc):
        logger.info(f"Disconnected from MQTT broker (rc={rc})")
        self.connected = False
        if self._stop_event.is_set():
            return
        if not self.client:
            return
        self._start_reconnect()

    def _start_reconnect(self) -> None:
        """Start a reconnect loop if not already running."""
        with self._reconnect_lock:
            if self._reconnecting:
                return
            self._reconnecting = True

        def _reconnect_loop():
            delay = 1
            try:
                while not self._stop_event.is_set():
                    try:
                        logger.info("Attempting MQTT reconnect...")
                        if self.client:
                            self.client.reconnect()
                            return
                    except Exception as exc:
                        logger.warning(f"MQTT reconnect failed: {exc}")
                        time.sleep(delay)
                        delay = min(delay * 2, 30)
            finally:
                with self._reconnect_lock:
                    self._reconnecting = False

        threading.Thread(target=_reconnect_loop, daemon=True).start()

    def publish_discovery(self):
        """
        Publish Home Assistant Discovery messages.
        Creates sensors and binary_sensors for each camera.
        """
        if not self.client or not self.connected:
            return

        config = self.settings_service.load_config()
        mqtt_config = config.mqtt
        prefix = mqtt_config.topic_prefix

        # Device info
        device_info = {
            "identifiers": ["thermal_dual_vision"],
            "name": "Thermal Dual Vision",
            "manufacturer": "Custom",
            "model": "v2.1.0",
            "sw_version": "2.1.0"
        }

        # Global System Sensors
        self._publish_ha_config(
            component="binary_sensor",
            object_id="system_status",
            config={
                "name": "System Status",
                "device_class": "connectivity",
                "state_topic": f"{prefix}/status",
                "unique_id": "tdv_system_status",
                "device": device_info
            }
        )

        # Per-camera entities
        # We need to fetch cameras. Since we are in a service, we can't easily import camera_crud_service 
        # without circular imports if not careful. Better to pass cameras or fetch from DB.
        # For simplicity, we'll import here.
        from app.db.session import get_session
        from app.services.camera_crud import get_camera_crud_service
        
        db = next(get_session())
        try:
            camera_service = get_camera_crud_service()
            cameras = camera_service.get_cameras(db)
            
            for cam in cameras:
                safe_id = cam.id.replace("-", "_")
                
                # Motion/Person Binary Sensor
                self._publish_ha_config(
                    component="binary_sensor",
                    object_id=f"person_detected_{safe_id}",
                    config={
                        "name": f"{cam.name} Person Detected",
                        "device_class": "motion",
                        "state_topic": f"{prefix}/camera/{cam.id}/person",
                        "unique_id": f"tdv_person_{safe_id}",
                        "device": device_info,
                        "expire_after": 30  # Auto-off after 30s if no update
                    }
                )

                # Last Event Summary Sensor
                self._publish_ha_config(
                    component="sensor",
                    object_id=f"last_event_{safe_id}",
                    config={
                        "name": f"{cam.name} Last Event",
                        "icon": "mdi:text-box-outline",
                        "state_topic": f"{prefix}/camera/{cam.id}/event",
                        "value_template": "{{ value_json.summary | default('No summary') }}",
                        "json_attributes_topic": f"{prefix}/camera/{cam.id}/event",
                        "unique_id": f"tdv_last_event_{safe_id}",
                        "device": device_info
                    }
                )

        except Exception as e:
            logger.error(f"Failed to publish discovery: {e}")
        finally:
            db.close()

        # Publish initial system status
        self.client.publish(f"{prefix}/status", "ON", retain=True)

    def _publish_ha_config(self, component: str, object_id: str, config: Dict[str, Any]):
        """Helper to publish HA discovery config."""
        discovery_topic = f"homeassistant/{component}/tdv/{object_id}/config"
        self.client.publish(discovery_topic, json.dumps(config), retain=True)

    def publish_event(self, event_data: Dict[str, Any]):
        """
        Publish detection event.
        
        Args:
            event_data: Dict with event details (id, camera_id, summary, etc.)
        """
        if not self.client or not self.connected:
            return

        try:
            config = self.settings_service.load_config().mqtt
            prefix = config.topic_prefix
            camera_id = event_data.get("camera_id")

            # 1. Publish binary sensor state ON
            self.client.publish(f"{prefix}/camera/{camera_id}/person", "ON")

            # 2. Publish event details (JSON)
            payload = json.dumps(event_data, default=str)
            self.client.publish(f"{prefix}/camera/{camera_id}/event", payload)
            
            # 3. Publish global event feed
            self.client.publish(f"{prefix}/events", payload)

            # Note: The binary sensor will stay ON until expire_after (configured in discovery)
            # or we can explicitly turn it off after some time if we want logic here.
            # HA `expire_after` is usually cleaner for stateless events.

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")

# Singleton
_mqtt_service: Optional[MqttService] = None

def get_mqtt_service() -> MqttService:
    global _mqtt_service
    if _mqtt_service is None:
        _mqtt_service = MqttService()
    return _mqtt_service
