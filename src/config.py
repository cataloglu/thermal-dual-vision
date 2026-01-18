"""Configuration management for Smart Motion Detector."""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlsplit, urlunsplit


@dataclass
class CameraConfig:
    """Camera configuration."""
    url: str = ""
    fps: int = 5
    resolution: tuple = (1280, 720)
    camera_type: str = "color"
    color_url: str = ""
    thermal_url: str = ""


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
    send_images: bool = True


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
        return cls.from_sources(os.environ, saved=None)

    @classmethod
    def from_sources(cls, env: Mapping[str, str], saved: Optional[Dict[str, Any]]) -> "Config":
        """Load configuration from env overrides and saved config."""
        config = cls()
        if saved:
            _apply_saved_config(config, saved)

        # Camera
        _apply_env_str(env, "CAMERA_URL", lambda value: setattr(config.camera, "url", value))
        _apply_env_int(env, "CAMERA_FPS", lambda value: setattr(config.camera, "fps", value), config.camera.fps)
        _apply_env_str(
            env,
            "CAMERA_TYPE",
            lambda value: setattr(config.camera, "camera_type", value.lower()),
        )
        _apply_env_str(env, "COLOR_CAMERA_URL", lambda value: setattr(config.camera, "color_url", value))
        _apply_env_str(env, "THERMAL_CAMERA_URL", lambda value: setattr(config.camera, "thermal_url", value))

        # Motion
        _apply_env_int(
            env,
            "MOTION_SENSITIVITY",
            lambda value: setattr(config.motion, "sensitivity", value),
            config.motion.sensitivity,
        )
        _apply_env_int(
            env,
            "MOTION_MIN_AREA",
            lambda value: setattr(config.motion, "min_area", value),
            config.motion.min_area,
        )
        _apply_env_int(
            env,
            "MOTION_COOLDOWN",
            lambda value: setattr(config.motion, "cooldown_seconds", value),
            config.motion.cooldown_seconds,
        )

        # YOLO
        _apply_env_str(env, "YOLO_MODEL", lambda value: setattr(config.yolo, "model", value))
        _apply_env_float(
            env,
            "YOLO_CONFIDENCE",
            lambda value: setattr(config.yolo, "confidence", value),
            config.yolo.confidence,
        )

        # LLM
        _apply_env_str(env, "OPENAI_API_KEY", lambda value: setattr(config.llm, "api_key", value))

        # Screenshots
        _apply_env_int(
            env,
            "SCREENSHOT_BEFORE",
            lambda value: setattr(config.screenshots, "before_seconds", value),
            config.screenshots.before_seconds,
        )
        _apply_env_int(
            env,
            "SCREENSHOT_AFTER",
            lambda value: setattr(config.screenshots, "after_seconds", value),
            config.screenshots.after_seconds,
        )

        # MQTT
        _apply_env_str(env, "MQTT_HOST", lambda value: setattr(config.mqtt, "host", value))
        _apply_env_int(
            env,
            "MQTT_PORT",
            lambda value: setattr(config.mqtt, "port", value),
            config.mqtt.port,
        )
        _apply_env_str(env, "MQTT_USER", lambda value: setattr(config.mqtt, "username", value))
        _apply_env_str(env, "MQTT_PASSWORD", lambda value: setattr(config.mqtt, "password", value))
        _apply_env_str(
            env,
            "MQTT_TOPIC_PREFIX",
            lambda value: setattr(config.mqtt, "topic_prefix", value),
        )
        _apply_env_bool(
            env,
            "MQTT_DISCOVERY",
            lambda value: setattr(config.mqtt, "discovery", value),
            config.mqtt.discovery,
        )

        # Telegram
        _apply_env_bool(
            env,
            "TELEGRAM_ENABLED",
            lambda value: setattr(config.telegram, "enabled", value),
            config.telegram.enabled,
        )
        _apply_env_str(env, "TELEGRAM_BOT_TOKEN", lambda value: setattr(config.telegram, "bot_token", value))
        chat_ids_str = env.get("TELEGRAM_CHAT_ID", "")
        if chat_ids_str:
            config.telegram.chat_ids = [cid.strip() for cid in chat_ids_str.split(",")]

        # Logging
        _apply_env_str(env, "LOG_LEVEL", lambda value: setattr(config, "log_level", value))

        return config

    def to_dict(self, redact: bool = False) -> Dict[str, Any]:
        """Return config as nested dict."""
        data = {
            "camera": {
                "url": self.camera.url,
                "fps": self.camera.fps,
                "resolution": self.camera.resolution,
                "camera_type": self.camera.camera_type,
                "color_url": self.camera.color_url,
                "thermal_url": self.camera.thermal_url,
            },
            "motion": {
                "sensitivity": self.motion.sensitivity,
                "min_area": self.motion.min_area,
                "cooldown_seconds": self.motion.cooldown_seconds,
            },
            "yolo": {
                "model": self.yolo.model,
                "confidence": self.yolo.confidence,
                "classes": self.yolo.classes,
            },
            "llm": {
                "api_key": self.llm.api_key,
                "model": self.llm.model,
                "max_tokens": self.llm.max_tokens,
                "timeout": self.llm.timeout,
            },
            "screenshots": {
                "before_seconds": self.screenshots.before_seconds,
                "after_seconds": self.screenshots.after_seconds,
                "quality": self.screenshots.quality,
                "max_stored": self.screenshots.max_stored,
                "buffer_seconds": self.screenshots.buffer_seconds,
            },
            "mqtt": {
                "host": self.mqtt.host,
                "port": self.mqtt.port,
                "username": self.mqtt.username,
                "password": self.mqtt.password,
                "topic_prefix": self.mqtt.topic_prefix,
                "discovery": self.mqtt.discovery,
                "discovery_prefix": self.mqtt.discovery_prefix,
                "qos": self.mqtt.qos,
            },
            "telegram": {
                "enabled": self.telegram.enabled,
                "bot_token": self.telegram.bot_token,
                "chat_ids": self.telegram.chat_ids,
                "rate_limit_seconds": self.telegram.rate_limit_seconds,
                "send_images": self.telegram.send_images,
            },
            "log_level": self.log_level,
        }

        if redact:
            _redact_config(data)
        return data

    def validate(self, allow_incomplete: bool = False) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if self.camera.camera_type not in {"color", "thermal", "dual"}:
            errors.append("Camera type must be 'color', 'thermal', or 'dual'")

        if not allow_incomplete:
            if self.camera.camera_type == "dual":
                if not self.camera.color_url:
                    errors.append("Color camera URL is required for dual mode")
                if not self.camera.thermal_url:
                    errors.append("Thermal camera URL is required for dual mode")
            elif not self.camera.url:
                errors.append("Camera URL is required")

            if self.telegram.enabled:
                if not self.telegram.bot_token:
                    errors.append("Telegram bot token is required when enabled")
                if not self.telegram.chat_ids:
                    errors.append("Telegram chat ID is required when enabled")

        return errors


