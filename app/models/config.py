"""
Configuration models for Smart Motion Detector v2.

This module contains Pydantic models for all configuration sections.
All models include validation rules and default values.
"""
import re
from typing import List, Literal, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DetectionConfig(BaseModel):
    """YOLOv8 person detection configuration."""
    
    model: Literal["yolov8n-person", "yolov8s-person", "yolov9t", "yolov9s"] = Field(
        default="yolov8n-person",
        description="Primary model selection: yolov8n (fast), yolov8s (accurate), yolov9t (thermal), yolov9s (best)"
    )
    confidence_threshold: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for detections (higher = fewer false alarms)"
    )
    thermal_confidence_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for thermal (higher = fewer false alarms from heat blobs)"
    )
    nms_iou_threshold: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description="Non-Maximum Suppression IoU threshold"
    )
    inference_resolution: List[int] = Field(
        default=[480, 480],
        description="Inference resolution [width, height]. Lower = less CPU (e.g. 416 or 480)."
    )
    inference_fps: int = Field(
        default=3,
        ge=1,
        le=30,
        description="Frames per second for inference (lower = less CPU; 3 is a good balance)"
    )
    aspect_ratio_preset: Literal["person", "thermal_person", "custom"] = Field(
        default="person",
        description="Preset for person shape: person (general), thermal_person (thermal), custom (use min/max below)"
    )
    aspect_ratio_min: float = Field(
        default=0.2,
        ge=0.0,
        le=5.0,
        description="Minimum person aspect ratio (width/height); used when preset is custom"
    )
    aspect_ratio_max: float = Field(
        default=1.2,
        ge=0.0,
        le=5.0,
        description="Maximum person aspect ratio (width/height); used when preset is custom"
    )
    enable_tracking: bool = Field(
        default=False,
        description="Enable object tracking (future feature)"
    )

    @field_validator("inference_resolution")
    @classmethod
    def validate_resolution(cls, v: List[int]) -> List[int]:
        """Validate inference resolution."""
        if len(v) != 2:
            raise ValueError("inference_resolution must have exactly 2 values [width, height]")
        if any(x <= 0 for x in v):
            raise ValueError("Resolution values must be positive")
        return v

    @field_validator("aspect_ratio_max")
    @classmethod
    def validate_aspect_ratio(cls, v: float, info) -> float:
        values = info.data
        min_ratio = values.get("aspect_ratio_min")
        if min_ratio is not None and v < min_ratio:
            raise ValueError("aspect_ratio_max must be >= aspect_ratio_min")
        return v

    def get_effective_aspect_ratio_bounds(self) -> Tuple[float, float]:
        """Return (min_ratio, max_ratio) from preset or custom values."""
        if self.aspect_ratio_preset == "person":
            return 0.2, 1.2
        if self.aspect_ratio_preset == "thermal_person":
            return 0.25, 1.0
        return self.aspect_ratio_min, self.aspect_ratio_max


class MotionPreset(BaseModel):
    """Motion detection preset configuration."""
    
    sensitivity: int = Field(ge=1, le=10)
    min_area: int = Field(ge=0)
    cooldown_seconds: int = Field(ge=0)


class MotionConfig(BaseModel):
    """Motion detection configuration (pre-filter for person detection)."""
    
    algorithm: Literal["frame_diff", "mog2", "knn"] = Field(
        default="mog2",
        description="Algorithm: frame_diff (simple), mog2/knn (stable, fewer false alarms from shadows)"
    )
    sensitivity: int = Field(
        default=7,
        ge=1,
        le=10,
        description="Motion sensitivity (1-10 scale)"
    )
    min_area: int = Field(
        default=500,
        ge=0,
        description="Minimum pixel area for motion"
    )
    cooldown_seconds: int = Field(
        default=5,
        ge=0,
        description="Minimum time between motion detections"
    )
    presets: dict[str, MotionPreset] = Field(
        default_factory=lambda: {
            "thermal_recommended": MotionPreset(
                sensitivity=8,
                min_area=450,
                cooldown_seconds=4
            ),
            "color_recommended": MotionPreset(
                sensitivity=7,
                min_area=500,
                cooldown_seconds=5
            ),
        },
        description="Predefined motion presets"
    )


