#!/bin/bash
set -e

echo "Starting Thermal Dual Vision Add-on (v2.1.2)..."

# 1. Sync HA Options to App Config
echo "Syncing configuration..."
# Updated path to match new directory structure inside container
python3 -u /app/thermal-dual-vision/sync_options.py

# 2. Setup Environment
# Read log level from options, default to info
export LOG_LEVEL=$(jq --raw-output '.log_level // "info"' /data/options.json)
export DATA_DIR=/config

# 3. Start go2rtc
echo "Starting go2rtc..."
/usr/local/bin/go2rtc -config /app/go2rtc.yaml &

# 4. Start Backend API
echo "Starting Backend API..."
cd /app
python3 -u -m app.main &

# 5. Start Nginx
echo "Starting Nginx..."
nginx -g "daemon off;"
