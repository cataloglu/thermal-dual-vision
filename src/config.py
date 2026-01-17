"""Configuration management for Smart Motion Detector."""

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union


@dataclass
class CameraConfig:
    """Camera configuration."""
    url: str = ""
    fps: int = 5
    resolution: tuple = (1280, 720)


@dataclass
class MotionConfig:
    """Motion detection configuration."""
    sensitivity: int = 7
    min_area: int = 500
    cooldown_seconds: int = 5


@dataclass
class YoloConfig:
    """YOLO detection configuration."""
    model: str = "yolov8n"
    confidence: float = 0.5
    classes: List[str] = field(default_factory=lambda: ["person", "car", "dog", "cat"])


@dataclass
class LLMConfig:
    """LLM Vision configuration."""
    api_key: str = ""
    model: str = "gpt-4-vision-preview"
    max_tokens: int = 1000
    timeout: int = 30


@dataclass
class ScreenshotConfig:
    """Screenshot configuration."""
    before_seconds: int = 3
    after_seconds: int = 3
    quality: int = 85
    max_stored: int = 100
    buffer_seconds: int = 10


@dataclass
class MQTTConfig:
    """MQTT configuration."""
    host: str = "core-mosquitto"
    port: int = 1883
    username: str = ""
    password: str = ""
    topic_prefix: str = "smart_motion"
    discovery: bool = True
    discovery_prefix: str = "homeassistant"
    qos: int = 1


@dataclass
class TelegramConfig:
    """Telegram bot configuration."""
    enabled: bool = False
    bot_token: str = ""
    chat_ids: List[str] = field(default_factory=list)
    rate_limit_seconds: int = 5


