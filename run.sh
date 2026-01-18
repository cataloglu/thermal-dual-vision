#!/usr/bin/env bash

# Smart Motion Detector - Entry Point
# Home Assistant Add-on runner script

set -e

CONFIG_PATH=/data/options.json

# Load container environment variables when running under s6.
if [ -d /run/s6/container_environment ]; then
    for env_file in /run/s6/container_environment/*; do
        env_key=$(basename "$env_file")
        if [ -n "${env_key}" ] && [ -z "${!env_key+x}" ]; then
            export "${env_key}=$(cat "$env_file")"
        fi
    done
fi

HAS_BASHIO=0
HAS_CONFIG=0
if [ -x /usr/bin/bashio ] || [ -f /usr/lib/bashio/bashio.sh ]; then
    # Home Assistant add-on environment
    # shellcheck source=/usr/lib/bashio/bashio.sh
    . /usr/lib/bashio/bashio.sh
    HAS_BASHIO=1
fi
if [ -f "${CONFIG_PATH}" ]; then
    HAS_CONFIG=1
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

set_config_if_present() {
    local key="$1"
    local var_name="$2"
    local value
    value=$(bashio::config "$key")
    if [ -n "${value}" ] && [ "${value}" != "null" ]; then
        export "${var_name}=${value}"
    fi
}

if [ "$HAS_BASHIO" -eq 1 ] && [ "$HAS_CONFIG" -eq 1 ]; then
    # Read configuration from Home Assistant
    set_config_if_present 'camera_url' 'CAMERA_URL'
    set_config_if_present 'camera_type' 'CAMERA_TYPE'
    set_config_if_present 'color_camera_url' 'COLOR_CAMERA_URL'
    set_config_if_present 'thermal_camera_url' 'THERMAL_CAMERA_URL'
    set_config_if_present 'camera_fps' 'CAMERA_FPS'
    set_config_if_present 'motion_sensitivity' 'MOTION_SENSITIVITY'
    set_config_if_present 'motion_min_area' 'MOTION_MIN_AREA'
    set_config_if_present 'motion_cooldown' 'MOTION_COOLDOWN'
    set_config_if_present 'yolo_model' 'YOLO_MODEL'
    set_config_if_present 'yolo_confidence' 'YOLO_CONFIDENCE'
    set_config_if_present 'openai_api_key' 'OPENAI_API_KEY'
    set_config_if_present 'screenshot_before_sec' 'SCREENSHOT_BEFORE'
    set_config_if_present 'screenshot_after_sec' 'SCREENSHOT_AFTER'
    set_config_if_present 'mqtt_topic_prefix' 'MQTT_TOPIC_PREFIX'
    set_config_if_present 'mqtt_discovery' 'MQTT_DISCOVERY'
    set_config_if_present 'telegram_enabled' 'TELEGRAM_ENABLED'
    set_config_if_present 'telegram_bot_token' 'TELEGRAM_BOT_TOKEN'
    set_config_if_present 'telegram_chat_id' 'TELEGRAM_CHAT_ID'
    set_config_if_present 'log_level' 'LOG_LEVEL'
    set_config_if_present 'host' 'HOST'
    set_config_if_present 'port' 'PORT'
else
    # Local Docker fallback
    if [ "$HAS_BASHIO" -eq 1 ]; then
        log_warn "Home Assistant config not found, using environment defaults."
    fi
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
    export SCREENSHOT_BEFORE="${SCREENSHOT_BEFORE:-3}"
    export SCREENSHOT_AFTER="${SCREENSHOT_AFTER:-3}"
    export MQTT_TOPIC_PREFIX="${MQTT_TOPIC_PREFIX:-}"
    export MQTT_DISCOVERY="${MQTT_DISCOVERY:-false}"
    export TELEGRAM_ENABLED="${TELEGRAM_ENABLED:-false}"
    export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
    export TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
    export LOG_LEVEL="${LOG_LEVEL:-INFO}"
fi

export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8000}"

# Get MQTT credentials from Home Assistant
if [ "$HAS_BASHIO" -eq 1 ] && [ "$HAS_CONFIG" -eq 1 ] && bashio::services.available "mqtt"; then
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
