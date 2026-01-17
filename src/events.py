"""Shared event schema for pipelines and notifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Protocol
from uuid import uuid4


class EventType(str, Enum):
    """Supported event types."""

    MOTION = "motion"
    ANALYSIS = "analysis"
    ALERT = "alert"
    HEALTH = "health"
    READY = "ready"


@dataclass
class BaseEvent:
    """Base event contract for pipeline and notification layers."""

    event_id: str
    event_type: EventType
    timestamp: datetime
    source: str
    camera_id: Optional[str]
    payload: Dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0"

    def as_dict(self) -> Dict[str, Any]:
        """Serialize event into a JSON-friendly dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "camera_id": self.camera_id,
            "payload": self.payload,
            "schema_version": self.schema_version,
        }


def new_event(
    event_type: EventType,
    source: str,
    camera_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    timestamp: Optional[datetime] = None,
    schema_version: str = "1.0",
) -> BaseEvent:
    """Create a new BaseEvent with generated id and timestamp."""
    return BaseEvent(
        event_id=str(uuid4()),
        event_type=event_type,
        timestamp=timestamp or datetime.now(timezone.utc),
        source=source,
        camera_id=camera_id,
        payload=payload or {},
        schema_version=schema_version,
    )


class EventPublisher(Protocol):
    """Protocol for publishing events to downstream systems."""

    def publish(self, event: BaseEvent) -> None:
        """Publish an event to a sink."""
        ...  # pragma: no cover


class EventConsumer(Protocol):
    """Protocol for handling events from pipelines."""

    def handle(self, event: BaseEvent) -> None:
        """Handle an incoming event."""
        ...  # pragma: no cover
