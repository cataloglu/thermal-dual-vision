"""Application entry point for pipeline selection."""

import os
import threading
from typing import Callable, Optional

from src.config_store import load_effective_config
from src.health_server import EventStore, PipelineStatusTracker, run_health_server
from src.logger import get_logger, setup_logger
from src.pipelines.base import BasePipeline
from src.pipelines.color_pipeline import ColorPipeline
from src.pipelines.dual_pipeline import DualPipeline
from src.pipelines.thermal_pipeline import ThermalPipeline

PIPELINE_CLASSES = (ThermalPipeline, ColorPipeline, DualPipeline)


class PipelineController:
    """Control pipeline lifecycle for API handlers."""

    def __init__(
        self,
        pipeline_factory: Callable[[], BasePipeline],
        pipeline_status: PipelineStatusTracker,
        logger,
    ) -> None:
        self._pipeline_factory = pipeline_factory
        self._pipeline_status = pipeline_status
        self._logger = logger
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._pipeline: Optional[BasePipeline] = None

    def start(self) -> bool:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False
            self._pipeline = self._pipeline_factory()
            self._thread = threading.Thread(target=self._run_pipeline, daemon=True)
            self._thread.start()
            return True

    def stop(self) -> bool:
        with self._lock:
            if not self._pipeline or not self._thread or not self._thread.is_alive():
                return False
            self._pipeline.stop()
            return True

    def restart(self) -> None:
        self.stop()
        self.start()

    def _run_pipeline(self) -> None:
        if not self._pipeline:
            return
        self._logger.info("Starting %s pipeline", self._pipeline.camera_type)
        self._pipeline_status.set_status("running")
        try:
            self._pipeline.run()
            if self._pipeline.stop_event.is_set():
                self._pipeline_status.set_status("idle", "Pipeline stopped")
            else:
                self._pipeline_status.set_status("stopped", "Pipeline exited")
        except Exception as exc:
            self._pipeline_status.set_status("error", str(exc))
            raise


def main() -> None:
    """Run the pipeline based on camera type."""
    config = load_effective_config(os.environ)
    setup_logger(level=config.log_level)
    logger = get_logger("main")

    errors = config.validate()
    if errors:
        for error in errors:
            logger.error("Config error: %s", error)
        raise SystemExit(1)

    event_store = EventStore()
    pipeline_status = PipelineStatusTracker(event_store=event_store)

    camera_type = config.camera.camera_type
    pipeline: BasePipeline = ColorPipeline(config)
    for pipeline_cls in PIPELINE_CLASSES:
        if pipeline_cls.supports(camera_type):
            pipeline = pipeline_cls(config)
            break

    controller = PipelineController(lambda: pipeline.__class__(config), pipeline_status, logger)
    controller.start()

    host = os.getenv("HOST") or config.general.bind_host
    port = int(os.getenv("PORT") or config.general.http_port)

    run_health_server(
        config=config,
        event_store=event_store,
        pipeline_status=pipeline_status,
        pipeline_controller=controller,
        host=host,
        port=port,
    )


if __name__ == "__main__":
    main()


