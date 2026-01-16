# MQTT Integration Tests

This document describes how to test the MQTT client with a real Mosquitto broker to verify end-to-end functionality with Home Assistant.

## Overview

While unit tests use a mocked broker, integration tests validate actual MQTT protocol behavior with a real Mosquitto broker. This ensures:

- Connection establishment and authentication
- Discovery message format and topics
- State publishing with correct QoS and retain flags
- Last Will Testament (LWT) behavior
- Reconnection logic on disconnect
- Home Assistant auto-discovery protocol compliance

## Prerequisites

### Required Tools

1. **Docker** - To run Mosquitto broker
   ```bash
   docker --version
   ```

2. **Mosquitto CLI Tools** - For subscribing to topics
   ```bash
   # Ubuntu/Debian
   sudo apt-get install mosquitto-clients

   # macOS
   brew install mosquitto

   # Or use Docker
   docker run --rm eclipse-mosquitto:2 mosquitto_sub --help
   ```

3. **Python Dependencies**
   ```bash
   pip install asyncio-mqtt
   ```

## Setup

### 1. Start Mosquitto Broker

Start a Mosquitto broker in Docker:

```bash
docker run -d \
  --name mqtt-test \
  -p 1883:1883 \
  eclipse-mosquitto:2 \
  mosquitto -c /mosquitto-no-auth.conf
```

Verify the broker is running:

```bash
docker ps | grep mqtt-test
```

### 2. Configure MQTT Client

Create a test configuration file `config/test_mqtt.yaml`:

```yaml
mqtt:
  host: "localhost"
  port: 1883
  username: ""
  password: ""
  topic_prefix: "smart_motion"
  discovery: true
  discovery_prefix: "homeassistant"
  qos: 1
```

## Manual Testing

### Test 1: Connection and Availability (LWT)

**Purpose:** Verify connection establishment and Last Will Testament configuration.

**Terminal 1** - Subscribe to availability:
```bash
mosquitto_sub -h localhost -t 'smart_motion/availability' -v
```

**Terminal 2** - Run Python client:
```python
import asyncio
from src.config import load_config
from src.mqtt_client import MQTTClient

async def test_connection():
    config = load_config("config/test_mqtt.yaml")
    client = MQTTClient(config.mqtt)

    await client.connect()
    print("Connected! Check Terminal 1 for 'online' message")

    await asyncio.sleep(2)
    await client.disconnect()
    print("Disconnected! Check Terminal 1 for 'offline' message")

asyncio.run(test_connection())
```

**Expected Output in Terminal 1:**
```
smart_motion/availability online
smart_motion/availability offline
```

**Verification:**
- ✓ Receives "online" when client connects
- ✓ Receives "offline" when client disconnects
- ✓ Messages are retained (reconnect subscriber and see last state)

---

### Test 2: Home Assistant Auto-Discovery

**Purpose:** Verify discovery messages follow HA MQTT discovery protocol.

**Terminal 1** - Subscribe to all discovery topics:
```bash
mosquitto_sub -h localhost -t 'homeassistant/#' -v
```

**Terminal 2** - Publish discovery:
```python
import asyncio
from src.config import load_config
from src.mqtt_client import MQTTClient

async def test_discovery():
    config = load_config("config/test_mqtt.yaml")
    client = MQTTClient(config.mqtt)

    await client.connect()
    await client.publish_discovery()
    print("Discovery messages sent! Check Terminal 1")

    await asyncio.sleep(2)
    await client.disconnect()

asyncio.run(test_discovery())
```

**Expected Output in Terminal 1:**
```
homeassistant/binary_sensor/smart_motion/motion/config {...}
homeassistant/sensor/smart_motion/threat_level/config {...}
homeassistant/sensor/smart_motion/confidence/config {...}
homeassistant/sensor/smart_motion/last_analysis/config {...}
```

**Verification:**
- ✓ All 4 discovery topics are published
- ✓ Binary sensor has `device_class: motion`
- ✓ All configs have same `device` block with unique `identifiers`
- ✓ State topics use correct prefix: `smart_motion/*`
- ✓ Availability topic is set: `smart_motion/availability`
- ✓ Messages are retained (reconnect subscriber and see configs)

**JSON Payload Validation:**
```bash
# View formatted discovery payload
mosquitto_sub -h localhost -t 'homeassistant/binary_sensor/smart_motion/motion/config' -C 1 | jq .
```

Expected fields:
- `name`: "Smart Motion"
- `unique_id`: "smart_motion_detector_motion"
- `state_topic`: "smart_motion/motion/state"
- `device_class`: "motion"
- `availability_topic`: "smart_motion/availability"
- `payload_on`: "ON"
- `payload_off`: "OFF"
- `device.identifiers`: ["smart_motion_detector"]

---

### Test 3: Motion State Publishing

**Purpose:** Verify motion detection and analysis data publishing.

**Terminal 1** - Subscribe to state topics:
```bash
# Subscribe to all state topics
mosquitto_sub -h localhost -t 'smart_motion/#' -v
```

