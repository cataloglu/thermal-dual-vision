"""
Inference service for Smart Motion Detector v2.

This service handles YOLOv8 model loading, preprocessing, and inference.
"""
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from ultralytics import YOLO


logger = logging.getLogger(__name__)


class InferenceService:
    """Service for YOLOv8 inference and preprocessing."""
    
    # Model configuration
    MODELS_DIR = Path("app/models")
    PERSON_CLASS_ID = 0  # COCO class ID for person
    
    # Preprocessing configuration
    INFERENCE_SIZE = (640, 640)
    CLAHE_CLIP_LIMIT = 2.0
    CLAHE_TILE_SIZE = (8, 8)
    GAUSSIAN_KERNEL = (3, 3)
    
    # Aspect ratio filtering (person shape)
    PERSON_RATIO_MIN = 0.3  # Tall/skinny person
    PERSON_RATIO_MAX = 0.8  # Normal person
    
    def __init__(self):
        """Initialize inference service."""
        self.model: Optional[YOLO] = None
        self.model_name: Optional[str] = None
        
        # Ensure models directory exists
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    def load_model(self, model_name: str = "yolov8n") -> None:
        """
        Load YOLOv8 model.
        
        Downloads model from Ultralytics if not exists.
        Performs warmup inference.
        
        Args:
            model_name: Model name (yolov8n or yolov8s)
            
        Raises:
            Exception: If model loading fails
        """
        try:
            model_filename = f"{model_name}.pt"
            model_path = self.MODELS_DIR / model_filename
            root_path = Path.cwd() / model_filename

            logger.info("Loading YOLO model: %s", model_name)

            # Load model from local paths or auto-download if missing
            if model_path.exists():
                source = str(model_path)
            elif root_path.exists():
                if not model_path.exists():
                    try:
                        shutil.move(str(root_path), str(model_path))
                        logger.info("Moved model from repo root to %s", model_path)
                        source = str(model_path)
                    except Exception as move_error:
                        logger.warning(
                            "Failed to move model from repo root (%s): %s",
                            root_path,
                            move_error,
                        )
                        source = str(root_path)
                else:
                    source = str(model_path)
            else:
                source = model_filename

            self.model = YOLO(source)
            self.model_name = model_name
            
            # Warmup inference
            logger.info("Performing warmup inference...")
            dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
            self.model(dummy_frame, verbose=False)
            
            logger.info(f"Model loaded successfully: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise
    
    def preprocess_thermal(
        self,
        frame: np.ndarray,
        enable_enhancement: bool = True,
        clahe_clip_limit: float = CLAHE_CLIP_LIMIT,
        clahe_tile_size: Tuple[int, int] = CLAHE_TILE_SIZE,
    ) -> np.ndarray:
        """
        Preprocess thermal image with CLAHE enhancement.
        
        Research-backed: mAP improvement 0.93 → 0.99 (+6%)
        Source: Springer 2025 - Kurtosis-based histogram enhancement
        
        Args:
            frame: Input thermal frame (BGR or grayscale)
            enable_enhancement: Enable CLAHE enhancement
            clahe_clip_limit: CLAHE clip limit (default: 2.0)
            clahe_tile_size: CLAHE tile grid size (default: 8x8)
            
        Returns:
            Enhanced and resized frame ready for inference
        """
        # Convert to grayscale if needed
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        if enable_enhancement:
            # CLAHE enhancement
            clahe = cv2.createCLAHE(
                clipLimit=clahe_clip_limit,
                tileGridSize=clahe_tile_size
            )
            enhanced = clahe.apply(gray)
            
            # Gaussian blur (noise reduction)
            enhanced = cv2.GaussianBlur(enhanced, self.GAUSSIAN_KERNEL, 0)
        else:
            enhanced = gray
        
        # Convert back to BGR for YOLOv8
        if len(enhanced.shape) == 2:
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        
        return enhanced
    
    def preprocess_color(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess color image.
        
        Args:
            frame: Input color frame (BGR)
            
        Returns:
            Resized frame ready for inference
        """
        return frame
    
    def infer(
        self,
        frame: np.ndarray,
        confidence_threshold: float = 0.25,
    ) -> List[Dict]:
        """
        Run YOLOv8 inference on frame.
        
        Filters by confidence and person class only.
        
        Args:
            frame: Preprocessed frame (640x640)
            confidence_threshold: Minimum confidence (0.0-1.0)
            
        Returns:
            List of detections with bbox, confidence, class_id
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        # Run inference
        results = self.model(frame, conf=confidence_threshold, verbose=False)
        
        # Extract detections
        detections = []
        
        for result in results:
            boxes = result.boxes
            
            if boxes is None or len(boxes) == 0:
                continue
            
            for box in boxes:
                # Get class ID
                class_id = int(box.cls[0])
                
                # Filter: person only (class_id = 0)
                if class_id != self.PERSON_CLASS_ID:
                    continue
                
                # Get bbox coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                # Get confidence
                confidence = float(box.conf[0])
                
                detections.append({
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "confidence": confidence,
                    "class_id": class_id,
                    "class_name": "person",
                })
        
        return detections
    
    def filter_by_aspect_ratio(
        self,
        detections: List[Dict],
        min_ratio: float = PERSON_RATIO_MIN,
        max_ratio: float = PERSON_RATIO_MAX,
    ) -> List[Dict]:
        """
        Filter detections by aspect ratio (width/height).
        
        Person shape: 0.3-0.8 ratio (tall/skinny to normal)
        Trees/walls: >1.0 ratio (wide) → ignore
        
        Args:
            detections: List of detections
            min_ratio: Minimum aspect ratio (default: 0.3)
            max_ratio: Maximum aspect ratio (default: 0.8)
            
        Returns:
            Filtered detections
        """
        filtered = []
        
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            width = x2 - x1
            height = y2 - y1
            
            if height == 0:
                continue
            
            ratio = width / height
            
            # Check if ratio is in person range
            if min_ratio <= ratio <= max_ratio:
                det["aspect_ratio"] = ratio
                filtered.append(det)
            else:
                logger.debug(
                    f"Detection filtered by aspect ratio: {ratio:.2f} "
                    f"(expected {min_ratio}-{max_ratio})"
                )
        
        return filtered
    
    def check_temporal_consistency(
        self,
        current_detections: List[Dict],
        detection_history: List[List[Dict]],
        min_consecutive_frames: int = 3,
        max_gap_frames: int = 1,
    ) -> bool:
        """
        Check temporal consistency across frames.
        
        Object must be detected in N consecutive frames.
        Tolerates M frame gaps (prevents false negatives from occlusion).
        
        Args:
            current_detections: Current frame detections
            detection_history: List of previous frame detections
            min_consecutive_frames: Minimum consecutive frames (default: 3)
            max_gap_frames: Maximum gap frames to tolerate (default: 1)
            
        Returns:
            True if temporally consistent
        """
        if len(current_detections) == 0:
            return False
        
        # Need at least min_consecutive_frames in history
        if len(detection_history) < min_consecutive_frames - 1:
            return False
        
        # Check last N frames
        recent_history = detection_history[-(min_consecutive_frames - 1):]
        
        # Count frames with detections
        frames_with_detections = sum(1 for frame_dets in recent_history if len(frame_dets) > 0)
        
        # Add current frame
        frames_with_detections += 1
        
        # Calculate gaps
        gaps = min_consecutive_frames - frames_with_detections
        
        # Check if gaps are within tolerance
        return gaps <= max_gap_frames
    
    def check_zone_inertia(
        self,
        detection: Dict,
        zone_polygon: List[List[float]],
        zone_history: List[bool],
        min_frames_in_zone: int = 3,
        frame_width: int = 640,
        frame_height: int = 640,
    ) -> bool:
        """
        Check zone inertia (object must stay in zone for N frames).
        
        Prevents false positives from bounding box jitter.
        Better than Frigate (1-2 frames) - we use 3-5 frames!
        
        Args:
            detection: Detection dict with bbox
            zone_polygon: Zone polygon coordinates (normalized 0.0-1.0)
            zone_history: List of booleans (in zone or not) for previous frames
            min_frames_in_zone: Minimum frames in zone (default: 3)
            frame_width: Frame width for normalization (default: 640)
            frame_height: Frame height for normalization (default: 640)
            
        Returns:
            True if object has been in zone for min_frames_in_zone
        """
        # Check if current detection is in zone
        bbox_center = self._get_bbox_center(detection["bbox"])
        
        # Normalize bbox center to 0.0-1.0 range
        normalized_center = (
            bbox_center[0] / frame_width,
            bbox_center[1] / frame_height
        )
        
        in_zone = self._point_in_polygon(normalized_center, zone_polygon)
        
        # Add to history
        zone_history.append(in_zone)
        
        # Keep only last N frames
        if len(zone_history) > min_frames_in_zone:
            zone_history.pop(0)
        
        # Check if in zone for min_frames_in_zone
        if len(zone_history) < min_frames_in_zone:
            return False
        
        # Count frames in zone
        frames_in_zone = sum(zone_history)
        
        return frames_in_zone >= min_frames_in_zone
    
    def _get_bbox_center(self, bbox: List[int]) -> Tuple[float, float]:
        """
        Get center point of bounding box.
        
        Args:
            bbox: Bounding box [x1, y1, x2, y2]
            
        Returns:
            Center point (x, y)
        """
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        return (center_x, center_y)
    
    def _point_in_polygon(
        self,
        point: Tuple[float, float],
        polygon: List[List[float]]
    ) -> bool:
        """
        Check if point is inside polygon using ray casting algorithm.
        
        Args:
            point: Point (x, y)
            polygon: Polygon coordinates [[x1, y1], [x2, y2], ...]
            
        Returns:
            True if point is inside polygon
        """
        x, y = point
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside


# Global singleton instance
_inference_service: Optional[InferenceService] = None


def get_inference_service() -> InferenceService:
    """
    Get or create the global inference service instance.
    
    Returns:
        InferenceService: Global inference service instance
    """
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
    return _inference_service
