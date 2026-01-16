"""YOLO object detection with frame optimization."""

import cv2
import numpy as np
from typing import Tuple


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