**Terminal 2** - Publish motion events:
```python
import asyncio
from dataclasses import dataclass
from src.config import load_config
from src.mqtt_client import MQTTClient

@dataclass
class MockAnalysis:
    is_threat: bool
    confidence: float
    threat_level: str

async def test_motion():
    config = load_config("config/test_mqtt.yaml")
    client = MQTTClient(config.mqtt)

    await client.connect()
    await client.publish_discovery()

    # Test 1: Motion detected with analysis
    print("Publishing motion with threat analysis...")
    analysis = MockAnalysis(
        is_threat=True,
        confidence=0.87,
        threat_level="high"
    )
    await client.publish_motion(detected=True, analysis=analysis)
    await asyncio.sleep(1)

    # Test 2: Motion detected without analysis
    print("Publishing motion without analysis...")
    await client.publish_motion(detected=True)
    await asyncio.sleep(1)

    # Test 3: No motion
    print("Publishing no motion...")
    await client.publish_motion(detected=False)
    await asyncio.sleep(1)

    await client.disconnect()

asyncio.run(test_motion())
```

**Expected Output in Terminal 1:**
```
smart_motion/availability online
smart_motion/motion/state ON
smart_motion/threat_level/state high
smart_motion/confidence/state 87
smart_motion/last_analysis/state 2026-01-16T08:30:45.123456
smart_motion/motion/state ON
smart_motion/motion/state OFF
smart_motion/availability offline
```

**Verification:**
- ✓ Motion state publishes "ON" or "OFF"
- ✓ Threat level publishes when analysis provided
- ✓ Confidence converts to percentage (0.87 → 87)
- ✓ Last analysis publishes ISO timestamp
- ✓ Works without analysis (only motion state changes)
- ✓ All messages use QoS 1

---

### Test 4: Reconnection Logic

**Purpose:** Verify automatic reconnection on broker disconnect.

**Terminal 1** - Monitor availability:
```bash
mosquitto_sub -h localhost -t 'smart_motion/availability' -v
```

**Terminal 2** - Start client:
```python
import asyncio
from src.config import load_config
from src.mqtt_client import MQTTClient

async def test_reconnect():
    config = load_config("config/test_mqtt.yaml")
    client = MQTTClient(config.mqtt)

    # Add callbacks to see reconnection
    client.on_connect(lambda: print("CALLBACK: Connected"))
    client.on_disconnect(lambda: print("CALLBACK: Disconnected"))

    await client.connect()
    print("Client connected. Now stop the broker to test reconnection...")
    print("Run: docker stop mqtt-test")

    # Wait for manual broker stop
    await asyncio.sleep(10)

    print("Now restart broker: docker start mqtt-test")
    print("Client should automatically reconnect...")

    # Wait for reconnection
    await asyncio.sleep(30)

    await client.disconnect()

asyncio.run(test_reconnect())
```

**Test Steps:**
1. Start the client (see "Connected" callback)
2. Stop broker: `docker stop mqtt-test`
3. Observe "Disconnected" callback and reconnection attempts in logs
4. Start broker: `docker start mqtt-test`
5. Observe automatic reconnection and "Connected" callback
6. Terminal 1 should show "online" → "offline" → "online"

**Verification:**
- ✓ Client logs show reconnection attempts with exponential backoff
- ✓ Callbacks fire on disconnect and reconnect
- ✓ LWT publishes "offline" on disconnect
- ✓ Client publishes "online" on successful reconnect
- ✓ Backoff increases: 1s, 2s, 4s, 8s, ... up to 60s max

---

### Test 5: Generic State Publishing

**Purpose:** Verify custom state publishing functionality.

**Terminal 1** - Subscribe to custom topic:
```bash
mosquitto_sub -h localhost -t 'smart_motion/status' -v
```

**Terminal 2** - Publish custom state:
```python
import asyncio
from src.config import load_config
from src.mqtt_client import MQTTClient

async def test_state():
    config = load_config("config/test_mqtt.yaml")
    client = MQTTClient(config.mqtt)

    await client.connect()

    # Publish custom state
    await client.publish_state("status", {
        "uptime": 3600,
        "detections": 42,
        "version": "1.0.0"
    })

    await asyncio.sleep(1)
    await client.disconnect()

asyncio.run(test_state())
```

**Expected Output in Terminal 1:**
```json
smart_motion/status {"uptime": 3600, "detections": 42, "version": "1.0.0"}
```

**Verification:**
- ✓ Publishes to `{topic_prefix}/{custom_topic}`
- ✓ JSON serialization works correctly
- ✓ Uses configured QoS

---

## Home Assistant Integration Test

### Setup Home Assistant

1. **Add MQTT Integration:**
   - Settings → Devices & Services → Add Integration → MQTT
   - Host: `localhost` (or your broker address)
   - Port: `1883`

