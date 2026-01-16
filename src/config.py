"""Configuration management for Smart Motion Detector."""

import os
from dataclasses import dataclass, field
from typing import List, Optional


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