class ThermalConfig(BaseModel):
    """Thermal image enhancement configuration."""
    
    enable_enhancement: bool = Field(
        default=True,
        description="Enable thermal image enhancement"
    )
    enhancement_method: Literal["clahe", "histogram", "none"] = Field(
        default="clahe",
        description="Enhancement method"
    )
    clahe_clip_limit: float = Field(
        default=2.0,
        ge=0.0,
        description="CLAHE clip limit"
    )
    clahe_tile_size: List[int] = Field(
        default=[32, 32],
        description="CLAHE tile grid size (larger = less blockiness, e.g. 32x32)"
    )
    gaussian_blur_kernel: List[int] = Field(
        default=[3, 3],
        description="Gaussian blur kernel size [width, height]"
    )

    @field_validator("clahe_tile_size", "gaussian_blur_kernel")
    @classmethod
    def validate_size(cls, v: List[int]) -> List[int]:
        """Validate size parameters."""
        if len(v) != 2:
            raise ValueError("Size must have exactly 2 values [width, height]")
        if any(x <= 0 for x in v):
            raise ValueError("Size values must be positive")
        return v


class StreamConfig(BaseModel):
    """RTSP stream ingestion configuration (camera → backend)."""
    
    protocol: Literal["tcp", "udp"] = Field(
        default="tcp",
        description="RTSP protocol (tcp recommended)"
    )
    capture_backend: Literal["auto", "opencv", "ffmpeg"] = Field(
        default="auto",
        description="Capture backend for RTSP streams"
    )
    buffer_size: int = Field(
        default=1,
        ge=1,
        description="OpenCV VideoCapture buffer size"
    )
    reconnect_delay_seconds: int = Field(
        default=10,
        ge=1,
        description="Delay between reconnect attempts"
    )
    max_reconnect_attempts: int = Field(
        default=20,
        ge=1,
        description="Maximum reconnect attempts"
    )
    read_failure_threshold: int = Field(
        default=5,
        ge=1,
        description="Consecutive read failures before reconnect logic"
    )
    read_failure_timeout_seconds: float = Field(
        default=20.0,
        ge=1.0,
        le=60.0,
        description="Seconds without frames before reconnect"
    )


class WebRTCConfig(BaseModel):
    """WebRTC configuration."""
    
    enabled: bool = Field(
        default=False,
        description="Enable WebRTC output"
    )
    go2rtc_url: str = Field(
        default="",
        description="go2rtc server URL (required for WebRTC)"
    )


class LiveConfig(BaseModel):
    """Live view output configuration (backend → browser)."""
    
    output_mode: Literal["mjpeg", "webrtc"] = Field(
        default="mjpeg",
        description="Live stream output mode"
    )
    mjpeg_quality: int = Field(
        default=92,
        ge=50,
        le=100,
        description="JPEG quality for MJPEG stream (higher = better, more bandwidth)"
    )
    overlay_timezone: Literal["utc", "local"] = Field(
        default="local",
        description="Video overlay time: server local time or UTC (always server time, never camera OSD)"
    )
    webrtc: WebRTCConfig = Field(
        default_factory=WebRTCConfig,
        description="WebRTC configuration"
    )


class RecordConfig(BaseModel):
    """
    Recording config (minimal, no UI). Recording buffer sabit:
    - 1 saat kayıt (RECORDING_BUFFER_HOURS)
    - 5 dakikada bir temizlik (CLEANUP_INTERVAL_SEC)
    - 60 sn segment
    """
    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True, description="Always on")