2. **Run Discovery:**
   ```python
   import asyncio
   from src.config import load_config
   from src.mqtt_client import MQTTClient

   async def main():
       config = load_config("config/test_mqtt.yaml")
       client = MQTTClient(config.mqtt)

       await client.connect()
       await client.publish_discovery()

       print("Discovery sent! Check Home Assistant...")
       print("Settings → Devices & Services → MQTT")
       print("Look for 'Smart Motion Detector' device")

       # Keep publishing states
       while True:
           await client.publish_motion(True)
           await asyncio.sleep(5)
           await client.publish_motion(False)
           await asyncio.sleep(5)

   asyncio.run(main())
   ```

3. **Verify in Home Assistant:**
   - Navigate to: Settings → Devices & Services → MQTT
   - Find device: **Smart Motion Detector**
   - Verify 4 entities appear:
     - `binary_sensor.smart_motion` (Motion)
     - `sensor.smart_motion_threat_level`
     - `sensor.smart_motion_confidence`
     - `sensor.smart_motion_last_analysis`
   - Watch entities update as states are published

**Expected Results:**
- ✓ Device appears automatically (no manual configuration)
- ✓ All 4 entities are created
- ✓ Binary sensor shows motion icon
- ✓ Entities show real-time state updates
- ✓ Device shows "Available" when client connected
- ✓ Device shows "Unavailable" when client disconnected

---

## Troubleshooting

### Connection Issues

**Problem:** Client can't connect to broker

**Solutions:**
```bash
# Check broker is running
docker ps | grep mqtt-test

# Check broker logs
docker logs mqtt-test

# Test connection manually
mosquitto_pub -h localhost -p 1883 -t 'test' -m 'hello'

# Restart broker
docker restart mqtt-test
```

---

### Discovery Not Working

**Problem:** Entities don't appear in Home Assistant

**Solutions:**
1. Verify discovery messages are published:
   ```bash
   mosquitto_sub -h localhost -t 'homeassistant/#' -v
   ```

2. Check HA MQTT integration is enabled:
   - Settings → Devices & Services → MQTT

3. Check discovery_prefix matches HA config:
   - Default is `homeassistant`

4. Clear retained messages and republish:
   ```bash
   # Clear all discovery topics
   mosquitto_pub -h localhost -t 'homeassistant/binary_sensor/smart_motion/motion/config' -n -r
   mosquitto_pub -h localhost -t 'homeassistant/sensor/smart_motion/threat_level/config' -n -r
   mosquitto_pub -h localhost -t 'homeassistant/sensor/smart_motion/confidence/config' -n -r
   mosquitto_pub -h localhost -t 'homeassistant/sensor/smart_motion/last_analysis/config' -n -r
   ```

5. Restart Home Assistant

---

### Messages Not Retained

**Problem:** Subscriber doesn't see messages when connecting after publish

**Solutions:**
- Verify retain flag is set in code
- Check broker supports retained messages
- Test manually:
  ```bash
  # Publish with retain
  mosquitto_pub -h localhost -t 'test/retain' -m 'hello' -r

  # Subscribe (should see message immediately)
  mosquitto_sub -h localhost -t 'test/retain' -v
  ```

---

### Reconnection Not Working

**Problem:** Client doesn't reconnect after broker restart

**Solutions:**
1. Check `_should_reconnect` flag is True
2. Verify logs show reconnection attempts
3. Ensure broker allows reconnections
4. Check network connectivity
5. Increase backoff max delay in code if needed

---

## Cleanup

After testing, stop and remove the broker:

```bash
# Stop broker
docker stop mqtt-test

# Remove container
docker rm mqtt-test

# Or do both
docker rm -f mqtt-test
```

---

## Automated Integration Tests

While integration tests are primarily manual due to external dependencies, you can create automated tests using `docker-compose` for CI/CD:

```yaml
# docker-compose.test.yml
version: '3.8'
services:
  mosquitto:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
    command: mosquitto -c /mosquitto-no-auth.conf

  test-runner:
    build: .
    depends_on:
      - mosquitto
    environment:
      MQTT_HOST: mosquitto
      MQTT_PORT: 1883
    command: pytest tests/integration/ -v
```

Run with:
```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

---

## References

- [Home Assistant MQTT Discovery](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery)
- [Mosquitto Docker Hub](https://hub.docker.com/_/eclipse-mosquitto)
- [asyncio-mqtt Documentation](https://github.com/sbtinstruments/asyncio-mqtt)
- [MQTT Protocol Specification](https://mqtt.org/mqtt-specification/)

---

## Summary

This integration testing approach ensures:

1. ✅ **Connection Management** - Connect, disconnect, LWT all work
2. ✅ **Protocol Compliance** - Messages follow MQTT and HA discovery specs
3. ✅ **Reliability** - Reconnection and error handling work correctly
4. ✅ **Home Assistant Integration** - Entities appear and update properly
5. ✅ **State Publishing** - All entity types publish correct data

For any issues, check logs with `logger.debug()` enabled and use `mosquitto_sub` to verify messages at the broker level.
