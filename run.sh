#!/usr/bin/with-contenv bashio

echo "Starting Thermal Dual Vision Add-on..."

# Ensure data directory exists
mkdir -p /app/data

# Sync HA Options to App Config
if [ -f /data/options.json ]; then
    echo "Syncing HA options..."
    python3 /app/sync_options.py
else
    echo "No HA options found (development mode?)"
fi

# Set Log Level from Bashio if available
if bashio::config.has_value 'log_level'; then
    export LOG_LEVEL=$(bashio::config 'log_level')
    echo "Log level set to $LOG_LEVEL"
fi

# Start go2rtc
echo "Starting go2rtc..."
/usr/local/bin/go2rtc -config /app/go2rtc.yaml &

# Start Backend
echo "Starting Backend API..."
cd /app
# We use exec to keep PID 1 or handle signals, but here we run in background
# to allow nginx to run in foreground
python3 -m app.main &

# Start Nginx (Frontend & Proxy)
echo "Starting Nginx..."
nginx -g "daemon off;"
