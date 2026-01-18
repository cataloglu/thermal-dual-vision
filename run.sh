#!/usr/bin/env bash

# Smart Motion Detector - Entry Point
# Home Assistant Add-on runner script

set -e

CONFIG_PATH=/data/options.json

if [ -x /usr/bin/bashio ] || [ -f /usr/lib/bashio/bashio.sh ]; then
    # Home Assistant add-on environment
    # shellcheck source=/usr/lib/bashio/bashio.sh
    . /usr/lib/bashio/bashio.sh
    HAS_BASHIO=1
else
    HAS_BASHIO=0
fi

log_info() {
    if [ "$HAS_BASHIO" -eq 1 ]; then
        bashio::log.info "$1"
    else
        echo "[INFO] $1"
    fi
}

log_warn() {
    if [ "$HAS_BASHIO" -eq 1 ]; then
        bashio::log.warning "$1"
    else
        echo "[WARN] $1"
    fi
}

log_info "Starting Smart Motion Detector..."

if [ "$HAS_BASHIO" -eq 1 ] && [ -f "${CONFIG_PATH}" ]; then
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
    export HOST=$(bashio::config 'host')
    export PORT=$(bashio::config 'port')

    if [ -z "${HOST}" ]; then
        HOST="0.0.0.0"
    fi
    if [ -z "${PORT}" ]; then
        PORT="8000"
    fi
else
    # Local Docker fallback
    export CAMERA_URL="${CAMERA_URL:-dummy://}"
    export CAMERA_TYPE="${CAMERA_TYPE:-color}"
    export COLOR_CAMERA_URL="${COLOR_CAMERA_URL:-}"
    export THERMAL_CAMERA_URL="${THERMAL_CAMERA_URL:-}"
    export CAMERA_FPS="${CAMERA_FPS:-5}"
    export MOTION_SENSITIVITY="${MOTION_SENSITIVITY:-7}"
    export MOTION_MIN_AREA="${MOTION_MIN_AREA:-500}"
    export MOTION_COOLDOWN="${MOTION_COOLDOWN:-5}"
    export YOLO_MODEL="${YOLO_MODEL:-yolov8n}"
    export YOLO_CONFIDENCE="${YOLO_CONFIDENCE:-0.5}"
    export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
    export SCREENSHOT_BEFORE="${SCREENSHOT_BEFORE:-3}"
    export SCREENSHOT_AFTER="${SCREENSHOT_AFTER:-3}"
    export MQTT_TOPIC_PREFIX="${MQTT_TOPIC_PREFIX:-}"
    export MQTT_DISCOVERY="${MQTT_DISCOVERY:-false}"
    export TELEGRAM_ENABLED="${TELEGRAM_ENABLED:-false}"
    export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
    export TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
    export LOG_LEVEL="${LOG_LEVEL:-INFO}"
    export HOST="${HOST:-0.0.0.0}"
    export PORT="${PORT:-8000}"
fi

# Get MQTT credentials from Home Assistant
if [ "$HAS_BASHIO" -eq 1 ] && [ -f "${CONFIG_PATH}" ] && bashio::services.available "mqtt"; then
    export MQTT_HOST=$(bashio::services mqtt "host")
    export MQTT_PORT=$(bashio::services mqtt "port")
    export MQTT_USER=$(bashio::services mqtt "username")
    export MQTT_PASSWORD=$(bashio::services mqtt "password")
    log_info "MQTT service found: ${MQTT_HOST}:${MQTT_PORT}"
else
    log_warn "MQTT service not available"
fi

log_info "Configuration loaded"
if [ -n "${CAMERA_URL}" ]; then
    log_info "Camera URL: [set]"
else
    log_warn "Camera URL: [missing]"
fi
log_info "Color Camera URL: $( [ -n "${COLOR_CAMERA_URL}" ] && echo "[set]" || echo "[missing]" )"
log_info "Thermal Camera URL: $( [ -n "${THERMAL_CAMERA_URL}" ] && echo "[set]" || echo "[missing]" )"
log_info "Motion Sensitivity: ${MOTION_SENSITIVITY}"
log_info "YOLO Model: ${YOLO_MODEL}"
log_info "Log Level: ${LOG_LEVEL}"

# Run the application
cd /app
exec python3 -m src.main
