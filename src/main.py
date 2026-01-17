"""Application entry point for pipeline selection."""

import threading

from src.config import Config
from src.health_server import EventStore, PipelineStatusTracker, run_health_server
from src.logger import get_logger, setup_logger
from src.pipelines.base import BasePipeline
from src.pipelines.color_pipeline import ColorPipeline
from src.pipelines.dual_pipeline import DualPipeline
from src.pipelines.thermal_pipeline import ThermalPipeline

PIPELINE_CLASSES = (ThermalPipeline, ColorPipeline, DualPipeline)


def main() -> None:
    """Run the pipeline based on camera type."""
    config = Config.from_env()
    setup_logger(level=config.log_level)
    logger = get_logger("main")

    errors = config.validate()
    if errors:
        for error in errors:
            logger.error("Config error: %s", error)
        raise SystemExit(1)

    event_store = EventStore()
    pipeline_status = PipelineStatusTracker(event_store=event_store)
    server_thread = threading.Thread(
        target=run_health_server,
        kwargs={
            "config": config,
            "event_store": event_store,
            "pipeline_status": pipeline_status,
        },
        daemon=True,
    )
    server_thread.start()

    camera_type = config.camera.camera_type
    pipeline: BasePipeline = ColorPipeline(config)
    for pipeline_cls in PIPELINE_CLASSES:
        if pipeline_cls.supports(camera_type):
            pipeline = pipeline_cls(config)
            break

    logger.info("Starting %s pipeline", pipeline.camera_type or camera_type)
    pipeline_status.set_status("running")

    try:
        pipeline.run()
        pipeline_status.set_status("stopped", "Pipeline exited")
    except Exception as exc:
        pipeline_status.set_status("error", str(exc))
        raise


if __name__ == "__main__":
    main()
