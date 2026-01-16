#!/usr/bin/env bashio

# Smart Motion Detector - Container Initialization
# Sets up directories, permissions, and validates prerequisites

set -e

bashio::log.info "Initializing Smart Motion Detector container..."

# Create required directories
bashio::log.info "Creating required directories..."
mkdir -p /data/screenshots
mkdir -p /data/logs
mkdir -p /app

# Set proper permissions
bashio::log.info "Setting permissions..."
chmod -R 755 /data
chmod -R 777 /data/screenshots
chmod -R 777 /data/logs

# Validate Python installation
if ! command -v python3 &> /dev/null; then
    bashio::log.error "Python3 is not installed!"
    exit 1
fi

# Validate required Python packages
bashio::log.info "Validating Python environment..."
python3 -c "import cv2, torch, paho.mqtt.client" 2>/dev/null || {
    bashio::log.warning "Some Python packages may not be installed yet"
}

# Check if configuration is accessible
if bashio::fs.file_exists '/data/options.json'; then
    bashio::log.info "Configuration file found"
else
    bashio::log.warning "Configuration file not found, will use defaults"
fi

# Validate camera URL is configured
if bashio::config.has_value 'camera_url'; then
    CAMERA_URL=$(bashio::config 'camera_url')
    if [ -z "$CAMERA_URL" ]; then
        bashio::log.warning "Camera URL is empty, please configure in add-on options"
    else
        bashio::log.info "Camera URL configured"
    fi
else
    bashio::log.warning "Camera URL not configured"
fi

# Check MQTT service availability
if bashio::services.available "mqtt"; then
    bashio::log.info "MQTT service available"
else
    bashio::log.warning "MQTT service not available - install Mosquitto broker add-on"
fi

bashio::log.info "Container initialization complete"
