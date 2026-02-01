#!/bin/bash
set -euo pipefail

ADDON_VERSION="${ADDON_VERSION:-2.1.124}"
echo "Starting Thermal Dual Vision (v${ADDON_VERSION})..."

# Ensure data directory exists
mkdir -p /app/data

# Ensure Ultralytics config directory is writable
YOLO_CONFIG_DIR="/app/data/ultralytics"
mkdir -p "$YOLO_CONFIG_DIR"
export YOLO_CONFIG_DIR

# Load HA add-on options (log level)
LOG_LEVEL=""
if [ -f /data/options.json ]; then
    LOG_LEVEL=$(jq -r '.log_level // empty' /data/options.json 2>/dev/null || true)
fi
LOG_LEVEL="${LOG_LEVEL:-info}"
LOG_LEVEL_LOWER="$(echo "${LOG_LEVEL}" | tr '[:upper:]' '[:lower:]')"
export LOG_LEVEL

# Adjust noisy OpenCV/FFmpeg logs based on requested log level
if [ "${LOG_LEVEL_LOWER}" = "trace" ]; then
    OPENCV_LOG_LEVEL="${OPENCV_LOG_LEVEL:-DEBUG}"
    OPENCV_FFMPEG_LOGLEVEL="${OPENCV_FFMPEG_LOGLEVEL:-verbose}"
    FFMPEG_LOGLEVEL="${FFMPEG_LOGLEVEL:-verbose}"
elif [ "${LOG_LEVEL_LOWER}" = "debug" ]; then
    OPENCV_LOG_LEVEL="${OPENCV_LOG_LEVEL:-INFO}"
    OPENCV_FFMPEG_LOGLEVEL="${OPENCV_FFMPEG_LOGLEVEL:-info}"
    FFMPEG_LOGLEVEL="${FFMPEG_LOGLEVEL:-info}"
else
    OPENCV_LOG_LEVEL="${OPENCV_LOG_LEVEL:-ERROR}"
    OPENCV_FFMPEG_LOGLEVEL="${OPENCV_FFMPEG_LOGLEVEL:-error}"
    FFMPEG_LOGLEVEL="${FFMPEG_LOGLEVEL:-error}"
fi
export OPENCV_LOG_LEVEL
export OPENCV_FFMPEG_LOGLEVEL
export FFMPEG_LOGLEVEL
echo "Log level: ${LOG_LEVEL} (opencv=${OPENCV_LOG_LEVEL}, ffmpeg=${FFMPEG_LOGLEVEL})"

# ---------------------------------------------------------
# AUTO-DISCOVER MQTT FROM HA SUPERVISOR API
# ---------------------------------------------------------
if [ -n "${SUPERVISOR_TOKEN:-}" ]; then
    echo "Querying HA Supervisor for MQTT service..."
    
    # Get MQTT service info
    if MQTT_INFO=$(curl -s --connect-timeout 5 --max-time 10 -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/services/mqtt); then
    
        # Check if result is valid JSON and has host
        if echo "$MQTT_INFO" | jq -e '.result == "ok"' > /dev/null; then
            echo "MQTT Service found! configuring..."
            
            MQTT_HOST=$(echo "$MQTT_INFO" | jq -r '.data.host')
            MQTT_PORT=$(echo "$MQTT_INFO" | jq -r '.data.port')
            MQTT_USER=$(echo "$MQTT_INFO" | jq -r '.data.username')
            MQTT_PASS=$(echo "$MQTT_INFO" | jq -r '.data.password')

            # Normalize null/empty values for anonymous connections
            if [ "$MQTT_HOST" = "null" ] || [ -z "$MQTT_HOST" ]; then MQTT_HOST="core-mosquitto"; fi
            if [ "$MQTT_USER" = "null" ]; then MQTT_USER=""; fi
            if [ "$MQTT_PASS" = "null" ]; then MQTT_PASS=""; fi
            
            # Export as ENV variables for Python app
            export MQTT_HOST="$MQTT_HOST"
            export MQTT_PORT="$MQTT_PORT"
            export MQTT_USER="$MQTT_USER"
            export MQTT_PASS="$MQTT_PASS"
            
            # Also update config.json directly to persist settings
            # We use a small python script to inject these into config.json
            python3 - <<'PY'
import json
import os

config_path = '/app/data/config.json'
try:
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {}

    if 'mqtt' not in data:
        data['mqtt'] = {}

    data['mqtt']['enabled'] = True
    host = os.getenv('MQTT_HOST')
    port_raw = os.getenv('MQTT_PORT')
    user = os.getenv('MQTT_USER')
    password = os.getenv('MQTT_PASS')

    if not host or host == 'null':
        host = 'core-mosquitto'

    try:
        port = int(port_raw or 1883)
    except Exception:
        port = 1883

    data['mqtt']['host'] = host
    data['mqtt']['port'] = port

    if user and user != 'null':
        data['mqtt']['username'] = user
    else:
        data['mqtt'].pop('username', None)

    if password and password != 'null':
        data['mqtt']['password'] = password
    else:
        data['mqtt'].pop('password', None)

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print('Updated config.json with auto-discovered MQTT settings')
except Exception as e:
    print(f'Failed to update config: {e}')
PY
        else
            result=$(echo "$MQTT_INFO" | jq -r '.result' 2>/dev/null || echo "unknown")
            echo "MQTT Service not available via Supervisor (result: $result)."
        fi
    else
        echo "Failed to query Supervisor for MQTT service."
    fi
fi
# ---------------------------------------------------------

# Fix stream_roles for existing cameras (migration)
echo "Checking database migrations..."
if [ -f /app/data/app.db ]; then
    python3 /app/fix_stream_roles.py || true
fi

echo "Starting supervisor..."
exec supervisord -c /etc/supervisor/supervisord.conf
