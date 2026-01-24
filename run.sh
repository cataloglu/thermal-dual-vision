#!/bin/bash

echo "Starting Thermal Dual Vision..."

# Ensure data directory exists
mkdir -p /app/data

# Sync options from HA if available (simple python script)
if [ -f /data/options.json ]; then
    echo "Syncing HA options..."
    python3 /app/sync_options.py
fi

# Start go2rtc
echo "Starting go2rtc..."
/usr/local/bin/go2rtc -config /app/go2rtc.yaml &

# Start Backend
echo "Starting Backend API..."
cd /app
python3 -m app.main &

# Start Nginx
echo "Starting Nginx..."
# Daemon off keeps the container running
nginx -g "daemon off;"
