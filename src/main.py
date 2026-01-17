"""Application entry point for Smart Motion Detector."""

from __future__ import annotations

import asyncio
import os
import signal
from typing import Optional

from aiohttp import web
from dotenv import load_dotenv

from src.config import Config
from src.logger import get_logger, setup_logger
from src.mqtt_client import MQTTClient
from src.telegram_bot import TelegramBot
from src.rtsp_camera import RTSPCamera
from src.web_ui import WebUI
from src.utils import mask_url


async def _start_web_server(
    host: str, 
    port: int, 
    web_ui: WebUI
) -> web.AppRunner:
    """
    Start web server with UI and API endpoints.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        web_ui: WebUI instance with routes
    
    Returns:
        AppRunner instance
    """
    app = web_ui.create_app()
    
    # Note: Health endpoints are already defined in WebUI.create_app()
    # Adding /ready endpoint for compatibility with orchestration tools
    async def ready(_: web.Request) -> web.Response:
        return web.json_response({"status": "ready"})

    app.router.add_get("/ready", ready)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    return runner


async def _stop_health_server(runner: Optional[web.AppRunner]) -> None:
    """Stop web server."""
    if runner is not None:
        await runner.cleanup()


async def _run() -> int:
    load_dotenv()

    config = Config.from_env()
    setup_logger(name="smart_motion", level=config.log_level)
    logger = get_logger("main")

    errors = config.validate()
    if errors:
        for err in errors:
            logger.error("Config error: %s", err)
        return 1

    # Initialize RTSP camera (or dummy if no URL)
    camera: Optional[RTSPCamera] = None
    camera = RTSPCamera(config.camera)
    try:
        await camera.connect()
        if config.camera.url:
            masked_url = mask_url(config.camera.url)
            logger.info("RTSP camera connected: %s", masked_url)
        else:
            logger.info("Dummy test camera started (no RTSP URL configured)")
    except RuntimeError as exc:
        # RuntimeError is raised by RTSPCamera for connection failures
        masked_url = mask_url(config.camera.url) if config.camera.url else "dummy"
        logger.error("Failed to connect camera (%s): %s", masked_url, exc)
        camera = None
    except (OSError, IOError) as exc:
        # Network/file system errors
        masked_url = mask_url(config.camera.url) if config.camera.url else "dummy"
        logger.error("I/O error connecting camera (%s): %s", masked_url, exc)
        camera = None
    except Exception as exc:
        # Unexpected errors
        masked_url = mask_url(config.camera.url) if config.camera.url else "dummy"
        logger.error("Unexpected error connecting camera (%s): %s", masked_url, exc, exc_info=True)
        camera = None

    # Create web UI with camera callback
    def get_camera_frame():
        """Get current camera frame for web UI."""
        if camera:
            return camera.get_frame()
        return None

    web_ui = WebUI(camera_callback=get_camera_frame)

    # Start web server on ingress port (Home Assistant requirement)
    ingress_host = os.getenv("SUPERVISOR_INGRESS_HOST", "0.0.0.0")
    ingress_port = int(os.getenv("SUPERVISOR_INGRESS_PORT", "8099"))
    health_host = os.getenv("HEALTH_HOST", ingress_host)
    health_port = int(os.getenv("HEALTH_PORT", str(ingress_port)))
    
    web_runner = await _start_web_server(health_host, health_port, web_ui)
    logger.info("Web server started on %s:%s (Ingress: %s:%s)", 
                health_host, health_port, ingress_host, ingress_port)

    mqtt_client: Optional[MQTTClient] = None
    if config.mqtt.enabled:
        mqtt_client = MQTTClient(config.mqtt)
        try:
            await mqtt_client.connect()
            await mqtt_client.publish_discovery()
        except RuntimeError as exc:
            # RuntimeError is raised by MQTTClient for connection/configuration failures
            logger.warning("MQTT connection failed: %s", exc)
        except (ConnectionError, OSError, TimeoutError) as exc:
            # Network errors
            logger.warning("MQTT network error: %s", exc)
        except Exception as exc:
            # Unexpected errors
            logger.warning("MQTT init failed: %s", exc, exc_info=True)

    telegram_bot: Optional[TelegramBot] = None
    if config.telegram.enabled:
        telegram_bot = TelegramBot(config.telegram)
        try:
            await telegram_bot.start()
        except RuntimeError as exc:
            # RuntimeError is raised by TelegramBot for configuration failures
            logger.warning("Telegram bot configuration error: %s", exc)
        except (ConnectionError, OSError, TimeoutError) as exc:
            # Network errors
            logger.warning("Telegram bot network error: %s", exc)
        except Exception as exc:
            # Unexpected errors
            logger.warning("Telegram bot failed to start: %s", exc, exc_info=True)

    logger.info(
        "Smart Motion Detector initialized. RTSP input enabled. Motion pipeline to be implemented."
    )

    stop_event = asyncio.Event()

    def _request_stop() -> None:
        stop_event.set()

    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _request_stop)
            except NotImplementedError:
                signal.signal(sig, lambda *_: _request_stop())
    except RuntimeError:
        pass

    await stop_event.wait()

    # Cleanup resources
    if camera:
        await camera.disconnect()
    if telegram_bot:
        await telegram_bot.stop()
    if mqtt_client:
        await mqtt_client.disconnect()
    await _stop_health_server(web_runner)

    return 0


def main() -> None:
    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
