"""Thermal camera pipeline skeleton."""

import time

import cv2

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
        url = self.config.camera.url
        if url.startswith("dummy://"):
            logger.info("Dummy camera URL detected, keeping pipeline alive.")
            while True:
                time.sleep(1)

        while True:
            capture = cv2.VideoCapture(url)
            if not capture.isOpened():
                logger.warning("Failed to open thermal stream, retrying...")
                capture.release()
                time.sleep(2)
                continue

            try:
                while True:
                    ok, _frame = capture.read()
                    if not ok:
                        logger.warning("Failed to read thermal frame, reconnecting...")
                        break
                    if self.config.camera.fps > 0:
                        time.sleep(1 / self.config.camera.fps)
            finally:
                capture.release()
