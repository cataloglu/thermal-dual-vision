"""YOLO object detection with frame optimization."""

import cv2
import numpy as np
from typing import Any, List, Optional, Tuple

from src.logger import get_logger

# Initialize logger
logger = get_logger("yolo_detector")


def resize_for_inference(frame: np.ndarray, max_size: int = 640) -> Tuple[np.ndarray, Tuple[float, float]]:
    """
    Resize frame for YOLO inference while maintaining aspect ratio.

    YOLOv8n natively works with 640x640 images. Resizing reduces memory usage
    and improves inference speed without significant accuracy loss.

    Args:
        frame: Input frame (BGR format)
        max_size: Maximum dimension size (default 640 for YOLOv8n)

    Returns:
        Tuple of (resized_frame, scale_factors)
        - resized_frame: Resized frame for inference
        - scale_factors: (scale_x, scale_y) to map detections back to original size
    """
    height, width = frame.shape[:2]

    # If already small enough, return as-is
    if height <= max_size and width <= max_size:
        return frame, (1.0, 1.0)

    # Calculate scaling factor to fit within max_size while maintaining aspect ratio
    scale = max_size / max(height, width)
    new_width = int(width * scale)
    new_height = int(height * scale)

    # Resize with INTER_LINEAR for good quality/speed balance
    resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

    # Calculate scale factors for mapping detections back
    scale_x = width / new_width
    scale_y = height / new_height

    return resized, (scale_x, scale_y)


def scale_detections(
    detections: list,
    scale_factors: Tuple[float, float]
) -> list:
    """
    Scale detection bounding boxes back to original frame size.

    Args:
        detections: List of detection results with bounding boxes
        scale_factors: (scale_x, scale_y) from resize_for_inference

    Returns:
        Scaled detections in original frame coordinates
    """
    scale_x, scale_y = scale_factors
    scaled_detections = []

    for detection in detections:
        # Assuming detection format: {"bbox": [x, y, w, h], "class": str, "confidence": float}
        if "bbox" in detection:
            x, y, w, h = detection["bbox"]
            scaled_bbox = [
                x * scale_x,
                y * scale_y,
                w * scale_x,
                h * scale_y
            ]
            scaled_detection = detection.copy()
            scaled_detection["bbox"] = scaled_bbox
            scaled_detections.append(scaled_detection)
        else:
            scaled_detections.append(detection)

    return scaled_detections


class YOLODetector:
    """YOLO object detector with lazy model initialization."""

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.5,
        max_size: int = 640
    ) -> None:
        """
        Initialize YOLO Detector with lazy loading.

        Model is not loaded until first detection call to save memory
        and startup time.

        Args:
            model_name: YOLO model name (default: yolov8n.pt - nano model)
            confidence_threshold: Minimum confidence for detections (0.0-1.0)
            max_size: Maximum frame dimension for inference (default: 640)
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.max_size = max_size

        # Lazy initialization - model loaded on first use
        self._model: Optional[Any] = None
        logger.debug(
            "YOLODetector initialized with model=%s, conf=%.2f (lazy loading)",
            model_name,
            confidence_threshold
        )

    @property
    def model(self) -> Any:
        """
        Get YOLO model, loading it lazily on first access.

        Returns:
            Loaded YOLO model instance

        Raises:
            ImportError: If ultralytics is not installed
            Exception: If model loading fails
        """
        if self._model is None:
            self._lazy_load_model()
        return self._model

    def _lazy_load_model(self) -> None:
        """
        Lazy load YOLO model on first use.

        This defers model loading until actually needed, saving memory
        and startup time when YOLO detection is optional.

        Raises:
            ImportError: If ultralytics is not installed
            Exception: If model loading fails
        """
        try:
            from ultralytics import YOLO

            logger.info("Loading YOLO model: %s", self.model_name)
            self._model = YOLO(self.model_name)
            logger.info("YOLO model loaded successfully")
        except ImportError as e:
            logger.error("ultralytics not installed: %s", str(e))
            raise ImportError(
                "ultralytics package required for YOLO detection. "
                "Install with: pip install ultralytics"
            ) from e
        except Exception as e:
            logger.error("Failed to load YOLO model: %s", str(e))
            raise

    def detect(
        self,
        frame: np.ndarray,
        resize: bool = True
    ) -> List[dict]:
        """
        Detect objects in frame using YOLO.

        Args:
            frame: Input frame (BGR format)
            resize: Whether to resize frame for faster inference (default: True)

        Returns:
            List of detections with format:
                [{"bbox": [x, y, w, h], "class": str, "confidence": float}, ...]
        """
        # Resize frame if requested
        if resize:
            resized_frame, scale_factors = resize_for_inference(frame, self.max_size)
        else:
            resized_frame = frame
            scale_factors = (1.0, 1.0)

        # Run inference (this triggers lazy model loading via property)
        # stream=True enables memory-efficient batch processing
        # verbose=False disables unnecessary logging for performance
        results = self.model.predict(
            resized_frame,
            conf=self.confidence_threshold,
            stream=True,
            verbose=False
        )

        # Parse detections
        detections: List[dict] = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Extract bounding box in xyxy format
                xyxy = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = xyxy
                w = x2 - x1
                h = y2 - y1

                # Extract class and confidence
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                confidence = float(box.conf[0])

                detections.append({
                    "bbox": [float(x1), float(y1), float(w), float(h)],
                    "class": cls_name,
                    "confidence": confidence
                })

        # Scale detections back to original frame size if resized
        if resize:
            detections = scale_detections(detections, scale_factors)

        return detections

    def detect_batch(
        self,
        frames: List[np.ndarray],
        resize: bool = True
    ) -> List[List[dict]]:
        """
        Detect objects in multiple frames using batch inference.

        Batch processing improves throughput when processing multiple frames
        by reducing per-frame overhead. Useful when queue builds up.

        Args:
            frames: List of input frames (BGR format)
            resize: Whether to resize frames for faster inference (default: True)

        Returns:
            List of detection lists, one per frame. Each detection has format:
                [{"bbox": [x, y, w, h], "class": str, "confidence": float}, ...]
        """
        if not frames:
            return []

        # Prepare frames for batch inference
        batch_frames = []
        batch_scale_factors = []

        for frame in frames:
            if resize:
                resized_frame, scale_factors = resize_for_inference(frame, self.max_size)
            else:
                resized_frame = frame
                scale_factors = (1.0, 1.0)

            batch_frames.append(resized_frame)
            batch_scale_factors.append(scale_factors)

        # Run batch inference with stream=True for memory efficiency
        # verbose=False disables per-frame logging
        results = self.model.predict(
            batch_frames,
            conf=self.confidence_threshold,
            stream=True,
            verbose=False
        )

        # Parse detections for each frame
        all_detections: List[List[dict]] = []

        for result, scale_factors in zip(results, batch_scale_factors):
            frame_detections: List[dict] = []
            boxes = result.boxes

            for box in boxes:
                # Extract bounding box in xyxy format
                xyxy = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = xyxy
                w = x2 - x1
                h = y2 - y1

                # Extract class and confidence
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                confidence = float(box.conf[0])

                frame_detections.append({
                    "bbox": [float(x1), float(y1), float(w), float(h)],
                    "class": cls_name,
                    "confidence": confidence
                })

            # Scale detections back to original frame size if resized
            if resize:
                frame_detections = scale_detections(frame_detections, scale_factors)

            all_detections.append(frame_detections)

        return all_detections

    def is_loaded(self) -> bool:
        """
        Check if YOLO model is loaded.

        Returns:
            True if model is loaded, False otherwise
        """
        return self._model is not None
