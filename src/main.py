"""Application entry point for pipeline selection."""

import os
import threading

from src.config_store import load_effective_config
from src.health_server import EventStore, PipelineStatusTracker, run_health_server
from src.logger import get_logger, setup_logger
from src.pipelines.base import BasePipeline
from src.pipelines.color_pipeline import ColorPipeline
from src.pipelines.dual_pipeline import DualPipeline
from src.pipelines.thermal_pipeline import ThermalPipeline

PIPELINE_CLASSES = (ThermalPipeline, ColorPipeline, DualPipeline)


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

    def _run_pipeline() -> None:
        logger.info("Starting %s pipeline", pipeline.camera_type or camera_type)
        pipeline_status.set_status("running")
        try:
            pipeline.run()
            pipeline_status.set_status("stopped", "Pipeline exited")
        except Exception as exc:
            pipeline_status.set_status("error", str(exc))
            raise

    pipeline_thread = threading.Thread(target=_run_pipeline, daemon=True)
    pipeline_thread.start()

    host = config_store_env("HOST", "0.0.0.0")
    port = int(config_store_env("PORT", "8000"))

    run_health_server(
        config=config,
        event_store=event_store,
        pipeline_status=pipeline_status,
        host=host,
        port=port,
    )


if __name__ == "__main__":
    main()


def config_store_env(key: str, default: str) -> str:
    value = os.getenv(key)
    if value is None or value == "":
        return default
    return value
