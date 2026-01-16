# Smart Motion Detector - Documentation

## Overview

Smart Motion Detector is an AI-powered Home Assistant add-on that combines traditional motion detection with YOLO object detection and GPT-4 Vision analysis. It monitors your camera feed, detects motion, identifies objects, and provides intelligent descriptions of what's happening.

**Key Features:**
- Real-time motion detection with configurable sensitivity
- YOLO-based object detection (person, car, dog, cat, etc.)
- GPT-4 Vision API for intelligent scene analysis
- MQTT integration with Home Assistant auto-discovery
- Optional Telegram notifications with screenshots
- Web UI for health monitoring
- Screenshot capture before/after motion events

---

## Installation

### Prerequisites

- Home Assistant OS or Supervised installation
- Working camera accessible via RTSP, HTTP, or other stream URL
- OpenAI API key (for GPT-4 Vision analysis)
- MQTT broker (typically Mosquitto add-on)
- Optional: Telegram bot for notifications

### Installation Steps

1. **Add the Repository**
   - Navigate to **Supervisor** → **Add-on Store** in Home Assistant
   - Click the **⋮** menu (top right) → **Repositories**
   - Add this repository URL: `https://github.com/your-repo/smart-motion-detector`
   - Click **Add** → **Close**

2. **Install the Add-on**
   - Find "Smart Motion Detector" in the add-on store
   - Click on the add-on → **Install**
   - Wait for installation to complete (may take several minutes for first-time setup)

