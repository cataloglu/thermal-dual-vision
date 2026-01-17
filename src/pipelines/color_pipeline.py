"""Color camera pipeline skeleton."""

from src.config import Config
from src.logger import get_logger
from src.pipelines.base import BasePipeline

logger = get_logger("pipeline.color")


class ColorPipeline(BasePipeline):
    """Pipeline for color camera processing."""

    camera_type = "color"

    def __init__(self, config: Config) -> None:
        super().__init__(config)

    def run(self) -> None:
        logger.info("Color pipeline started (skeleton).")
        # TODO: implement color camera processing loop