@dataclass
class Config:
    """Main application configuration."""
    camera: CameraConfig = field(default_factory=CameraConfig)
    motion: MotionConfig = field(default_factory=MotionConfig)
    yolo: YoloConfig = field(default_factory=YoloConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    screenshots: ScreenshotConfig = field(default_factory=ScreenshotConfig)
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    log_level: str = "INFO"
    ha_mode: bool = True

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config = cls()

        # Camera
        config.camera.url = os.getenv("CAMERA_URL", "")
        config.camera.fps = int(os.getenv("CAMERA_FPS", "5"))

        # Motion
        config.motion.sensitivity = int(os.getenv("MOTION_SENSITIVITY", "7"))
        config.motion.min_area = int(os.getenv("MOTION_MIN_AREA", "500"))
        config.motion.cooldown_seconds = int(os.getenv("MOTION_COOLDOWN", "5"))

        # YOLO
        config.yolo.model = os.getenv("YOLO_MODEL", "yolov8n")
        config.yolo.confidence = float(os.getenv("YOLO_CONFIDENCE", "0.5"))

        # LLM
        config.llm.api_key = os.getenv("OPENAI_API_KEY", "")

        # Screenshots
        config.screenshots.before_seconds = int(os.getenv("SCREENSHOT_BEFORE", "3"))
        config.screenshots.after_seconds = int(os.getenv("SCREENSHOT_AFTER", "3"))

        # MQTT
        config.mqtt.host = os.getenv("MQTT_HOST", "core-mosquitto")
        config.mqtt.port = int(os.getenv("MQTT_PORT", "1883"))
        config.mqtt.username = os.getenv("MQTT_USER", "")
        config.mqtt.password = os.getenv("MQTT_PASSWORD", "")
        config.mqtt.topic_prefix = os.getenv("MQTT_TOPIC_PREFIX", "smart_motion")
        config.mqtt.discovery = os.getenv("MQTT_DISCOVERY", "true").lower() == "true"

        # Telegram
        config.telegram.enabled = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
        config.telegram.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_ids_str = os.getenv("TELEGRAM_CHAT_ID", "")
        if chat_ids_str:
            config.telegram.chat_ids = [cid.strip() for cid in chat_ids_str.split(",")]

        # Logging
        config.log_level = os.getenv("LOG_LEVEL", "INFO")

        # HA Mode
        config.ha_mode = os.getenv("HA_MODE", "true").lower() == "true"

        return config

    @classmethod
    def from_yaml(cls, config_path: Union[str, Path]) -> "Config":
        """Load configuration from YAML file."""
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)

        if data is None:
            data = {}

        config = cls()

        # Camera
        if "camera" in data:
            cam_data = data["camera"]
            if "url" in cam_data:
                config.camera.url = cam_data["url"]
            if "fps" in cam_data:
                config.camera.fps = int(cam_data["fps"])
            if "resolution" in cam_data:
                config.camera.resolution = tuple(cam_data["resolution"])

        # Motion
        if "motion" in data:
            motion_data = data["motion"]
            if "sensitivity" in motion_data:
                config.motion.sensitivity = int(motion_data["sensitivity"])
            if "min_area" in motion_data:
                config.motion.min_area = int(motion_data["min_area"])
            if "cooldown_seconds" in motion_data:
                config.motion.cooldown_seconds = int(motion_data["cooldown_seconds"])

        # YOLO
        if "yolo" in data:
            yolo_data = data["yolo"]
            if "model" in yolo_data:
                config.yolo.model = yolo_data["model"]
            if "confidence" in yolo_data:
                config.yolo.confidence = float(yolo_data["confidence"])
            if "classes" in yolo_data:
                config.yolo.classes = yolo_data["classes"]

        # LLM
        if "llm" in data:
            llm_data = data["llm"]
            if "api_key" in llm_data:
                config.llm.api_key = llm_data["api_key"]
            if "model" in llm_data:
                config.llm.model = llm_data["model"]
            if "max_tokens" in llm_data:
                config.llm.max_tokens = int(llm_data["max_tokens"])
            if "timeout" in llm_data:
                config.llm.timeout = int(llm_data["timeout"])

        # Screenshots
        if "screenshots" in data:
            screenshot_data = data["screenshots"]
            if "before_seconds" in screenshot_data:
                config.screenshots.before_seconds = int(screenshot_data["before_seconds"])
            if "after_seconds" in screenshot_data:
                config.screenshots.after_seconds = int(screenshot_data["after_seconds"])
            if "quality" in screenshot_data:
                config.screenshots.quality = int(screenshot_data["quality"])
            if "max_stored" in screenshot_data:
                config.screenshots.max_stored = int(screenshot_data["max_stored"])
            if "buffer_seconds" in screenshot_data:
                config.screenshots.buffer_seconds = int(screenshot_data["buffer_seconds"])

        # MQTT
        if "mqtt" in data:
            mqtt_data = data["mqtt"]
            if "host" in mqtt_data:
                config.mqtt.host = mqtt_data["host"]
            if "port" in mqtt_data:
                config.mqtt.port = int(mqtt_data["port"])
            if "username" in mqtt_data:
                config.mqtt.username = mqtt_data["username"]
            if "password" in mqtt_data:
                config.mqtt.password = mqtt_data["password"]
            if "topic_prefix" in mqtt_data:
                config.mqtt.topic_prefix = mqtt_data["topic_prefix"]
            if "discovery" in mqtt_data:
                config.mqtt.discovery = bool(mqtt_data["discovery"])
            if "discovery_prefix" in mqtt_data:
                config.mqtt.discovery_prefix = mqtt_data["discovery_prefix"]
            if "qos" in mqtt_data:
                config.mqtt.qos = int(mqtt_data["qos"])

        # Telegram
        if "telegram" in data:
            telegram_data = data["telegram"]
            if "enabled" in telegram_data:
                config.telegram.enabled = bool(telegram_data["enabled"])
            if "bot_token" in telegram_data:
                config.telegram.bot_token = telegram_data["bot_token"]
            if "chat_ids" in telegram_data:
                config.telegram.chat_ids = telegram_data["chat_ids"]
            if "rate_limit_seconds" in telegram_data:
                config.telegram.rate_limit_seconds = int(telegram_data["rate_limit_seconds"])

        # Logging
        if "log_level" in data:
            config.log_level = data["log_level"]

        # HA Mode
        if "ha_mode" in data:
            config.ha_mode = bool(data["ha_mode"])

        return config

    @classmethod
    def from_sources(cls, config_path: Optional[Union[str, Path]] = None) -> "Config":
        """Load configuration from multiple sources with priority: env > YAML > defaults.

        Args:
            config_path: Optional path to YAML config file

        Returns:
            Config: Configuration object with values from all sources
        """
        # Start with defaults and YAML if provided
        if config_path is not None:
            config_path = Path(config_path)
            if config_path.exists():
                config = cls.from_yaml(config_path)
            else:
                config = cls()
        else:
            config = cls()

        # Override with environment variables if they are set
        # Camera
        if "CAMERA_URL" in os.environ:
            config.camera.url = os.environ["CAMERA_URL"]
        if "CAMERA_FPS" in os.environ:
            config.camera.fps = int(os.environ["CAMERA_FPS"])

        # Motion
        if "MOTION_SENSITIVITY" in os.environ:
            config.motion.sensitivity = int(os.environ["MOTION_SENSITIVITY"])
        if "MOTION_MIN_AREA" in os.environ:
            config.motion.min_area = int(os.environ["MOTION_MIN_AREA"])
        if "MOTION_COOLDOWN" in os.environ:
            config.motion.cooldown_seconds = int(os.environ["MOTION_COOLDOWN"])

        # YOLO
        if "YOLO_MODEL" in os.environ:
            config.yolo.model = os.environ["YOLO_MODEL"]
        if "YOLO_CONFIDENCE" in os.environ:
            config.yolo.confidence = float(os.environ["YOLO_CONFIDENCE"])

        # LLM
        if "OPENAI_API_KEY" in os.environ:
            config.llm.api_key = os.environ["OPENAI_API_KEY"]

        # Screenshots
        if "SCREENSHOT_BEFORE" in os.environ:
            config.screenshots.before_seconds = int(os.environ["SCREENSHOT_BEFORE"])
        if "SCREENSHOT_AFTER" in os.environ:
            config.screenshots.after_seconds = int(os.environ["SCREENSHOT_AFTER"])

        # MQTT
        if "MQTT_HOST" in os.environ:
            config.mqtt.host = os.environ["MQTT_HOST"]
        if "MQTT_PORT" in os.environ:
            config.mqtt.port = int(os.environ["MQTT_PORT"])
        if "MQTT_USER" in os.environ:
            config.mqtt.username = os.environ["MQTT_USER"]
        if "MQTT_PASSWORD" in os.environ:
            config.mqtt.password = os.environ["MQTT_PASSWORD"]
        if "MQTT_TOPIC_PREFIX" in os.environ:
            config.mqtt.topic_prefix = os.environ["MQTT_TOPIC_PREFIX"]
        if "MQTT_DISCOVERY" in os.environ:
            config.mqtt.discovery = os.environ["MQTT_DISCOVERY"].lower() == "true"

        # Telegram
        if "TELEGRAM_ENABLED" in os.environ:
            config.telegram.enabled = os.environ["TELEGRAM_ENABLED"].lower() == "true"
        if "TELEGRAM_BOT_TOKEN" in os.environ:
            config.telegram.bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
        if "TELEGRAM_CHAT_ID" in os.environ:
            chat_ids_str = os.environ["TELEGRAM_CHAT_ID"]
            if chat_ids_str:
                config.telegram.chat_ids = [cid.strip() for cid in chat_ids_str.split(",")]

        # Logging
        if "LOG_LEVEL" in os.environ:
            config.log_level = os.environ["LOG_LEVEL"]

        # HA Mode
        if "HA_MODE" in os.environ:
            config.ha_mode = os.environ["HA_MODE"].lower() == "true"

        return config

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not self.camera.url:
            errors.append("Camera URL is required")

        if not self.llm.api_key:
            errors.append("OpenAI API key is required")

        if self.telegram.enabled:
            if not self.telegram.bot_token:
                errors.append("Telegram bot token is required when enabled")
            if not self.telegram.chat_ids:
                errors.append("Telegram chat ID is required when enabled")

        return errors