class EventConfig(BaseModel):
    """Event generation configuration."""
    
    cooldown_seconds: int = Field(
        default=7,
        ge=0,
        description="Minimum time between events (higher = fewer rapid false alarms)"
    )
    prebuffer_seconds: float = Field(
        default=5.0,
        ge=0.0,
        le=60.0,
        description="Seconds of frames to keep before motion"
    )
    postbuffer_seconds: float = Field(
        default=15.0,
        ge=0.0,
        le=60.0,
        description="Seconds of frames to keep after motion"
    )
    record_fps: int = Field(
        default=10,
        ge=1,
        le=30,
        description="Frame rate for event video buffer"
    )
    frame_buffer_size: int = Field(
        default=10,
        ge=1,
        description="Frame buffer size for collage generation"
    )
    
    frame_interval: int = Field(
        default=2,
        ge=1,
        description="Frame capture interval"
    )
    min_event_duration: float = Field(
        default=1.0,
        ge=0.0,
        description="Minimum sustained detection in seconds (higher = fewer false alarms)"
    )


class MediaConfig(BaseModel):
    """Media cleanup configuration."""
    
    retention_days: int = Field(
        default=7,
        ge=0,
        le=365,
        description="Days to keep events (0 = unlimited)"
    )
    cleanup_interval_hours: int = Field(
        default=24,
        ge=1,
        description="Cleanup job interval in hours"
    )
    disk_limit_percent: int = Field(
        default=80,
        ge=50,
        le=95,
        description="Maximum disk usage percentage"
    )


class AIConfig(BaseModel):
    """OpenAI integration configuration."""
    
    enabled: bool = Field(
        default=False,
        description="Enable AI event summaries"
    )
    api_key: str = Field(
        default="",
        description="OpenAI API key (will be masked)"
    )
    model: Literal["gpt-4o", "gpt-4o-mini", "gpt-4-vision-preview"] = Field(
        default="gpt-4o",
        description="OpenAI model with vision support"
    )
    prompt_template: Literal["default", "custom"] = Field(
        default="default",
        description="Prompt template selection (default or custom)"
    )
    custom_prompt: str = Field(
        default="",
        description="Custom prompt (if template=custom)"
    )
    language: Literal["tr", "en"] = Field(
        default="tr",
        description="AI response language"
    )
    max_tokens: int = Field(
        default=200,
        ge=1,
        description="Maximum tokens per request"
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Response consistency (0.0-1.0)"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        description="API timeout in seconds"
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: str) -> str:
        """Validate OpenAI API key format."""
        if not value or value == "***REDACTED***":
            return value
        if not value.startswith("sk-"):
            raise ValueError("api_key must start with sk-")
        return value

    @field_validator("prompt_template", mode="before")
    @classmethod
    def normalize_prompt_template(cls, value: Optional[str]) -> str:
        """Normalize legacy prompt template values."""
        if not value:
            return "default"
        if value in {"simple", "security_focused", "detailed"}:
            return "default"
        return value


class TelegramConfig(BaseModel):
    """Telegram notification configuration."""
    
    enabled: bool = Field(
        default=False,
        description="Enable Telegram notifications"
    )
    bot_token: str = Field(
        default="",
        description="Telegram bot token (will be masked)"
    )
    chat_ids: List[str] = Field(
        default_factory=list,
        description="List of chat IDs to send notifications"
    )
    rate_limit_seconds: int = Field(
        default=5,
        ge=0,
        description="Minimum time between messages"
    )
    send_images: bool = Field(
        default=True,
        description="Send collage images with notifications"
    )
    video_speed: int = Field(
        default=2,
        ge=1,
        description="Video acceleration factor (2 = 10s from 20s clip)"
    )
    cooldown_seconds: int = Field(
        default=5,
        ge=0,
        description="Cooldown between notifications"
    )
    max_messages_per_min: int = Field(
        default=20,
        ge=1,
        description="Maximum messages per minute (rate limit)"
    )
    snapshot_quality: int = Field(
        default=85,
        ge=0,
        le=100,
        description="JPEG quality for snapshots (0-100)"
    )

    @field_validator("bot_token")
    @classmethod
    def validate_bot_token(cls, value: str) -> str:
        """Validate Telegram bot token format."""
        if not value or value == "***REDACTED***":
            return value
        if not re.match(r"^\d+:[A-Za-z0-9_-]{20,}$", value):
            raise ValueError("bot_token has invalid format")
        return value

    @field_validator("chat_ids")
    @classmethod
    def validate_chat_ids(cls, value: List[str]) -> List[str]:
        """Validate Telegram chat ID list."""
        for chat_id in value:
            if not isinstance(chat_id, str) or not re.match(r"^-?\d+$", chat_id):
                raise ValueError("chat_ids must be numeric strings")
        return value


