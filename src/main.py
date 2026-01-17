"""Application entry point for pipeline selection."""

from src.config import Config
from src.logger import get_logger, setup_logger
from src.pipelines.base import BasePipeline
from src.pipelines.color_pipeline import ColorPipeline
from src.pipelines.thermal_pipeline import ThermalPipeline

PIPELINE_CLASSES = (ThermalPipeline, ColorPipeline)


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

    camera_type = config.camera.camera_type
    pipeline: BasePipeline = ColorPipeline(config)
    for pipeline_cls in PIPELINE_CLASSES:
        if pipeline_cls.supports(camera_type):
            pipeline = pipeline_cls(config)
            break

    logger.info("Starting %s pipeline", pipeline.camera_type or camera_type)
    pipeline.run()


if __name__ == "__main__":
    main()
