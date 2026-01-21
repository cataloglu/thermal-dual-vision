"""
Configuration models for Smart Motion Detector v2.

This module contains Pydantic models for all configuration sections.
All models include validation rules and default values.
"""
import re
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class DetectionConfig(BaseModel):
    """YOLOv8 person detection configuration."""
    
    model: Literal["yolov8n-person", "yolov8s-person", "yolov9t", "yolov9s"] = Field(
        default="yolov8n-person",
        description="Primary model selection: yolov8n (fast), yolov8s (accurate), yolov9t (thermal), yolov9s (best)"
    )
    confidence_threshold: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for detections"
    )
    nms_iou_threshold: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description="Non-Maximum Suppression IoU threshold"
    )
    inference_resolution: List[int] = Field(
        default=[640, 640],
        description="Inference resolution [width, height]"
    )
    inference_fps: int = Field(
        default=5,
        ge=1,
        le=30,
        description="Frames per second for inference"
    )
    aspect_ratio_min: float = Field(
        default=0.2,
        ge=0.0,
        le=5.0,
        description="Minimum person aspect ratio (width/height)"
    )
    aspect_ratio_max: float = Field(
        default=1.2,
        ge=0.0,
        le=5.0,
        description="Maximum person aspect ratio (width/height)"
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


class MotionPreset(BaseModel):
    """Motion detection preset configuration."""
    
    sensitivity: int = Field(ge=1, le=10)
    min_area: int = Field(ge=0)
    cooldown_seconds: int = Field(ge=0)


class MotionConfig(BaseModel):
    """Motion detection configuration (pre-filter for person detection)."""
    
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
            )
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
        default=[8, 8],
        description="CLAHE tile grid size [width, height]"
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
    buffer_size: int = Field(
        default=1,
        ge=1,
        description="OpenCV VideoCapture buffer size"
    )
    reconnect_delay_seconds: int = Field(
        default=5,
        ge=1,
        description="Delay between reconnect attempts"
    )
    max_reconnect_attempts: int = Field(
        default=10,
        ge=1,
        description="Maximum reconnect attempts"
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
    webrtc: WebRTCConfig = Field(
        default_factory=WebRTCConfig,
        description="WebRTC configuration"
    )


class RecordConfig(BaseModel):
    """Recording and retention configuration."""
    
    enabled: bool = Field(
        default=False,
        description="Enable event-based recording"
    )
    retention_days: int = Field(
        default=7,
        ge=1,
        description="Days to keep recordings"
    )
    record_segments_seconds: int = Field(
        default=10,
        ge=1,
        description="Recording segment length in seconds"
    )
    disk_limit_percent: int = Field(
        default=80,
        ge=50,
        le=95,
        description="Maximum disk usage percentage"
    )
    cleanup_policy: Literal["oldest_first", "lowest_confidence"] = Field(
        default="oldest_first",
        description="Cleanup strategy"
    )
    delete_order: List[str] = Field(
        default=["mp4", "gif", "collage"],
        description="Media deletion priority order"
    )


class EventConfig(BaseModel):
    """Event generation configuration."""
    
    cooldown_seconds: int = Field(
        default=5,
        ge=0,
        description="Minimum time between events"
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
        description="Minimum event duration in seconds"
    )


class MediaConfig(BaseModel):
    """Media cleanup configuration."""
    
    retention_days: int = Field(
        default=7,
        ge=1,
        description="Days to keep media files"
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
    prompt_template: Literal["simple", "security_focused", "detailed", "custom"] = Field(
        default="security_focused",
        description="Prompt template selection"
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
        default=4,
        ge=1,
        description="Video acceleration factor"
    )
    event_types: List[str] = Field(
        default=["person"],
        description="Event types to send notifications for"
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
        default="slate",
        description="UI theme"
    )
    language: Literal["tr", "en"] = Field(
        default="tr",
        description="Interface language"
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
    appearance: AppearanceConfig = Field(
        default_factory=AppearanceConfig,
        description="Appearance configuration (theme and language)"
    )
