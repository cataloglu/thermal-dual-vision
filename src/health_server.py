"""Health and readiness HTTP endpoints."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import cv2
from aiohttp import web

from src.config import Config
from src.logger import get_logger
from src.mqtt_client import MQTTClient
from src.telegram_bot import TELEGRAM_AVAILABLE, TelegramBot

logger = get_logger("health")


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


class CameraStatusChecker:
    """Probe camera availability with a short-lived capture."""

    def __init__(self, config: Config, cache_seconds: float = 2.0) -> None:
        self.config = config
        self.cache_seconds = cache_seconds
        self._last_check = 0.0
        self._last_status = ComponentStatus(status="unknown", detail="Not checked")

    def check(self) -> ComponentStatus:
        if not self.config.camera.url:
            return ComponentStatus(status="missing", detail="Camera URL not set")

        now = time.time()
        if now - self._last_check < self.cache_seconds:
            return self._last_status

        self._last_check = now

        capture = cv2.VideoCapture(self.config.camera.url)
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
    ) -> None:
        self.config = config
        self.mqtt_client = mqtt_client
        self.telegram_bot = telegram_bot
        self.camera_checker = camera_checker or CameraStatusChecker(config)

    def _mqtt_status(self) -> ComponentStatus:
        if self.mqtt_client is None:
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

        return {
            "status": overall,
            "timestamp": time.time(),
            "components": {key: value.as_dict() for key, value in components.items()},
        }

    def is_ready(self) -> bool:
        report = self.build_report()
        components = report["components"]

        camera_ok = components["camera"]["status"] == "ok"
        telegram_ok = components["telegram"]["status"] in {"ok", "disabled"}
        mqtt_ok = components["mqtt"]["status"] == "ok"

        return camera_ok and telegram_ok and mqtt_ok


def create_app(
    config: Config,
    mqtt_client: Optional[MQTTClient] = None,
    telegram_bot: Optional[TelegramBot] = None,
) -> web.Application:
    """Create aiohttp app with health endpoints."""
    reporter = HealthReporter(config, mqtt_client, telegram_bot)

    async def health_handler(_: web.Request) -> web.Response:
        return web.json_response(reporter.build_report())

    async def ready_handler(_: web.Request) -> web.Response:
        payload = reporter.build_report()
        payload["ready"] = reporter.is_ready()
        status = 200 if payload["ready"] else 503
        return web.json_response(payload, status=status)

    app = web.Application()
    app.router.add_get("/api/health", health_handler)
    app.router.add_get("/ready", ready_handler)
    return app


def run_health_server(
    config: Config,
    mqtt_client: Optional[MQTTClient] = None,
    telegram_bot: Optional[TelegramBot] = None,
    host: str = "0.0.0.0",
    port: int = 8099,
) -> None:
    """Run the health server."""
    app = create_app(config, mqtt_client, telegram_bot)
    logger.info("Starting health server on %s:%s", host, port)
    web.run_app(app, host=host, port=port)
