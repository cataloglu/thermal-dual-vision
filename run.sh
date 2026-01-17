#!/bin/sh

# Smart Motion Detector - Entry Point
# Works both in Home Assistant Supervisor and local Docker

set -e

CONFIG_PATH=/data/options.json

# Load bashio if available (Home Assistant Supervisor)
if [ -f /usr/lib/bashio/bashio.sh ]; then
    # shellcheck source=/dev/null
    . /usr/lib/bashio/bashio.sh
fi

# Mask sensitive information in URLs
_mask_url() {
    url="$1"
    if echo "$url" | grep -q '@'; then
        # Mask password in URL: rtsp://user:pass@host -> rtsp://user:***@host
        echo "$url" | sed 's/:[^:@]*@/:***@/'
    else
        echo "$url"
    fi
}

# Check if bashio is available (Home Assistant Supervisor)
if command -v bashio > /dev/null 2>&1 || [ -f /usr/lib/bashio/bashio.sh ]; then
    # Home Assistant Supervisor mode
    if ! command -v bashio > /dev/null 2>&1 && [ -f /usr/lib/bashio/bashio.sh ]; then
        # Load bashio library
        # shellcheck source=/dev/null
        . /usr/lib/bashio/bashio.sh
    fi
    
    bashio.log.info "Starting Smart Motion Detector (Supervisor mode)..."
    
    # Read configuration from Home Assistant
    export RTSP_URL=$(bashio.config 'rtsp_url')
    export CAMERA_URL="${RTSP_URL}"  # Keep backward compatibility
    export CAMERA_FPS=$(bashio.config 'camera_fps')
    export MOTION_SENSITIVITY=$(bashio.config 'motion_sensitivity')
    export MOTION_MIN_AREA=$(bashio.config 'motion_min_area')
    export MOTION_COOLDOWN=$(bashio.config 'motion_cooldown')
    export YOLO_MODEL=$(bashio.config 'yolo_model')
    export YOLO_CONFIDENCE=$(bashio.config 'yolo_confidence')
    export OPENAI_API_KEY=$(bashio.config 'openai_api_key')
    export SCREENSHOT_BEFORE=$(bashio.config 'screenshot_before_sec')
    export SCREENSHOT_AFTER=$(bashio.config 'screenshot_after_sec')
    export MQTT_TOPIC_PREFIX=$(bashio.config 'mqtt_topic_prefix')
    export MQTT_DISCOVERY=$(bashio.config 'mqtt_discovery')
    export TELEGRAM_ENABLED=$(bashio.config 'telegram_enabled')
    export TELEGRAM_BOT_TOKEN=$(bashio.config 'telegram_bot_token')
    export TELEGRAM_CHAT_ID=$(bashio.config 'telegram_chat_id')
    export LOG_LEVEL=$(bashio.config 'log_level')
    
    # Get MQTT credentials from Home Assistant
    if bashio.services.available "mqtt"; then
        export MQTT_HOST=$(bashio.services mqtt "host")
        export MQTT_PORT=$(bashio.services mqtt "port")
        export MQTT_USER=$(bashio.services mqtt "username")
        export MQTT_PASSWORD=$(bashio.services mqtt "password")
        bashio.log.info "MQTT service found: ${MQTT_HOST}:${MQTT_PORT}"
    else
        bashio.log.warning "MQTT service not available"
    fi
    
    bashio.log.info "Configuration loaded"
    # Mask RTSP URL in logs to prevent password exposure
    RTSP_URL_MASKED=$(_mask_url "${RTSP_URL}")
    bashio.log.info "RTSP URL: ${RTSP_URL_MASKED}"
    bashio.log.info "Motion Sensitivity: ${MOTION_SENSITIVITY}"
    bashio.log.info "YOLO Model: ${YOLO_MODEL}"
    bashio.log.info "Log Level: ${LOG_LEVEL}"
else
    # Local Docker mode - use environment variables
    echo "Starting Smart Motion Detector (Local Docker mode)..."
    
    # Use environment variables (set via docker run -e or .env file)
    export CAMERA_URL="${RTSP_URL:-${CAMERA_URL:-}}"
    
    echo "Configuration from environment variables:"
    # Mask RTSP URL in logs
    RTSP_URL_MASKED=$(_mask_url "${RTSP_URL:-not set}")
    echo "RTSP_URL: ${RTSP_URL_MASKED}"
    echo "CAMERA_URL: ${CAMERA_URL:-not set}"
    echo "LOG_LEVEL: ${LOG_LEVEL:-INFO}"
fi

# Run the application
cd /app
exec python3 -m src.main
