"""Health metrics HTTP endpoint for Smart Motion Detector."""

import asyncio
from typing import Optional

from aiohttp import web

from src.logger import get_logger
from src.metrics import MetricsCollector

# Initialize logger
logger = get_logger("health_endpoint")


class HealthEndpoint:
    """HTTP server exposing health and metrics endpoints."""

    def __init__(
        self,
        metrics_collector: MetricsCollector,
        host: str = "0.0.0.0",
        port: int = 8099
    ) -> None:
        """
        Initialize health endpoint server.

        Args:
            metrics_collector: MetricsCollector instance to expose metrics from
            host: Host to bind the server to (default: 0.0.0.0)
            port: Port to bind the server to (default: 8099)
        """
        self.metrics_collector = metrics_collector
        self.host = host
        self.port = port
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None

        logger.info(f"HealthEndpoint initialized on {host}:{port}")

    async def health_handler(self, request: web.Request) -> web.Response:
        """
        Handle /health endpoint requests.

        Args:
            request: HTTP request

        Returns:
            JSON response with basic health status
        """
        health_data = {
            "status": "healthy",
            "uptime_seconds": self.metrics_collector.get_uptime_seconds()
        }
        return web.json_response(health_data)

    async def metrics_handler(self, request: web.Request) -> web.Response:
        """
        Handle /metrics endpoint requests.

        Args:
            request: HTTP request

        Returns:
            JSON response with current performance metrics
        """
        metrics = self.metrics_collector.collect()
        metrics_data = {
            "fps": metrics.fps,
            "memory_mb": metrics.memory_mb,
            "cpu_percent": metrics.cpu_percent,
            "inference_ms": metrics.inference_ms,
            "queue_size": metrics.queue_size,
            "uptime_seconds": metrics.uptime_seconds,
            "timestamp": metrics.timestamp
        }
        return web.json_response(metrics_data)

    async def start(self) -> None:
        """Start the HTTP server."""
        try:
            # Create application and add routes
            self.app = web.Application()
            self.app.router.add_get("/health", self.health_handler)
            self.app.router.add_get("/metrics", self.metrics_handler)

            # Setup runner
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            # Create and start site
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()

            logger.info(f"Health endpoint server started on http://{self.host}:{self.port}")
            logger.info(f"  - Health check: http://{self.host}:{self.port}/health")
            logger.info(f"  - Metrics: http://{self.host}:{self.port}/metrics")

        except Exception as e:
            logger.error(f"Failed to start health endpoint server: {e}")
            raise

    async def stop(self) -> None:
        """Stop the HTTP server."""
        try:
            if self.runner:
                await self.runner.cleanup()
                logger.info("Health endpoint server stopped")
        except Exception as e:
            logger.error(f"Error stopping health endpoint server: {e}")

    async def run_forever(self) -> None:
        """
        Start the server and run forever.

        This is a convenience method for running the server standalone.
        """
        await self.start()
        try:
            # Keep running until interrupted
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour intervals
        except asyncio.CancelledError:
            logger.info("Health endpoint server cancelled")
        finally:
            await self.stop()
