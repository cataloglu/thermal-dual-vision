"""
SQLAlchemy database models for Smart Motion Detector v2.

This module contains all database models including Camera, Zone, and Event.
"""
import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class CameraType(enum.Enum):
    """Camera type enumeration."""
    COLOR = "color"
    THERMAL = "thermal"
    DUAL = "dual"


class CameraStatus(enum.Enum):
    """Camera status enumeration."""
    CONNECTED = "connected"
    RETRYING = "retrying"
    DOWN = "down"
    INITIALIZING = "initializing"


class DetectionSource(enum.Enum):
    """Detection source enumeration."""
    COLOR = "color"
    THERMAL = "thermal"
    AUTO = "auto"


class ZoneMode(enum.Enum):
    """Zone mode enumeration."""
    MOTION = "motion"
    PERSON = "person"
    BOTH = "both"


class Camera(Base):
    """
    Camera model representing a camera device.
    
    Stores camera configuration, connection details, and status.
    """
    __tablename__ = "cameras"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic info
    name = Column(String(100), nullable=False)
    type = Column(Enum(CameraType), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    
    # RTSP URLs (will be masked in responses)
    rtsp_url = Column(String(500), nullable=True)  # Legacy field
    rtsp_url_color = Column(String(500), nullable=True)
    rtsp_url_thermal = Column(String(500), nullable=True)
    
    # Channel numbers
    channel_color = Column(Integer, nullable=True)
    channel_thermal = Column(Integer, nullable=True)
    
    # Detection settings
    detection_source = Column(Enum(DetectionSource), default=DetectionSource.AUTO, nullable=False)
    stream_roles = Column(JSON, default=list, nullable=False)  # ["detect", "live", "record"]
    
    # Status
    status = Column(Enum(CameraStatus), default=CameraStatus.INITIALIZING, nullable=False)
    last_frame_ts = Column(DateTime, nullable=True)
    
    # Motion configuration (JSON)
    motion_config = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    zones = relationship("Zone", back_populates="camera", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="camera", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_camera_enabled", "enabled"),
        Index("idx_camera_status", "status"),
    )


class Zone(Base):
    """
    Zone model representing a detection zone within a camera view.
    
    Zones define polygonal areas for motion or person detection filtering.
    """
    __tablename__ = "zones"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key
    camera_id = Column(String(36), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    
    # Zone info
    name = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    mode = Column(Enum(ZoneMode), default=ZoneMode.PERSON, nullable=False)
    
    # Polygon coordinates (normalized 0.0-1.0)
    # Format: [[x1, y1], [x2, y2], ...]
    polygon = Column(JSON, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    camera = relationship("Camera", back_populates="zones")
    
    # Indexes
    __table_args__ = (
        Index("idx_zone_camera_id", "camera_id"),
        Index("idx_zone_enabled", "enabled"),
    )


class Event(Base):
    """
    Event model representing a detection event.
    
    Stores event metadata, confidence, media URLs, and AI summary.
    """
    __tablename__ = "events"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key
    camera_id = Column(String(36), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    
    # Event info
    timestamp = Column(DateTime, nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    event_type = Column(String(50), default="person", nullable=False)
    
    # AI summary (optional)
    summary = Column(Text, nullable=True)
    ai_enabled = Column(Boolean, default=False, nullable=False)
    ai_reason = Column(String(100), nullable=True)
    
    # Media URLs
    collage_url = Column(String(500), nullable=True)
    gif_url = Column(String(500), nullable=True)
    mp4_url = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    camera = relationship("Camera", back_populates="events")
    
    # Indexes
    __table_args__ = (
        Index("idx_event_timestamp", "timestamp"),
        Index("idx_event_camera_id", "camera_id"),
        Index("idx_event_confidence", "confidence"),
        Index("idx_event_camera_timestamp", "camera_id", "timestamp"),
    )
