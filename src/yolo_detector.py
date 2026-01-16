"""YOLO object detection module for Smart Motion Detector."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

from src.config import YoloConfig
from src.logger import get_logger

logger = get_logger("yolo")


@dataclass
class Detection:
    """Represents a single object detection result."""
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    class_id: int


class YoloDetector:
    """
    YOLOv8-based object detector with lazy model loading.

    The model is loaded on first detection call to optimize startup time.
    Supports confidence threshold and class-based filtering.
    """

    def __init__(self, config: YoloConfig):
        """
        Initialize YOLO detector with configuration.

        Args:
            config: YoloConfig instance with model settings
        """
        self.config = config
        self._model: Optional[object] = None
        self._class_names: Optional[List[str]] = None
        logger.info(
            f"YoloDetector initialized with model={config.model}, "
            f"confidence={config.confidence}, classes={config.classes}"
        )

    def _load_model(self) -> None:
        """
        Lazy load the YOLO model on first use.

        This method is called automatically on the first detect() call.
        Uses ultralytics YOLO implementation.
        """
        if self._model is not None:
            return

        try:
            from ultralytics import YOLO
            logger.info(f"Loading YOLO model: {self.config.model}")
            self._model = YOLO(self.config.model)

            # Store class names from model
            self._class_names = self._model.names

            logger.info(
                f"YOLO model loaded successfully. "
                f"Available classes: {len(self._class_names)}"
            )
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise

    def set_classes(self, classes: Optional[List[str]]) -> None:
        """
        Update the list of classes to detect dynamically.

        Args:
            classes: List of class names to detect, or None to detect all classes
        """
        self.config.classes = classes
        logger.info(f"Updated detection classes to: {classes}")

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect objects in the given frame.

        Args:
            frame: Input image as numpy array (BGR format)

        Returns:
            List of Detection objects containing detected objects

        Raises:
            Exception: If model loading or inference fails
        """
        # Ensure model is loaded
        self._load_model()

        try:
            # Run inference
            results = self._model(frame, verbose=False)

            detections = []

            # Process results
            if len(results) > 0:
                result = results[0]

                # Extract boxes, confidences, and class IDs
                if result.boxes is not None and len(result.boxes) > 0:
                    boxes = result.boxes.xyxy.cpu().numpy()  # x1, y1, x2, y2
                    confidences = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy().astype(int)

                    for box, conf, class_id in zip(boxes, confidences, class_ids):
                        # Filter by confidence threshold
                        if conf < self.config.confidence:
                            continue

                        # Get class name
                        class_name = self._class_names[class_id]

                        # Filter by allowed classes if specified
                        if self.config.classes and class_name not in self.config.classes:
                            continue

                        # Create Detection object
                        detection = Detection(
                            class_name=class_name,
                            confidence=float(conf),
                            bbox=(int(box[0]), int(box[1]), int(box[2]), int(box[3])),
                            class_id=class_id
                        )
                        detections.append(detection)

            logger.debug(f"Detected {len(detections)} objects in frame")
            return detections

        except Exception as e:
            logger.error(f"Detection failed: {e}")
            raise

    async def detect_async(self, frame: np.ndarray) -> List[Detection]:
        """
        Asynchronously detect objects in the given frame.

        This method runs the synchronous detect() in a thread pool executor
        to avoid blocking the event loop. Useful for integration with async
        applications like FastAPI.

        Args:
            frame: Input image as numpy array (BGR format)

        Returns:
            List of Detection objects containing detected objects

        Raises:
            Exception: If model loading or inference fails
        """
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            detections = await loop.run_in_executor(
                executor, self.detect, frame
            )
        return detections

    def draw_detections(self, frame: np.ndarray, detections: List[Detection]) -> np.ndarray:
        """
        Draw bounding boxes and labels on detected objects.

        Args:
            frame: Input image as numpy array (BGR format)
            detections: List of Detection objects to draw

        Returns:
            Frame with drawn detections (BGR format)
        """
        # Make a copy to avoid modifying the original frame
        annotated_frame = frame.copy()

        for detection in detections:
            x1, y1, x2, y2 = detection.bbox

            # Draw bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Prepare label text
            label = f"{detection.class_name}: {detection.confidence:.2f}"

            # Get text size for background rectangle
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )

            # Draw background rectangle for text
            cv2.rectangle(
                annotated_frame,
                (x1, y1 - text_height - baseline - 5),
                (x1 + text_width, y1),
                (0, 255, 0),
                -1
            )

            # Draw text
            cv2.putText(
                annotated_frame,
                label,
                (x1, y1 - baseline - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1
            )

        return annotated_frame
