"""Dual RTSP pipeline for thermal + color streams."""

from __future__ import annotations

import threading
import time
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from src.config import Config
from src.logger import get_logger
from src.pipelines.base import BasePipeline

logger = get_logger("pipeline.dual")


class DualPipeline(BasePipeline):
    """Pipeline that reads thermal and color streams in parallel."""

    camera_type = "dual"
    soft_tolerance_ms = 150
    hard_tolerance_ms = 500

    def __init__(self, config: Config, max_pairs: Optional[int] = None) -> None:
        super().__init__(config)
        self.max_pairs = max_pairs
        self._lock = threading.Lock()
        self._latest_frames: Dict[str, Optional[np.ndarray]] = {"color": None, "thermal": None}
        self._latest_ts: Dict[str, Optional[float]] = {"color": None, "thermal": None}
        self._threads: Dict[str, threading.Thread] = {}
        self._last_pair: Optional[Tuple[float, float]] = None

    def _capture_loop(self, label: str, url: str) -> None:
        capture = cv2.VideoCapture(url)
        if not capture.isOpened():
            logger.error("Failed to open %s stream", label)
            return

        try:
            while not self.stop_event.is_set():
                ok, frame = capture.read()
                if not ok:
                    logger.warning("Failed to read %s frame", label)
                    time.sleep(0.1)
                    continue

                ts = time.time() * 1000
                with self._lock:
                    self._latest_frames[label] = frame
                    self._latest_ts[label] = ts
        finally:
            capture.release()

    def _start_capture_threads(self) -> None:
        color_url = self.config.camera.color_url or self.config.camera.url
        thermal_url = self.config.camera.thermal_url or self.config.camera.url

        self._threads["color"] = threading.Thread(
            target=self._capture_loop, args=("color", color_url), daemon=True
        )
        self._threads["thermal"] = threading.Thread(
            target=self._capture_loop, args=("thermal", thermal_url), daemon=True
        )

        for thread in self._threads.values():
            thread.start()

    def _get_pair(self) -> Optional[Tuple[float, float]]:
        with self._lock:
            color_ts = self._latest_ts["color"]
            thermal_ts = self._latest_ts["thermal"]

        if color_ts is None or thermal_ts is None:
            return None
        return (color_ts, thermal_ts)

    def run(self) -> None:
        """Run dual stream capture and emit combined MVP output."""
        self._start_capture_threads()
        pair_count = 0

        try:
            while not self.stop_event.is_set():
                if self.max_pairs is not None and pair_count >= self.max_pairs:
                    break

                pair = self._get_pair()
                if pair is None or pair == self._last_pair:
                    time.sleep(0.05)
                    continue

                self._last_pair = pair
                pair_count += 1
                delta_ms = abs(pair[0] - pair[1])

                status = "ok"
                if delta_ms > self.hard_tolerance_ms:
                    status = "unmatched"
                elif delta_ms > self.soft_tolerance_ms:
                    status = "degraded"

                logger.info(
                    "Dual stream sync pair=%s delta_ms=%.1f status=%s",
                    pair_count,
                    delta_ms,
                    status,
                )

                if self.config.camera.fps > 0:
                    time.sleep(1 / self.config.camera.fps)
        finally:
            self.stop_event.set()
