import json
import os
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HA_OPTIONS_PATH = "/data/options.json"
APP_CONFIG_PATH = "/app/data/config.json"
APP_DATA_DIR = "/app/data"

def sync_options():
    """Sync Home Assistant options to App Config."""
    if not os.path.exists(HA_OPTIONS_PATH):
        logger.warning(f"HA options file not found at {HA_OPTIONS_PATH}")
        return

    try:
        # Read HA options
        with open(HA_OPTIONS_PATH, 'r') as f:
            options = json.load(f)
        
        logger.info(f"Loaded HA options: {options.keys()}")

        # Ensure app data dir exists
        os.makedirs(APP_DATA_DIR, exist_ok=True)

        # Read existing app config or create default
        config = {}
        if os.path.exists(APP_CONFIG_PATH):
            try:
                with open(APP_CONFIG_PATH, 'r') as f:
                    config = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load existing config, starting fresh: {e}")

        # --- MAP OPTIONS ---
        
        # MQTT Settings
        if "mqtt" not in config:
            config["mqtt"] = {}
        
        config["mqtt"]["enabled"] = True  # Always enable if configured via HA
        config["mqtt"]["host"] = options.get("mqtt_host", "core-mosquitto")
        config["mqtt"]["port"] = options.get("mqtt_port", 1883)
        
        user = options.get("mqtt_user")
        password = options.get("mqtt_pass")
        
        if user:
            config["mqtt"]["username"] = user
        if password:
            config["mqtt"]["password"] = password

        # Log Level (App config doesn't have a global log level setting, but we can set it for future)
        log_level = options.get("log_level", "info").upper()
        # You might want to set env var for this in run.sh

        # Save Config
        with open(APP_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Successfully synced options to {APP_CONFIG_PATH}")

    except Exception as e:
        logger.error(f"Failed to sync options: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sync_options()
