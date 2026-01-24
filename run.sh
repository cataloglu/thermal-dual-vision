#!/usr/bin/with-contenv bashio

echo "Starting Thermal Dual Vision..."

# Sync HA Options to App Config
# TODO: Python script to parse /data/options.json and update /app/data/config.json

# Start go2rtc
echo "Starting go2rtc..."
/usr/local/bin/go2rtc -config /app/go2rtc.yaml &

# Start Backend
echo "Starting Backend API..."
cd /app
python3 -m app.main &

# Start Nginx
echo "Starting Nginx..."
nginx -g "daemon off;"
