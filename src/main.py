"""Application entry point for pipeline selection."""

from src.config import Config
from src.logger import get_logger, setup_logger
from src.pipelines.color_pipeline import ColorPipeline
from src.pipelines.thermal_pipeline import ThermalPipeline


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
    if camera_type == "thermal":
        pipeline = ThermalPipeline(config)
    else:
        pipeline = ColorPipeline(config)

    logger.info("Starting %s pipeline", camera_type)
    pipeline.run()


if __name__ == "__main__":
    main()
