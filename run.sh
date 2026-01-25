#!/bin/bash

echo "Starting Thermal Dual Vision..."

# Ensure data directory exists
mkdir -p /app/data

# ---------------------------------------------------------
# AUTO-DISCOVER MQTT FROM HA SUPERVISOR API
# ---------------------------------------------------------
if [ -n "$SUPERVISOR_TOKEN" ]; then
    echo "Querying HA Supervisor for MQTT service..."
    
    # Get MQTT service info
    MQTT_INFO=$(curl -s -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/services/mqtt)
    
    # Check if result is valid JSON and has host
    if echo "$MQTT_INFO" | jq -e '.result == "ok"' > /dev/null; then
        echo "MQTT Service found! configuring..."
        
        MQTT_HOST=$(echo "$MQTT_INFO" | jq -r '.data.host')
        MQTT_PORT=$(echo "$MQTT_INFO" | jq -r '.data.port')
        MQTT_USER=$(echo "$MQTT_INFO" | jq -r '.data.username')
        MQTT_PASS=$(echo "$MQTT_INFO" | jq -r '.data.password')
        
        # Export as ENV variables for Python app
        export MQTT_HOST="$MQTT_HOST"
        export MQTT_PORT="$MQTT_PORT"
        export MQTT_USER="$MQTT_USER"
        export MQTT_PASS="$MQTT_PASS"
        
        # Also update config.json directly to persist settings
        # We use a small python script to inject these into config.json
        python3 -c "
import json
import os

config_path = '/app/data/config.json'
try:
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            data = json.load(f)
    else:
        data = {}

    if 'mqtt' not in data:
        data['mqtt'] = {}

    data['mqtt']['enabled'] = True
    data['mqtt']['host'] = '$MQTT_HOST'
    data['mqtt']['port'] = int('$MQTT_PORT')
    data['mqtt']['username'] = '$MQTT_USER'
    data['mqtt']['password'] = '$MQTT_PASS'

    with open(config_path, 'w') as f:
        json.dump(data, f, indent=2)
    print('Updated config.json with auto-discovered MQTT settings')
except Exception as e:
    print(f'Failed to update config: {e}')
"
    else:
        echo "MQTT Service not available via Supervisor."
    fi
fi
# ---------------------------------------------------------

# Start go2rtc
echo "Starting go2rtc..."
/usr/local/bin/go2rtc -config /app/go2rtc.yaml &

# Fix stream_roles for existing cameras (migration)
echo "Checking database migrations..."
if [ -f /app/data/app.db ]; then
    python3 /app/fix_stream_roles.py || true
fi

# Start Backend
echo "Starting Backend API..."
cd /app
python3 -m app.main &

# Start Nginx
echo "Starting Nginx..."
# Daemon off keeps the container running
nginx -g "daemon off;"