def _apply_env_str(
    env: Mapping[str, str],
    key: str,
    setter,
) -> None:
    value = env.get(key)
    if value is not None and value != "":
        setter(value)


def _apply_env_int(
    env: Mapping[str, str],
    key: str,
    setter,
    default: int,
) -> None:
    value = env.get(key)
    if value is None or value == "":
        return
    try:
        setter(int(value))
    except ValueError:
        setter(default)


def _apply_env_float(
    env: Mapping[str, str],
    key: str,
    setter,
    default: float,
) -> None:
    value = env.get(key)
    if value is None or value == "":
        return
    try:
        setter(float(value))
    except ValueError:
        setter(default)


def _apply_env_bool(
    env: Mapping[str, str],
    key: str,
    setter,
    default: bool,
) -> None:
    value = env.get(key)
    if value is None or value == "":
        return
    setter(value.lower() == "true")


def _apply_saved_config(config: Config, saved: Dict[str, Any]) -> None:
    camera = saved.get("camera", {})
    if "camera_url" in saved:
        config.camera.url = saved.get("camera_url") or config.camera.url
    config.camera.url = camera.get("url", config.camera.url)
    config.camera.fps = camera.get("fps", config.camera.fps)
    config.camera.camera_type = camera.get("camera_type", config.camera.camera_type)
    config.camera.color_url = camera.get("color_url", config.camera.color_url)
    config.camera.thermal_url = camera.get("thermal_url", config.camera.thermal_url)

    motion = saved.get("motion", {})
    config.motion.sensitivity = motion.get("sensitivity", config.motion.sensitivity)
    config.motion.min_area = motion.get("min_area", config.motion.min_area)
    config.motion.cooldown_seconds = motion.get("cooldown_seconds", config.motion.cooldown_seconds)

    yolo = saved.get("yolo", {})
    config.yolo.model = yolo.get("model", config.yolo.model)
    config.yolo.confidence = yolo.get("confidence", config.yolo.confidence)
    config.yolo.classes = yolo.get("classes", config.yolo.classes)

    llm = saved.get("llm", {})
    if "openai_api_key" in saved:
        config.llm.api_key = saved.get("openai_api_key") or config.llm.api_key
    config.llm.api_key = llm.get("api_key", config.llm.api_key)
    config.llm.model = llm.get("model", config.llm.model)
    config.llm.max_tokens = llm.get("max_tokens", config.llm.max_tokens)
    config.llm.timeout = llm.get("timeout", config.llm.timeout)

    screenshots = saved.get("screenshots", {})
    config.screenshots.before_seconds = screenshots.get(
        "before_seconds", config.screenshots.before_seconds
    )
    config.screenshots.after_seconds = screenshots.get(
        "after_seconds", config.screenshots.after_seconds
    )
    config.screenshots.quality = screenshots.get("quality", config.screenshots.quality)
    config.screenshots.max_stored = screenshots.get("max_stored", config.screenshots.max_stored)
    config.screenshots.buffer_seconds = screenshots.get(
        "buffer_seconds", config.screenshots.buffer_seconds
    )

    mqtt = saved.get("mqtt", {})
    config.mqtt.host = mqtt.get("host", config.mqtt.host)
    config.mqtt.port = mqtt.get("port", config.mqtt.port)
    config.mqtt.username = mqtt.get("username", config.mqtt.username)
    config.mqtt.password = mqtt.get("password", config.mqtt.password)
    config.mqtt.topic_prefix = mqtt.get("topic_prefix", config.mqtt.topic_prefix)
    config.mqtt.discovery = mqtt.get("discovery", config.mqtt.discovery)
    config.mqtt.discovery_prefix = mqtt.get("discovery_prefix", config.mqtt.discovery_prefix)
    config.mqtt.qos = mqtt.get("qos", config.mqtt.qos)

    telegram = saved.get("telegram", {})
    config.telegram.enabled = telegram.get("enabled", config.telegram.enabled)
    config.telegram.bot_token = telegram.get("bot_token", config.telegram.bot_token)
    chat_ids = telegram.get("chat_ids")
    if chat_ids:
        config.telegram.chat_ids = chat_ids
    config.telegram.rate_limit_seconds = telegram.get(
        "rate_limit_seconds", config.telegram.rate_limit_seconds
    )
    config.telegram.send_images = telegram.get("send_images", config.telegram.send_images)

    config.log_level = saved.get("log_level", config.log_level)


def _redact_config(config: Dict[str, Any]) -> None:
    camera = config.get("camera", {})
    camera["url"] = _redact_url(camera.get("url", ""))
    camera["color_url"] = _redact_url(camera.get("color_url", ""))
    camera["thermal_url"] = _redact_url(camera.get("thermal_url", ""))

    llm = config.get("llm", {})
    if llm.get("api_key"):
        llm["api_key"] = "***"

    mqtt = config.get("mqtt", {})
    if mqtt.get("password"):
        mqtt["password"] = "***"

    telegram = config.get("telegram", {})
    if telegram.get("bot_token"):
        telegram["bot_token"] = "***"


def _redact_url(url: str) -> str:
    if not url:
        return url
    parsed = urlsplit(url)
    if "@" not in parsed.netloc:
        return url
    userinfo, host = parsed.netloc.split("@", 1)
    if ":" in userinfo:
        user, _password = userinfo.split(":", 1)
        userinfo = f"{user}:***"
    else:
        userinfo = f"{userinfo}:***"
    return urlunsplit((parsed.scheme, f"{userinfo}@{host}", parsed.path, parsed.query, parsed.fragment))
