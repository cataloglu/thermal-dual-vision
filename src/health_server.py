"""Health, readiness, and minimal UI server."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

import cv2
from aiohttp import web

from src.config import Config
from src.events import EventType, new_event
from src.logger import get_logger
from src.mqtt_client import MQTTClient
from src.telegram_bot import TELEGRAM_AVAILABLE, TelegramBot

logger = get_logger("health")
UI_PATH = Path(__file__).with_name("web_ui.html")


@dataclass
class ComponentStatus:
    """Component status details."""

    status: str
    detail: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"status": self.status}
        if self.detail:
            payload["detail"] = self.detail
        return payload


@dataclass
class PipelineStatus:
    """Pipeline runtime status."""

    status: str
    detail: Optional[str]
    updated_at: float

    def as_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"status": self.status, "updated_at": self.updated_at}
        if self.detail:
            payload["detail"] = self.detail
        return payload


class EventStore:
    """In-memory ring buffer of recent events."""

    def __init__(self, max_events: int = 50) -> None:
        self._events: Deque[Dict[str, Any]] = deque(maxlen=max_events)

    def add_event(
        self,
        event_type: EventType,
        source: str,
        payload: Optional[Dict[str, Any]] = None,
        camera_id: Optional[str] = None,
    ) -> None:
        event = new_event(
            event_type=event_type,
            source=source,
            camera_id=camera_id,
            payload=payload,
        )
        self._events.appendleft(event.as_dict())

    def snapshot(self) -> List[Dict[str, Any]]:
        return list(self._events)


class PipelineStatusTracker:
    """Track pipeline status for UI and health reporting."""

    def __init__(self, event_store: Optional[EventStore] = None) -> None:
        self._event_store = event_store
        self._status = PipelineStatus(status="stopped", detail="Not started", updated_at=time.time())

    def set_status(self, status: str, detail: Optional[str] = None) -> None:
        if status == self._status.status and detail == self._status.detail:
            return
        self._status = PipelineStatus(status=status, detail=detail, updated_at=time.time())
        if self._event_store:
            self._event_store.add_event(
                event_type=EventType.HEALTH,
                source="pipeline",
                payload={"status": status, "detail": detail},
            )

    def as_dict(self) -> Dict[str, Any]:
        return self._status.as_dict()


class CameraStatusChecker:
    """Probe camera availability with a short-lived capture."""

    def __init__(self, config: Config, cache_seconds: float = 2.0) -> None:
        self.config = config
        self.cache_seconds = cache_seconds
        self._last_check = 0.0
        self._last_status = ComponentStatus(status="unknown", detail="Not checked")

    def check(self) -> ComponentStatus:
        if not self.config.camera.url and not self.config.camera.color_url and not self.config.camera.thermal_url:
            return ComponentStatus(status="missing", detail="Camera URL not set")

        now = time.time()
        if now - self._last_check < self.cache_seconds:
            return self._last_status

        self._last_check = now
        camera_url = self.config.camera.url or self.config.camera.color_url or self.config.camera.thermal_url
        if camera_url.startswith("dummy://"):
            self._last_status = ComponentStatus(status="ok", detail="Dummy camera")
            return self._last_status

        capture = cv2.VideoCapture(camera_url)
        try:
            if capture.isOpened():
                self._last_status = ComponentStatus(status="ok")
            else:
                self._last_status = ComponentStatus(
                    status="down", detail="Unable to open camera stream"
                )
        finally:
            capture.release()

        return self._last_status


class HealthReporter:
    """Build health and readiness payloads."""

    def __init__(
        self,
        config: Config,
        mqtt_client: Optional[MQTTClient] = None,
        telegram_bot: Optional[TelegramBot] = None,
        camera_checker: Optional[CameraStatusChecker] = None,
        event_store: Optional[EventStore] = None,
        pipeline_status: Optional[PipelineStatusTracker] = None,
    ) -> None:
        self.config = config
        self.mqtt_client = mqtt_client
        self.telegram_bot = telegram_bot
        self.camera_checker = camera_checker or CameraStatusChecker(config)
        self.event_store = event_store
        self.pipeline_status = pipeline_status
        self._last_health_status: Optional[str] = None
        self._last_ready_status: Optional[bool] = None

    def _mqtt_status(self) -> ComponentStatus:
        if self.mqtt_client is None:
            if not self.config.mqtt.discovery:
                return ComponentStatus(status="disabled", detail="MQTT discovery disabled")
            return ComponentStatus(status="unknown", detail="MQTT client not wired")
        return ComponentStatus(status="ok" if self.mqtt_client.is_connected else "down")

    def _telegram_status(self) -> ComponentStatus:
        if not self.config.telegram.enabled:
            return ComponentStatus(status="disabled")
        if not TELEGRAM_AVAILABLE:
            return ComponentStatus(status="missing", detail="python-telegram-bot not installed")
        if self.telegram_bot is None:
            return ComponentStatus(status="unknown", detail="Telegram bot not wired")
        return ComponentStatus(status="ok" if self.telegram_bot.is_running else "down")

    def _camera_status(self) -> ComponentStatus:
        return self.camera_checker.check()

    def _record_health_event(self, status: str) -> None:
        if not self.event_store or status == self._last_health_status:
            return
        self._last_health_status = status
        self.event_store.add_event(event_type=EventType.HEALTH, source="health")

    def _record_ready_event(self, ready: bool) -> None:
        if not self.event_store or ready == self._last_ready_status:
            return
        self._last_ready_status = ready
        self.event_store.add_event(event_type=EventType.READY, source="health", payload={"ready": ready})

    def build_report(self) -> Dict[str, Any]:
        components = {
            "camera": self._camera_status(),
            "mqtt": self._mqtt_status(),
            "telegram": self._telegram_status(),
        }

        overall = "ok"
        for status in components.values():
            if status.status in {"down", "missing"}:
                overall = "down"
                break
            if status.status == "unknown" and overall != "down":
                overall = "degraded"

        self._record_health_event(overall)

        return {
            "status": overall,
            "timestamp": time.time(),
            "components": {key: value.as_dict() for key, value in components.items()},
            "pipeline": self.pipeline_status.as_dict() if self.pipeline_status else {"status": "unknown"},
            "events": self.event_store.snapshot() if self.event_store else [],
        }

    def is_ready(self, report: Optional[Dict[str, Any]] = None) -> bool:
        payload = report or self.build_report()
        components = payload["components"]

        camera_ok = components["camera"]["status"] == "ok"
        telegram_ok = components["telegram"]["status"] in {"ok", "disabled"}
        mqtt_ok = components["mqtt"]["status"] in {"ok", "disabled"}

        return camera_ok and telegram_ok and mqtt_ok


def create_app(
    config: Config,
    mqtt_client: Optional[MQTTClient] = None,
    telegram_bot: Optional[TelegramBot] = None,
    event_store: Optional[EventStore] = None,
    pipeline_status: Optional[PipelineStatusTracker] = None,
) -> web.Application:
    """Create aiohttp app with health endpoints and UI."""
    reporter = HealthReporter(
        config,
        mqtt_client=mqtt_client,
        telegram_bot=telegram_bot,
        event_store=event_store,
        pipeline_status=pipeline_status,
    )

    async def health_handler(_: web.Request) -> web.Response:
        return web.json_response(reporter.build_report())

    async def ready_handler(_: web.Request) -> web.Response:
        payload = reporter.build_report()
        payload["ready"] = reporter.is_ready(payload)
        reporter._record_ready_event(payload["ready"])
        status = 200 if payload["ready"] else 503
        return web.json_response(payload, status=status)

    async def ui_handler(_: web.Request) -> web.Response:
        html = UI_PATH.read_text(encoding="utf-8")
        return web.Response(text=html, content_type="text/html")

    app = web.Application()
    app.router.add_get("/", ui_handler)
    app.router.add_get("/index.html", ui_handler)
    app.router.add_get("/api/health", health_handler)
    app.router.add_get("/ready", ready_handler)
    return app


def run_health_server(
    config: Config,
    mqtt_client: Optional[MQTTClient] = None,
    telegram_bot: Optional[TelegramBot] = None,
    event_store: Optional[EventStore] = None,
    pipeline_status: Optional[PipelineStatusTracker] = None,
    host: str = "0.0.0.0",
    port: int = 8099,
) -> None:
    """Run the health server."""
    app = create_app(
        config,
        mqtt_client=mqtt_client,
        telegram_bot=telegram_bot,
        event_store=event_store,
        pipeline_status=pipeline_status,
    )
    logger.info("Starting health server on %s:%s", host, port)
    web.run_app(app, host=host, port=port)
