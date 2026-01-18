"""Thermal camera pipeline skeleton."""

from src.config import Config
from src.logger import get_logger
from src.pipelines.base import BasePipeline

logger = get_logger("pipeline.thermal")


class ThermalPipeline(BasePipeline):
    """Pipeline for thermal camera processing."""

    camera_type = "thermal"

    def __init__(self, config: Config) -> None:
        super().__init__(config)

    def run(self) -> None:
        logger.info("Thermal pipeline started (skeleton).")
        # TODO: implement thermal camera processing loop