class AppearanceConfig(BaseModel):
    """Appearance configuration (theme and language)."""
    
    theme: Literal["slate", "carbon", "pure-black", "matrix"] = Field(
        default="pure-black",
        description="UI theme"
    )
    language: Literal["tr", "en"] = Field(
        default="tr",
        description="Interface language"
    )


class PerformanceConfig(BaseModel):
    """Performance and optimization configuration."""
    
    worker_mode: Literal["threading", "multiprocessing"] = Field(
        default="threading",
        description="Worker mode: threading (stable) or multiprocessing (experimental, no GIL)"
    )
    enable_metrics: bool = Field(
        default=False,
        description="Enable Prometheus metrics export"
    )
    metrics_port: int = Field(
        default=9090,
        ge=1024,
        le=65535,
        description="Prometheus metrics HTTP port"
    )


class MqttConfig(BaseModel):
    """MQTT / Home Assistant integration configuration."""
    
    enabled: bool = Field(
        default=False,
        description="Enable MQTT integration"
    )
    host: str = Field(
        default="core-mosquitto",
        description="MQTT broker host"
    )
    port: int = Field(
        default=1883,
        description="MQTT broker port"
    )
    username: Optional[str] = Field(
        default=None,
        description="MQTT username (optional for anonymous)"
    )
    password: Optional[str] = Field(
        default=None,
        description="MQTT password (will be masked)"
    )
    topic_prefix: str = Field(
        default="thermal_vision",
        description="MQTT topic prefix"
    )


class AppConfig(BaseModel):
    """Main application configuration containing all sections."""
    
    detection: DetectionConfig = Field(
        default_factory=DetectionConfig,
        description="YOLOv8 detection configuration"
    )
    motion: MotionConfig = Field(
        default_factory=MotionConfig,
        description="Motion detection configuration"
    )
    thermal: ThermalConfig = Field(
        default_factory=ThermalConfig,
        description="Thermal image enhancement configuration"
    )
    stream: StreamConfig = Field(
        default_factory=StreamConfig,
        description="RTSP stream configuration"
    )
    live: LiveConfig = Field(
        default_factory=LiveConfig,
        description="Live view output configuration"
    )
    record: RecordConfig = Field(
        default_factory=RecordConfig,
        description="Recording configuration"
    )
    event: EventConfig = Field(
        default_factory=EventConfig,
        description="Event generation configuration"
    )
    media: MediaConfig = Field(
        default_factory=MediaConfig,
        description="Media cleanup configuration"
    )
    ai: AIConfig = Field(
        default_factory=AIConfig,
        description="AI integration configuration"
    )
    telegram: TelegramConfig = Field(
        default_factory=TelegramConfig,
        description="Telegram notification configuration"
    )
    performance: PerformanceConfig = Field(
        default_factory=PerformanceConfig,
        description="Performance and optimization configuration"
    )
    mqtt: MqttConfig = Field(
        default_factory=MqttConfig,
        description="MQTT / Home Assistant integration configuration"
    )
    appearance: AppearanceConfig = Field(
        default_factory=AppearanceConfig,
        description="Appearance configuration (theme and language)"
    )