3. **Configure the Add-on**
   - Before starting, configure at minimum:
     - Camera URL
     - OpenAI API key
   - See [Configuration](#configuration) section below for all options

4. **Start the Add-on**
   - Click **Start**
   - Check the **Log** tab for any errors
   - Enable **Start on boot** if desired
   - Enable **Watchdog** for automatic restart on crashes

5. **Access the Web UI**
   - Click **Open Web UI** or navigate to `http://homeassistant.local:8099`
   - The UI shows health status and basic statistics

---

## Configuration

### Required Settings

#### `camera_url` (required)
The URL to your camera stream.

**Supported formats:**
- RTSP: `rtsp://username:password@192.168.1.100:554/stream`
- HTTP/MJPEG: `http://192.168.1.100/video.mjpg`
- USB camera: `0` (device index)

**Example:**
```yaml
camera_url: "rtsp://admin:password@192.168.1.50:554/stream1"
```

#### `openai_api_key` (required)
Your OpenAI API key for GPT-4 Vision analysis.

**How to get:**
1. Visit https://platform.openai.com/api-keys
2. Create a new API key
3. Copy and paste into this field

**Example:**
```yaml
openai_api_key: "sk-proj-xxxxxxxxxxxxxxxxxxxx"
```

---

### Camera Settings

#### `camera_fps`
Frames per second to capture from the camera.

- **Default:** `5`
- **Range:** 1-30
- **Recommendation:** Lower values (3-5) reduce CPU usage; higher values (10-15) improve motion detection accuracy

**Example:**
```yaml
camera_fps: 5
```

---

### Motion Detection Settings

#### `motion_sensitivity`
Sensitivity level for motion detection.

- **Default:** `7`
- **Range:** 1-10 (1 = least sensitive, 10 = most sensitive)
- **Recommendation:** Start with 7, decrease if getting false alarms, increase if missing events

**Example:**
```yaml
motion_sensitivity: 7
```

#### `motion_min_area`
Minimum pixel area that must change to trigger motion.

- **Default:** `500`
- **Range:** 100-10000
- **Recommendation:** Increase to ignore small movements (trees, shadows), decrease for detecting smaller objects

**Example:**
```yaml
motion_min_area: 500
```

#### `motion_cooldown`
Seconds to wait after a motion event before detecting new motion.

- **Default:** `5`
- **Range:** 1-60
- **Purpose:** Prevents duplicate events for the same motion
- **Recommendation:** 5-10 seconds for most use cases

**Example:**
```yaml
motion_cooldown: 5
```

---

### YOLO Detection Settings

#### `yolo_model`
YOLO model size to use for object detection.

- **Default:** `yolov8n`
- **Options:**
  - `yolov8n` - Nano (fastest, least accurate)
  - `yolov8s` - Small (balanced)
  - `yolov8m` - Medium (slower, most accurate)
- **Recommendation:** Use `yolov8n` unless you need higher accuracy

**Example:**
```yaml
yolo_model: "yolov8n"
```

#### `yolo_confidence`
Minimum confidence threshold for YOLO detections.

- **Default:** `0.5`
- **Range:** 0.1-1.0
- **Recommendation:** 0.5 for balanced detection; increase to reduce false positives

**Example:**
```yaml
yolo_confidence: 0.5
```

#### `yolo_classes`
List of object classes to detect.

- **Default:** `[person, car, dog, cat]`
- **Available classes:** person, bicycle, car, motorcycle, airplane, bus, train, truck, boat, bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe, backpack, umbrella, handbag, tie, suitcase, and more (COCO dataset)

**Example:**
```yaml
yolo_classes:
  - person
  - car
  - dog
  - cat
  - bicycle
```

---

### Screenshot Settings

#### `screenshot_before_sec`
Seconds of video to capture BEFORE motion is detected.

- **Default:** `3`
- **Range:** 1-10
- **Purpose:** Provides context for what led to the motion event

**Example:**
```yaml
screenshot_before_sec: 3
```

#### `screenshot_after_sec`
Seconds of video to capture AFTER motion is detected.

- **Default:** `3`
- **Range:** 1-10
- **Purpose:** Captures the full motion event

**Example:**
```yaml
screenshot_after_sec: 3
```

---

### MQTT Settings

#### `mqtt_topic_prefix`
Prefix for all MQTT topics.

- **Default:** `smart_motion`
- **Topics published:**
  - `{prefix}/motion` - Motion events
  - `{prefix}/detection` - Object detections
  - `{prefix}/analysis` - GPT-4 Vision analysis
  - `{prefix}/status` - Add-on status

**Example:**
```yaml
mqtt_topic_prefix: "smart_motion"
```

#### `mqtt_discovery`
Enable Home Assistant MQTT discovery.

- **Default:** `true`
- **Recommendation:** Keep enabled for automatic entity creation

**Example:**
```yaml
mqtt_discovery: true
```

**Created entities:**
- `binary_sensor.smart_motion_detector_motion` - Motion detected state
- `sensor.smart_motion_detector_last_detection` - Last detected objects
- `sensor.smart_motion_detector_last_analysis` - GPT-4 Vision analysis
- `sensor.smart_motion_detector_status` - Add-on health status

---

### Telegram Notifications (Optional)

#### `telegram_enabled`
Enable Telegram notifications.

- **Default:** `false`

**Example:**
```yaml
telegram_enabled: true
```

#### `telegram_bot_token`
Your Telegram bot token.

**How to get:**
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the bot token

**Example:**
```yaml
telegram_bot_token: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
```

#### `telegram_chat_id`
Your Telegram chat ID (or group ID).

**How to get:**
1. Message your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find `"chat":{"id":123456789}` in the response

**Example:**
```yaml
telegram_chat_id: "123456789"
```

**Notifications include:**
- Screenshot of the event
- Detected objects
- GPT-4 Vision analysis
- Timestamp

---

### Logging

#### `log_level`
Logging verbosity level.

- **Default:** `INFO`
- **Options:** `DEBUG`, `INFO`, `WARNING`, `ERROR`
- **Recommendation:** Use `INFO` normally, `DEBUG` for troubleshooting

**Example:**
```yaml
log_level: "INFO"
```

---

## Complete Configuration Example

```yaml
camera_url: "rtsp://admin:password@192.168.1.50:554/stream1"
camera_fps: 5
motion_sensitivity: 7
motion_min_area: 500
motion_cooldown: 5
yolo_model: "yolov8n"
yolo_confidence: 0.5
yolo_classes:
  - person
  - car
  - dog
  - cat
openai_api_key: "sk-proj-xxxxxxxxxxxxxxxxxxxx"
screenshot_before_sec: 3
screenshot_after_sec: 3
mqtt_topic_prefix: "smart_motion"
mqtt_discovery: true
telegram_enabled: true
telegram_bot_token: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
telegram_chat_id: "123456789"
log_level: "INFO"
```

---

## Usage

### Home Assistant Integration

Once the add-on is running with MQTT discovery enabled, entities will automatically appear in Home Assistant:

**Binary Sensor:**
```yaml
# Example automation
automation:
  - alias: "Motion Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.smart_motion_detector_motion
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Motion Detected"
          message: "{{ states('sensor.smart_motion_detector_last_analysis') }}"
```

**Sensors:**
```yaml
# Display in Lovelace card
type: entities
entities:
  - binary_sensor.smart_motion_detector_motion
  - sensor.smart_motion_detector_last_detection
  - sensor.smart_motion_detector_last_analysis
  - sensor.smart_motion_detector_status
```

### MQTT Topics

Subscribe to topics for custom integrations:

```bash
# Motion events (JSON)
smart_motion/motion
{
  "timestamp": "2024-01-15T10:30:45",
  "motion_detected": true,
  "motion_area": 1250
}

# Object detections (JSON)
smart_motion/detection
{
  "timestamp": "2024-01-15T10:30:45",
  "objects": [
    {"class": "person", "confidence": 0.92},
    {"class": "dog", "confidence": 0.87}
  ]
}

# GPT-4 Vision analysis (JSON)
smart_motion/analysis
{
  "timestamp": "2024-01-15T10:30:45",
  "analysis": "A person is walking a dog in the backyard. The dog appears to be a golden retriever."
}
```

### Web UI

Access the web interface at `http://homeassistant.local:8099` or click "Open Web UI" in the add-on page.

**Features:**
- Health check status
- Current FPS
- Last motion event
- Last analysis
- Uptime

---

## Troubleshooting

### Camera Connection Issues

**Problem:** "Cannot connect to camera" error

**Solutions:**
1. Verify camera URL is correct
2. Test URL with VLC media player
3. Check network connectivity
4. Ensure camera supports the stream format
5. Try reducing `camera_fps`

**Debug:**
```yaml
log_level: "DEBUG"
```
Check logs for detailed connection errors.

---

### High CPU Usage

**Problem:** Add-on using too much CPU

**Solutions:**
1. Reduce `camera_fps` to 3-5
2. Use smaller YOLO model: `yolov8n`
3. Increase `motion_cooldown` to reduce processing frequency
4. Reduce camera resolution at the camera source

---

### False Motion Alerts

**Problem:** Too many false positives

**Solutions:**
1. Decrease `motion_sensitivity` (try 5-6)
2. Increase `motion_min_area` to ignore small changes
3. Position camera to avoid trees, curtains, shadows
4. Increase `motion_cooldown` to reduce duplicate events

---

### Missing Motion Events

**Problem:** Not detecting actual motion

**Solutions:**
1. Increase `motion_sensitivity` (try 8-9)
2. Decrease `motion_min_area`
3. Increase `camera_fps` for better detection
4. Verify camera view isn't obstructed

---

### MQTT Not Working

**Problem:** Entities not appearing in Home Assistant

**Solutions:**
1. Verify Mosquitto add-on is installed and running
2. Check `mqtt_discovery` is set to `true`
3. Restart Home Assistant after add-on starts
4. Check MQTT integration is configured in HA
5. Review logs for MQTT connection errors

---

### OpenAI API Errors

**Problem:** "OpenAI API error" in logs

**Solutions:**
1. Verify API key is correct
2. Check OpenAI account has credits
3. Ensure API key has GPT-4 Vision access
4. Check internet connectivity
5. Review OpenAI API status page

---

### Telegram Not Sending

**Problem:** No Telegram notifications

**Solutions:**
1. Verify `telegram_enabled: true`
2. Check bot token is correct
3. Verify chat ID is correct (including any negative sign)
4. Ensure you've started conversation with bot
5. Check logs for Telegram API errors

---

## Performance Tuning

### Low-End Hardware (Raspberry Pi 3)
```yaml
camera_fps: 3
yolo_model: "yolov8n"
motion_sensitivity: 6
motion_min_area: 800
```

### Balanced (Raspberry Pi 4, Intel NUC)
```yaml
camera_fps: 5
yolo_model: "yolov8n"
motion_sensitivity: 7
motion_min_area: 500
```

### High-Performance (Dedicated Server, GPU)
```yaml
camera_fps: 10
yolo_model: "yolov8s"
motion_sensitivity: 8
motion_min_area: 300
```

---

## Support

- **Issues:** https://github.com/your-repo/smart-motion-detector/issues
- **Discussions:** https://github.com/your-repo/smart-motion-detector/discussions
- **Home Assistant Community:** https://community.home-assistant.io/

---

## Privacy & Security

- All video processing occurs locally on your Home Assistant instance
- Screenshots are stored locally and not uploaded anywhere except:
  - OpenAI API (only the specific frames analyzed)
  - Telegram (if enabled, screenshots sent to your chat)
- OpenAI API key is stored securely in Home Assistant
- Camera credentials are never logged or exposed

---

## Credits

- **YOLO:** Ultralytics YOLOv8
- **OpenAI:** GPT-4 Vision API
- **Home Assistant:** Home automation platform

---

## Changelog

### Version 1.0.0
- Initial release
- Motion detection with YOLO object detection
- GPT-4 Vision integration
- MQTT auto-discovery
- Telegram notifications
- Web UI for monitoring
