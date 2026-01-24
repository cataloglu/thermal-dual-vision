"""
Script to sync Home Assistant options to App Config.
Reads /data/options.json and updates /config/config.json.
"""
import json
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("options_sync")

OPTIONS_FILE = Path("/data/options.json")
CONFIG_FILE = Path("/config/config.json")

def sync_options():
    if not OPTIONS_FILE.exists():
        logger.info("No HA options file found at /data/options.json")
        return

    try:
        with open(OPTIONS_FILE, "r") as f:
            options = json.load(f)
        
        logger.info(f"Loaded HA options: {options}")

        # Load existing config or create default structure
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        else:
            config = {
                "mqtt": {},
                "detection": {},
                "telegram": {},
                "ai": {}
            }

        # Map MQTT options
        if "mqtt" not in config:
            config["mqtt"] = {}
        
        config["mqtt"]["enabled"] = True  # Always enable if using HA Addon
        config["mqtt"]["host"] = options.get("mqtt_host", "core-mosquitto")
        config["mqtt"]["port"] = options.get("mqtt_port", 1883)
        
        user = options.get("mqtt_user")
        password = options.get("mqtt_pass")
        
        # Handle empty strings as None (Anonymous)
        config["mqtt"]["username"] = user if user else None
        config["mqtt"]["password"] = password if password else None
        
        # Map Log Level
        log_level = options.get("log_level", "info").upper()
        # We don't store log_level in config.json usually, it's env var,
        # but we can print it for run.sh to capture if needed
        
        # Save Config
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
            
        logger.info(f"Synced configuration to {CONFIG_FILE}")

    except Exception as e:
        logger.error(f"Failed to sync options: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sync_options()
