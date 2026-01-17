#!/usr/bin/env python3
"""Manual test script for standalone mode config loading.

This script validates that config loading works correctly in standalone mode:
1. HA_MODE=false is set
2. Config is read from config.yaml
3. Environment variables override YAML values
4. Default values are used when appropriate
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

import yaml
from src.config import Config


def test_ha_mode_false():
    """Test 1: HA_MODE=false from environment."""
    print("\n=== Test 1: HA_MODE=false from environment ===")
    os.environ["HA_MODE"] = "false"
    config = Config.from_env()
    assert config.ha_mode is False, f"Expected ha_mode=False, got {config.ha_mode}"
    print("✓ HA_MODE=false correctly loaded from environment")
    del os.environ["HA_MODE"]


def test_config_yaml_reading():
    """Test 2: Config is read from config.yaml."""
    print("\n=== Test 2: Config reading from config.yaml ===")
    config_path = Path("config/config.yaml")

    if not config_path.exists():
        print("⚠ config/config.yaml not found, skipping test")
        return

    config = Config.from_yaml(config_path)

    # Verify YAML values
    assert config.ha_mode is False, f"Expected ha_mode=False from YAML, got {config.ha_mode}"
    assert config.camera.url == "rtsp://example.com/stream", f"Expected camera URL from YAML, got {config.camera.url}"
    assert config.mqtt.username == "yaml-user", f"Expected MQTT username from YAML, got {config.mqtt.username}"
    assert config.llm.api_key == "yaml-api-key", f"Expected LLM API key from YAML, got {config.llm.api_key}"

    print(f"✓ Config loaded from YAML:")
    print(f"  - ha_mode: {config.ha_mode}")
    print(f"  - camera.url: {config.camera.url}")
    print(f"  - mqtt.username: {config.mqtt.username}")
    print(f"  - llm.api_key: {config.llm.api_key}")


def test_env_overrides_yaml():
    """Test 3: Environment variables override YAML values."""
    print("\n=== Test 3: Environment variables override YAML ===")

    # Create temporary YAML config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml_config = {
            'camera': {'url': 'rtsp://yaml.com/stream', 'fps': 5},
            'mqtt': {'host': 'yaml-host', 'username': 'yaml-user'},
            'llm': {'api_key': 'yaml-api-key'},
            'ha_mode': False
        }
        yaml.dump(yaml_config, f)
        temp_path = f.name

    try:
        # Set environment variables
        os.environ["CAMERA_URL"] = "rtsp://env.com/stream"
        os.environ["MQTT_HOST"] = "env-host"
        os.environ["MQTT_USER"] = "env-user"
        os.environ["OPENAI_API_KEY"] = "env-api-key"
        os.environ["HA_MODE"] = "true"

        # Load with priority: env > yaml > defaults
        config = Config.from_sources(temp_path)

        # Verify env vars took precedence
        assert config.camera.url == "rtsp://env.com/stream", f"Expected env camera URL, got {config.camera.url}"
        assert config.mqtt.host == "env-host", f"Expected env MQTT host, got {config.mqtt.host}"
        assert config.mqtt.username == "env-user", f"Expected env MQTT username, got {config.mqtt.username}"
        assert config.llm.api_key == "env-api-key", f"Expected env API key, got {config.llm.api_key}"
        assert config.ha_mode is True, f"Expected env ha_mode=True, got {config.ha_mode}"

        print("✓ Environment variables correctly override YAML values:")
        print(f"  - camera.url: {config.camera.url} (from env)")
        print(f"  - mqtt.host: {config.mqtt.host} (from env)")
        print(f"  - mqtt.username: {config.mqtt.username} (from env)")
        print(f"  - llm.api_key: {config.llm.api_key} (from env)")
        print(f"  - ha_mode: {config.ha_mode} (from env)")
        print(f"  - camera.fps: {config.camera.fps} (from yaml, not overridden)")

    finally:
        os.unlink(temp_path)
        for key in ["CAMERA_URL", "MQTT_HOST", "MQTT_USER", "OPENAI_API_KEY", "HA_MODE"]:
            if key in os.environ:
                del os.environ[key]


def test_priority_order():
    """Test 4: Complete priority order (env > yaml > defaults)."""
    print("\n=== Test 4: Priority order (env > yaml > defaults) ===")

    # Create YAML with some values
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml_config = {
            'camera': {'url': 'rtsp://yaml.com/stream', 'fps': 15},
            'motion': {'sensitivity': 8},
        }
        yaml.dump(yaml_config, f)
        temp_path = f.name

    try:
        # Set only one env var
        os.environ["CAMERA_URL"] = "rtsp://env.com/stream"

        config = Config.from_sources(temp_path)

        # From env (highest priority)
        assert config.camera.url == "rtsp://env.com/stream"
        print(f"  ✓ camera.url: {config.camera.url} (from env - highest priority)")

        # From YAML (medium priority)
        assert config.camera.fps == 15
        assert config.motion.sensitivity == 8
        print(f"  ✓ camera.fps: {config.camera.fps} (from yaml - medium priority)")
        print(f"  ✓ motion.sensitivity: {config.motion.sensitivity} (from yaml - medium priority)")

        # From defaults (lowest priority)
        assert config.motion.cooldown_seconds == 5
        assert config.yolo.model == "yolov8n"
        print(f"  ✓ motion.cooldown_seconds: {config.motion.cooldown_seconds} (from defaults - lowest priority)")
        print(f"  ✓ yolo.model: {config.yolo.model} (from defaults - lowest priority)")

        print("✓ Priority order working correctly: env > yaml > defaults")

    finally:
        os.unlink(temp_path)
        if "CAMERA_URL" in os.environ:
            del os.environ["CAMERA_URL"]


def test_standalone_mode_integration():
    """Test 5: Full standalone mode integration test."""
    print("\n=== Test 5: Full standalone mode integration ===")
    config_path = Path("config/config.yaml")

    if not config_path.exists():
        print("⚠ config/config.yaml not found, skipping test")
        return

    # Set HA_MODE to false (standalone mode)
    os.environ["HA_MODE"] = "false"

    # Override one value with env var
    os.environ["MQTT_HOST"] = "env-mqtt-override"

    try:
        config = Config.from_sources(config_path)

        # Verify standalone mode
        assert config.ha_mode is False
        print(f"✓ Standalone mode active (ha_mode={config.ha_mode})")

        # Verify YAML values loaded
        assert config.camera.url == "rtsp://example.com/stream"
        assert config.llm.api_key == "yaml-api-key"
        print(f"✓ Config loaded from YAML file:")
        print(f"  - camera.url: {config.camera.url}")
        print(f"  - llm.api_key: {config.llm.api_key}")

        # Verify env override
        assert config.mqtt.host == "env-mqtt-override"
        print(f"✓ Environment override working:")
        print(f"  - mqtt.host: {config.mqtt.host} (overridden by env var)")

    finally:
        for key in ["HA_MODE", "MQTT_HOST"]:
            if key in os.environ:
                del os.environ[key]


def main():
    """Run all tests."""
    print("="*70)
    print("STANDALONE MODE CONFIG LOADING TESTS")
    print("="*70)

    tests = [
        test_ha_mode_false,
        test_config_yaml_reading,
        test_env_overrides_yaml,
        test_priority_order,
        test_standalone_mode_integration,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ TEST FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ TEST ERROR: {e}")
            failed += 1

    print("\n" + "="*70)
    if failed == 0:
        print("✓ ALL TESTS PASSED")
        print("="*70)
        return 0
    else:
        print(f"✗ {failed} TEST(S) FAILED")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
