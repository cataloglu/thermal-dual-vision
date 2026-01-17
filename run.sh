#!/usr/bin/env bashio

# Smart Motion Detector - Entry Point
# Home Assistant Add-on runner script

set -e

CONFIG_PATH=/data/options.json

bashio::log.info "Starting Smart Motion Detector..."

# Read configuration from Home Assistant
export CAMERA_URL=$(bashio::config 'camera_url')
export CAMERA_TYPE=$(bashio::config 'camera_type')
export COLOR_CAMERA_URL=$(bashio::config 'color_camera_url')
export THERMAL_CAMERA_URL=$(bashio::config 'thermal_camera_url')
export CAMERA_FPS=$(bashio::config 'camera_fps')
export MOTION_SENSITIVITY=$(bashio::config 'motion_sensitivity')
export MOTION_MIN_AREA=$(bashio::config 'motion_min_area')
export MOTION_COOLDOWN=$(bashio::config 'motion_cooldown')
export YOLO_MODEL=$(bashio::config 'yolo_model')
export YOLO_CONFIDENCE=$(bashio::config 'yolo_confidence')
export OPENAI_API_KEY=$(bashio::config 'openai_api_key')
export SCREENSHOT_BEFORE=$(bashio::config 'screenshot_before_sec')
export SCREENSHOT_AFTER=$(bashio::config 'screenshot_after_sec')
export MQTT_TOPIC_PREFIX=$(bashio::config 'mqtt_topic_prefix')
export MQTT_DISCOVERY=$(bashio::config 'mqtt_discovery')
export TELEGRAM_ENABLED=$(bashio::config 'telegram_enabled')
export TELEGRAM_BOT_TOKEN=$(bashio::config 'telegram_bot_token')
export TELEGRAM_CHAT_ID=$(bashio::config 'telegram_chat_id')
export LOG_LEVEL=$(bashio::config 'log_level')

# Get MQTT credentials from Home Assistant
if bashio::services.available "mqtt"; then
    export MQTT_HOST=$(bashio::services mqtt "host")
    export MQTT_PORT=$(bashio::services mqtt "port")
    export MQTT_USER=$(bashio::services mqtt "username")
    export MQTT_PASSWORD=$(bashio::services mqtt "password")
    bashio::log.info "MQTT service found: ${MQTT_HOST}:${MQTT_PORT}"
else
    bashio::log.warning "MQTT service not available"
fi

bashio::log.info "Configuration loaded"
if [ -n "${CAMERA_URL}" ]; then
    bashio::log.info "Camera URL: [set]"
else
    bashio::log.warning "Camera URL: [missing]"
fi
bashio::log.info "Color Camera URL: $( [ -n "${COLOR_CAMERA_URL}" ] && echo "[set]" || echo "[missing]" )"
bashio::log.info "Thermal Camera URL: $( [ -n "${THERMAL_CAMERA_URL}" ] && echo "[set]" || echo "[missing]" )"
bashio::log.info "Motion Sensitivity: ${MOTION_SENSITIVITY}"
bashio::log.info "YOLO Model: ${YOLO_MODEL}"
bashio::log.info "Log Level: ${LOG_LEVEL}"

# Run the application
cd /app
exec python3 -m src.main
