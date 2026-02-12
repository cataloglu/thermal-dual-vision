"""
MQTT Service for Home Assistant Integration.
Handles connection, discovery, and event publishing.
"""
import json
import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt
from app.models.config import MqttConfig
from app.services.settings import get_settings_service

logger = logging.getLogger(__name__)

class MqttService:
    """
    MQTT Service for Home Assistant Integration.
    """
    
    @staticmethod
    def _normalize_credential(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        normalized = value.strip()
        if normalized.lower() in {"null", "none"}:
            return None
        return normalized
    
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.settings_service = get_settings_service()
        self.connected = False
        self.availability_topic: Optional[str] = None
        self._lock = threading.Lock()
        self._loop_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._reconnect_lock = threading.Lock()
        self._reconnecting = False
        
        # Monitoring state (NEW)
        self.active_topics: set = set()
        self.publish_count: int = 0
        self.last_messages: Dict[str, Dict[str, Any]] = {}  # topic → {payload, timestamp}
        self.connected_at: Optional[datetime] = None
        self.last_error: Optional[str] = None
        
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

            self.availability_topic = f"{config.topic_prefix}/availability"
            self.client.will_set(self.availability_topic, "offline", retain=True)

            username = self._normalize_credential(config.username)
            password = self._normalize_credential(config.password)
            
            if username:
                self.client.username_pw_set(username, password)
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
            self.connected_at = datetime.utcnow()
            if self.availability_topic:
                self.client.publish(self.availability_topic, "online", retain=True)
                self._track_publish(self.availability_topic, "online")
            # Publish discovery config on connect
            self.publish_discovery()
        else:
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
            self.connected = False
            self.last_error = f"Connection failed (rc={rc})"

    def _on_disconnect(self, client, userdata, rc):
        logger.info(f"Disconnected from MQTT broker (rc={rc})")
        self.connected = False
        if rc == 5:
            logger.warning("MQTT auth failed (rc=5). If using HA Mosquitto, check credentials or allow anonymous.")
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
        availability_topic = self.availability_topic or f"{prefix}/availability"
        availability_fields = {
            "availability_topic": availability_topic,
            "payload_available": "online",
            "payload_not_available": "offline",
        }

        device_info = self._get_device_info()
        self._publish_system_discovery(prefix, device_info, availability_fields)

        # Per-camera entities
        # We need to fetch cameras. Since we are in a service, we can't easily import camera_crud_service 
        # without circular imports if not careful. Better to pass cameras or fetch from DB.
        # For simplicity, we'll import here.
        from app.db.session import get_session
        from app.db.models import Event
        from app.services.camera_crud import get_camera_crud_service
        
        db = next(get_session())
        try:
            camera_service = get_camera_crud_service()
            cameras = camera_service.get_cameras(db)
            
            for cam in cameras:
                latest = (
                    db.query(Event)
                    .filter_by(camera_id=cam.id)
                    .order_by(Event.timestamp.desc())
                    .first()
                )
                self._publish_camera_discovery(
                    cam=cam,
                    prefix=prefix,
                    device_info=device_info,
                    availability_fields=availability_fields,
                )
                self._publish_camera_state(cam=cam, latest=latest, prefix=prefix)

            # Publish initial system status
            self.client.publish(f"{prefix}/status", "ON", retain=True)

        except Exception as e:
            logger.error(f"Failed to publish discovery: {e}")
        finally:
            db.close()

    def _publish_ha_config(self, component: str, object_id: str, config: Dict[str, Any]):
        """Helper to publish HA discovery config."""
        discovery_topic = f"homeassistant/{component}/tdv/{object_id}/config"
        self.client.publish(discovery_topic, json.dumps(config), retain=True)

    def _clear_ha_config(self, component: str, object_id: str) -> None:
        """Clear HA discovery config (removes entity)."""
        discovery_topic = f"homeassistant/{component}/tdv/{object_id}/config"
        self.client.publish(discovery_topic, "", retain=True)

    def _get_device_info(self) -> Dict[str, str]:
        # Get version from environment (set by Dockerfile)
        import os
        version = os.getenv("ADDON_VERSION", "2.5.2")
        return {
            "identifiers": ["thermal_dual_vision"],
            "name": "Thermal Dual Vision",
            "manufacturer": "Custom",
            "model": f"v{version}",
            "sw_version": version,
        }

    def _publish_system_discovery(
        self,
        prefix: str,
        device_info: Dict[str, str],
        availability_fields: Dict[str, str],
    ) -> None:
        self._publish_ha_config(
            component="binary_sensor",
            object_id="system_status",
            config={
                "name": "System Status",
                "device_class": "connectivity",
                "state_topic": f"{prefix}/status",
                "payload_on": "ON",
                "payload_off": "OFF",
                "unique_id": "tdv_system_status",
                "device": device_info,
                **availability_fields,
            },
        )

    def _publish_camera_discovery(
        self,
        cam: Any,
        prefix: str,
        device_info: Dict[str, str],
        availability_fields: Dict[str, str],
    ) -> None:
        safe_id = cam.id.replace("-", "_")
        
        # Binary sensor: Person detected (1+ person)
        self._publish_ha_config(
            component="binary_sensor",
            object_id=f"person_detected_{safe_id}",
            config={
                "name": f"{cam.name} Person Detected",
                "device_class": "motion",
                "state_topic": f"{prefix}/camera/{cam.id}/person",
                "payload_on": "ON",
                "payload_off": "OFF",
                "off_delay": 30,
                "unique_id": f"tdv_person_{safe_id}",
                "device": device_info,
                **availability_fields,
            },
        )
        
        # Sensor: Person count (0, 1, 2, 3...)
        self._publish_ha_config(
            component="sensor",
            object_id=f"person_count_{safe_id}",
            config={
                "name": f"{cam.name} Person Count",
                "state_topic": f"{prefix}/camera/{cam.id}/person_count",
                "unit_of_measurement": "persons",
                "icon": "mdi:account-multiple",
                "unique_id": f"tdv_person_count_{safe_id}",
                "device": device_info,
                **availability_fields,
            },
        )

        self._publish_ha_config(
            component="sensor",
            object_id=f"last_event_{safe_id}",
            config={
                "name": f"{cam.name} Last Event",
                "icon": "mdi:text-box-outline",
                "state_topic": f"{prefix}/camera/{cam.id}/event",
                "value_template": "{{ value_json.summary | default('No summary', true) }}",
                "json_attributes_topic": f"{prefix}/camera/{cam.id}/event",
                "unique_id": f"tdv_last_event_{safe_id}",
                "device": device_info,
                **availability_fields,
            },
        )

    def _publish_camera_state(self, cam: Any, latest: Optional[Any], prefix: str) -> None:
        self.client.publish(
            f"{prefix}/camera/{cam.id}/person",
            "OFF",
            retain=True,
        )
        if latest:
            summary = latest.summary or "No summary"
            payload = json.dumps(
                {
                    "id": latest.id,
                    "camera_id": latest.camera_id,
                    "timestamp": latest.timestamp.isoformat() + "Z",
                    "confidence": latest.confidence,
                    "event_type": latest.event_type,
                    "summary": summary,
                },
                default=str,
            )
        else:
            payload = json.dumps(
                {
                    "id": None,
                    "camera_id": cam.id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "confidence": 0.0,
                    "event_type": "none",
                    "summary": "Henüz olay yok",
                }
            )
        self.client.publish(
            f"{prefix}/camera/{cam.id}/event",
            payload,
            retain=True,
        )

    def publish_camera_update(self, camera_id: str) -> None:
        """Publish discovery/state for a single camera."""
        if not self.client or not self.connected:
            return
        from app.db.session import get_session
        from app.db.models import Event
        from app.services.camera_crud import get_camera_crud_service

        config = self.settings_service.load_config()
        prefix = config.mqtt.topic_prefix
        availability_topic = self.availability_topic or f"{prefix}/availability"
        availability_fields = {
            "availability_topic": availability_topic,
            "payload_available": "online",
            "payload_not_available": "offline",
        }
        device_info = self._get_device_info()

        db = next(get_session())
        try:
            camera_service = get_camera_crud_service()
            cam = camera_service.get_camera(db, camera_id)
            if not cam:
                return
            latest = (
                db.query(Event)
                .filter_by(camera_id=cam.id)
                .order_by(Event.timestamp.desc())
                .first()
            )
            self._publish_camera_discovery(
                cam=cam,
                prefix=prefix,
                device_info=device_info,
                availability_fields=availability_fields,
            )
            self._publish_camera_state(cam=cam, latest=latest, prefix=prefix)
        finally:
            db.close()

    def clear_camera_discovery(self, camera_id: str) -> None:
        """Remove a camera from HA discovery."""
        if not self.client or not self.connected:
            return
        config = self.settings_service.load_config()
        prefix = config.mqtt.topic_prefix
        safe_id = camera_id.replace("-", "_")
        self._clear_ha_config("binary_sensor", f"person_detected_{safe_id}")
        self._clear_ha_config("sensor", f"last_event_{safe_id}")
        self.client.publish(f"{prefix}/camera/{camera_id}/person", "OFF", retain=True)
        self.client.publish(f"{prefix}/camera/{camera_id}/event", "", retain=True)

    def publish_event(self, event_data: Dict[str, Any], person_detected: bool = True):
        """
        Publish detection event.
        
        Args:
            event_data: Dict with event details (id, camera_id, summary, etc.)
            person_detected: Whether to set person binary sensor ON
        """
        if not self.client or not self.connected:
            return

        try:
            config = self.settings_service.load_config().mqtt
            prefix = config.topic_prefix
            camera_id = event_data.get("camera_id")
            if not camera_id:
                return

            if not event_data.get("summary"):
                if event_data.get("ai_required"):
                    reason = event_data.get("ai_reason")
                    if reason == "analysis_failed":
                        summary = "AI doğrulaması başarısız"
                    elif reason == "no_api_key":
                        summary = "AI anahtarı yok"
                    else:
                        summary = "AI doğrulaması bekleniyor"
                else:
                    summary = "No summary"
                event_data = {**event_data, "summary": summary}

            # 1. Publish binary sensor state ON
            if person_detected:
                person_topic = f"{prefix}/camera/{camera_id}/person"
                self.client.publish(person_topic, "ON")
                self._track_publish(person_topic, "ON")
            
            # 1b. Publish person count
            person_count = event_data.get("person_count", 1)
            count_topic = f"{prefix}/camera/{camera_id}/person_count"
            self.client.publish(count_topic, str(person_count), retain=True)
            self._track_publish(count_topic, person_count)

            # 2. Publish event details (JSON)
            payload = json.dumps(event_data, default=str)
            event_topic = f"{prefix}/camera/{camera_id}/event"
            self.client.publish(event_topic, payload, retain=True)
            self._track_publish(event_topic, event_data)
            
            # 3. Publish global event feed
            events_topic = f"{prefix}/events"
            self.client.publish(events_topic, payload)
            self._track_publish(events_topic, event_data)

            # Note: The binary sensor will stay ON until expire_after (configured in discovery)
            # or we can explicitly turn it off after some time if we want logic here.
            # HA `expire_after` is usually cleaner for stateless events.

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            self.last_error = str(e)
    
    def _track_publish(self, topic: str, payload: Any) -> None:
        """Track published messages for monitoring."""
        try:
            self.active_topics.add(topic)
            self.publish_count += 1
            self.last_messages[topic] = {
                "payload": payload if isinstance(payload, (str, int, float, bool)) else str(payload)[:200],
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            # Keep only last 50 topics
            if len(self.last_messages) > 50:
                oldest_topic = min(self.last_messages.keys(), key=lambda k: self.last_messages[k]["timestamp"])
                self.last_messages.pop(oldest_topic, None)
        except Exception:
            pass
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Get MQTT monitoring status for UI display.
        
        Returns:
            Dict with connection status, topics, messages, stats
        """
        config = self.settings_service.load_config().mqtt
        
        return {
            "enabled": config.enabled,
            "connected": self.connected,
            "broker": f"{config.host}:{config.port}",
            "topic_prefix": config.topic_prefix,
            "availability_topic": self.availability_topic,
            "connected_at": self.connected_at.isoformat() + "Z" if self.connected_at else None,
            "active_topics": sorted(list(self.active_topics)),
            "publish_count": self.publish_count,
            "last_messages": dict(sorted(
                self.last_messages.items(),
                key=lambda x: x[1]["timestamp"],
                reverse=True
            )[:10]),  # Last 10 messages
            "last_error": self.last_error,
        }

# Singleton
_mqtt_service: Optional[MqttService] = None

def get_mqtt_service() -> MqttService:
    global _mqtt_service
    if _mqtt_service is None:
        _mqtt_service = MqttService()
    return _mqtt_service
