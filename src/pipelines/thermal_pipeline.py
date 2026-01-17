"""Thermal camera pipeline skeleton with passthrough frames."""

from __future__ import annotations

import time
from typing import Optional

import cv2
import numpy as np

from src.config import Config
from src.logger import get_logger

logger = get_logger("pipeline.thermal")


class ThermalPipeline:
    """Thermal pipeline that reads frames and passes them through."""

    def __init__(self, config: Config, max_frames: Optional[int] = None) -> None:
        self.config = config
        self.max_frames = max_frames
        self._capture: Optional[cv2.VideoCapture] = None

    def _ensure_capture(self) -> cv2.VideoCapture:
        if self._capture is None:
            self._capture = cv2.VideoCapture(self.config.camera.url)
        return self._capture

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Passthrough frame processing placeholder."""
        return frame

    def run(self) -> None:
        """Read frames from thermal camera and passthrough."""
        capture = self._ensure_capture()
        if not capture.isOpened():
            raise RuntimeError("Failed to open thermal camera stream")

        frame_count = 0
        try:
            while True:
                if self.max_frames is not None and frame_count >= self.max_frames:
                    break

                ok, frame = capture.read()
                if not ok:
                    logger.warning("Failed to read thermal frame")
                    break

                _ = self.process_frame(frame)
                frame_count += 1

                if self.config.camera.fps > 0:
                    time.sleep(1 / self.config.camera.fps)
        finally:
            capture.release()
