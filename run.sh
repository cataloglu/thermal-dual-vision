#!/bin/bash
set -euo pipefail

# Version is set by Dockerfile from BUILD_VERSION arg (from config.yaml)
ADDON_VERSION="${ADDON_VERSION:-unknown}"
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
            # Persist MQTT settings via single-writer sync script.
            python3 sync_options.py
        else
            result=$(echo "$MQTT_INFO" | jq -r '.result' 2>/dev/null || echo "unknown")
            echo "MQTT Service not available via Supervisor (result: $result)."
        fi
    else
        echo "Failed to query Supervisor for MQTT service."
    fi
fi
# ---------------------------------------------------------

# Database migrations (standalone scripts, no app imports)
echo "Checking database migrations..."
cd /app || true
MIGRATION_DEGRADED=0
if ! python3 fix_stream_roles_migration.py; then
    echo "Migration failed: fix_stream_roles_migration.py"
    MIGRATION_DEGRADED=1
fi
if ! python3 add_person_count_migration.py; then
    echo "Migration failed: add_person_count_migration.py"
    MIGRATION_DEGRADED=1
fi
if [ "${MIGRATION_DEGRADED}" -ne 0 ]; then
    export TDV_MIGRATION_DEGRADED="1"
    echo "WARNING: one or more migrations failed; service will start in degraded mode"
fi

echo "Starting supervisor..."
exec supervisord -c /etc/supervisor/supervisord.conf
