"""Tests for YOLO object detection module."""

import asyncio
import sys
import time
from unittest.mock import MagicMock, patch, PropertyMock

import cv2
import numpy as np
import pytest

from src.config import YoloConfig
from src.yolo_detector import Detection, YoloDetector


# Mock ultralytics module before any tests run
sys.modules['ultralytics'] = MagicMock()


@pytest.fixture
def yolo_config():
    """Create a basic YoloConfig for testing."""
    return YoloConfig(
        model="yolov8n",
        confidence=0.5,
        classes=["person", "car"]
    )


@pytest.fixture
def sample_frame():
    """Create a sample frame for testing."""
    # Create a simple 640x480 BGR image
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add a white rectangle to simulate an object
    cv2.rectangle(frame, (100, 100), (200, 200), (255, 255, 255), -1)
    return frame


@pytest.fixture
def mock_yolo_model():
    """Create a mock YOLO model with realistic behavior."""
    mock_model = MagicMock()

    # Mock the names attribute (class names)
    mock_model.names = {
        0: "person",
        1: "car",
        2: "dog",
        3: "cat"
    }

    # Mock detection results
    mock_result = MagicMock()
    mock_boxes = MagicMock()

    # Mock bounding boxes (x1, y1, x2, y2 format)
    mock_boxes.xyxy.cpu().numpy.return_value = np.array([
        [100, 100, 200, 200],  # person
        [300, 300, 400, 400]   # car
    ])

    # Mock confidence scores
    mock_boxes.conf.cpu().numpy.return_value = np.array([0.85, 0.92])

    # Mock class IDs
    mock_boxes.cls.cpu().numpy.return_value = np.array([0, 1])

    # Set up the boxes length
    type(mock_boxes).__len__ = lambda x: 2

    mock_result.boxes = mock_boxes
    mock_model.return_value = [mock_result]

    return mock_model


class TestDetection:
    """Tests for the Detection dataclass."""

    def test_detection_creation(self):
        """Test creating a Detection object."""
        detection = Detection(
            class_name="person",
            confidence=0.85,
            bbox=(100, 100, 200, 200),
            class_id=0
        )

        assert detection.class_name == "person"
        assert detection.confidence == 0.85
        assert detection.bbox == (100, 100, 200, 200)
        assert detection.class_id == 0


class TestYoloDetectorInitialization:
    """Tests for YoloDetector initialization."""

    def test_initialization(self, yolo_config):
        """Test basic initialization of YoloDetector."""
        detector = YoloDetector(yolo_config)

        assert detector.config == yolo_config
        assert detector._model is None
        assert detector._class_names is None

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = YoloConfig(
            model="yolov8m",
            confidence=0.7,
            classes=["dog", "cat"]
        )
        detector = YoloDetector(config)

        assert detector.config.model == "yolov8m"
        assert detector.config.confidence == 0.7
        assert detector.config.classes == ["dog", "cat"]


class TestYoloDetectorModelLoading:
    """Tests for YOLO model loading."""

    @patch('ultralytics.YOLO')
    def test_lazy_loading(self, mock_yolo_class, yolo_config):
        """Test that model is not loaded until first detection."""
        detector = YoloDetector(yolo_config)

        # Model should not be loaded yet
        assert detector._model is None
        mock_yolo_class.assert_not_called()

    @patch('ultralytics.YOLO')
    def test_model_loaded_on_first_detect(self, mock_yolo_class, yolo_config, sample_frame, mock_yolo_model):
        """Test that model is loaded on first detect() call."""
        mock_yolo_class.return_value = mock_yolo_model
        detector = YoloDetector(yolo_config)

        detector.detect(sample_frame)

        # Model should be loaded
        mock_yolo_class.assert_called_once_with("yolov8n")
        assert detector._model is not None

    @patch('ultralytics.YOLO')
    def test_model_loaded_only_once(self, mock_yolo_class, yolo_config, sample_frame, mock_yolo_model):
        """Test that model is only loaded once across multiple detections."""
        mock_yolo_class.return_value = mock_yolo_model
        detector = YoloDetector(yolo_config)

        detector.detect(sample_frame)
        detector.detect(sample_frame)
        detector.detect(sample_frame)

        # Model should be loaded only once
        mock_yolo_class.assert_called_once()

    @patch('ultralytics.YOLO')
    def test_model_loading_failure(self, mock_yolo_class, yolo_config, sample_frame):
        """Test handling of model loading failure."""
        mock_yolo_class.side_effect = Exception("Failed to load model")
        detector = YoloDetector(yolo_config)

        with pytest.raises(Exception, match="Failed to load model"):
            detector.detect(sample_frame)


class TestYoloDetectorDetection:
    """Tests for object detection functionality."""

    @patch('ultralytics.YOLO')
    def test_detect_basic(self, mock_yolo_class, yolo_config, sample_frame, mock_yolo_model):
        """Test basic object detection."""
        mock_yolo_class.return_value = mock_yolo_model
        detector = YoloDetector(yolo_config)

        detections = detector.detect(sample_frame)

        assert len(detections) == 2
        assert detections[0].class_name == "person"
        assert detections[0].confidence == 0.85
        assert detections[0].bbox == (100, 100, 200, 200)
        assert detections[1].class_name == "car"
        assert detections[1].confidence == 0.92

    @patch('ultralytics.YOLO')
    def test_detect_with_confidence_filter(self, mock_yolo_class, yolo_config, sample_frame):
        """Test detection with confidence threshold filtering."""
        # Create mock model with one low confidence detection
        mock_model = MagicMock()
        mock_model.names = {0: "person", 1: "car"}

        mock_result = MagicMock()
        mock_boxes = MagicMock()
        mock_boxes.xyxy.cpu().numpy.return_value = np.array([
            [100, 100, 200, 200],
            [300, 300, 400, 400]
        ])
        mock_boxes.conf.cpu().numpy.return_value = np.array([0.3, 0.85])  # First is below threshold
        mock_boxes.cls.cpu().numpy.return_value = np.array([0, 1])
        type(mock_boxes).__len__ = lambda x: 2
        mock_result.boxes = mock_boxes
        mock_model.return_value = [mock_result]

        mock_yolo_class.return_value = mock_model

        detector = YoloDetector(yolo_config)
        detections = detector.detect(sample_frame)

        # Only one detection should pass the confidence threshold (0.5)
        assert len(detections) == 1
        assert detections[0].class_name == "car"
        assert detections[0].confidence == 0.85

    @patch('ultralytics.YOLO')
    def test_detect_with_class_filter(self, mock_yolo_class, yolo_config, sample_frame):
        """Test detection with class filtering."""
        # Create mock model with multiple classes
        mock_model = MagicMock()
        mock_model.names = {0: "person", 1: "car", 2: "dog"}

        mock_result = MagicMock()
        mock_boxes = MagicMock()
        mock_boxes.xyxy.cpu().numpy.return_value = np.array([
            [100, 100, 200, 200],
            [200, 200, 300, 300],
            [300, 300, 400, 400]
        ])
        mock_boxes.conf.cpu().numpy.return_value = np.array([0.85, 0.92, 0.88])
        mock_boxes.cls.cpu().numpy.return_value = np.array([0, 1, 2])
        type(mock_boxes).__len__ = lambda x: 3
        mock_result.boxes = mock_boxes
        mock_model.return_value = [mock_result]

        mock_yolo_class.return_value = mock_model

        # Config has classes=["person", "car"], so "dog" should be filtered
        detector = YoloDetector(yolo_config)
        detections = detector.detect(sample_frame)

        assert len(detections) == 2
        assert detections[0].class_name == "person"
        assert detections[1].class_name == "car"

    @patch('ultralytics.YOLO')
    def test_detect_no_objects(self, mock_yolo_class, yolo_config, sample_frame):
        """Test detection when no objects are found."""
        mock_model = MagicMock()
        mock_model.names = {0: "person"}

        mock_result = MagicMock()
        mock_result.boxes = None  # No detections
        mock_model.return_value = [mock_result]

        mock_yolo_class.return_value = mock_model

        detector = YoloDetector(yolo_config)
        detections = detector.detect(sample_frame)

        assert len(detections) == 0

    @patch('ultralytics.YOLO')
    def test_detect_empty_boxes(self, mock_yolo_class, yolo_config, sample_frame):
        """Test detection when boxes list is empty."""
        mock_model = MagicMock()
        mock_model.names = {0: "person"}

        mock_result = MagicMock()
        mock_boxes = MagicMock()
        type(mock_boxes).__len__ = lambda x: 0  # Empty boxes
        mock_result.boxes = mock_boxes
        mock_model.return_value = [mock_result]

        mock_yolo_class.return_value = mock_model

        detector = YoloDetector(yolo_config)
        detections = detector.detect(sample_frame)

        assert len(detections) == 0

    @patch('ultralytics.YOLO')
    def test_detect_inference_failure(self, mock_yolo_class, yolo_config, sample_frame):
        """Test handling of inference failure."""
        mock_model = MagicMock()
        mock_model.names = {0: "person"}
        mock_model.side_effect = Exception("Inference failed")

        mock_yolo_class.return_value = mock_model

        detector = YoloDetector(yolo_config)

        with pytest.raises(Exception, match="Inference failed"):
            detector.detect(sample_frame)

    @patch('ultralytics.YOLO')
    def test_inference_performance(self, mock_yolo_class, yolo_config, sample_frame, mock_yolo_model):
        """Test that inference completes within acceptable time threshold."""
        mock_yolo_class.return_value = mock_yolo_model
        detector = YoloDetector(yolo_config)

        # Pre-load the model to exclude initialization time
        detector.detect(sample_frame)

        # Measure inference time over multiple runs
        num_runs = 10
        start_time = time.time()
        for _ in range(num_runs):
            detector.detect(sample_frame)
        end_time = time.time()

        # Calculate average inference time
        avg_inference_time = (end_time - start_time) / num_runs
        avg_inference_time_ms = avg_inference_time * 1000

        # Assert inference time is below 500ms
        assert avg_inference_time_ms < 500, \
            f"Inference time {avg_inference_time_ms:.2f}ms exceeds 500ms threshold"


class TestYoloDetectorAsyncDetection:
    """Tests for async detection functionality."""

    @patch('ultralytics.YOLO')
    @pytest.mark.asyncio
    async def test_detect_async(self, mock_yolo_class, yolo_config, sample_frame, mock_yolo_model):
        """Test async detection."""
        mock_yolo_class.return_value = mock_yolo_model
        detector = YoloDetector(yolo_config)

        detections = await detector.detect_async(sample_frame)

        assert len(detections) == 2
        assert detections[0].class_name == "person"
        assert detections[1].class_name == "car"

    @patch('ultralytics.YOLO')
    @pytest.mark.asyncio
    async def test_detect_async_runs_in_executor(self, mock_yolo_class, yolo_config, sample_frame, mock_yolo_model):
        """Test that async detection runs in a thread pool executor."""
        mock_yolo_class.return_value = mock_yolo_model
        detector = YoloDetector(yolo_config)

        # This should not block the event loop
        detections = await detector.detect_async(sample_frame)

        assert isinstance(detections, list)


class TestYoloDetectorConfiguration:
    """Tests for dynamic configuration changes."""

    def test_set_classes(self, yolo_config):
        """Test dynamically changing detection classes."""
        detector = YoloDetector(yolo_config)

        assert detector.config.classes == ["person", "car"]

        detector.set_classes(["dog", "cat", "bird"])

        assert detector.config.classes == ["dog", "cat", "bird"]

    def test_set_classes_to_none(self, yolo_config):
        """Test setting classes to None to detect all classes."""
        detector = YoloDetector(yolo_config)

        detector.set_classes(None)

        assert detector.config.classes is None

    @patch('ultralytics.YOLO')
    def test_set_classes_affects_detection(self, mock_yolo_class, yolo_config, sample_frame):
        """Test that changing classes affects detection results."""
        mock_model = MagicMock()
        mock_model.names = {0: "person", 1: "car", 2: "dog"}

        mock_result = MagicMock()
        mock_boxes = MagicMock()
        mock_boxes.xyxy.cpu().numpy.return_value = np.array([
            [100, 100, 200, 200],
            [200, 200, 300, 300],
            [300, 300, 400, 400]
        ])
        mock_boxes.conf.cpu().numpy.return_value = np.array([0.85, 0.92, 0.88])
        mock_boxes.cls.cpu().numpy.return_value = np.array([0, 1, 2])
        type(mock_boxes).__len__ = lambda x: 3
        mock_result.boxes = mock_boxes
        mock_model.return_value = [mock_result]

        mock_yolo_class.return_value = mock_model

        detector = YoloDetector(yolo_config)

        # Initially configured for ["person", "car"]
        detections = detector.detect(sample_frame)
        assert len(detections) == 2

        # Change to only detect dogs
        detector.set_classes(["dog"])
        detections = detector.detect(sample_frame)
        assert len(detections) == 1
        assert detections[0].class_name == "dog"

        # Set to None to detect all classes
        detector.set_classes(None)
        detections = detector.detect(sample_frame)
        assert len(detections) == 3


class TestYoloDetectorDrawing:
    """Tests for drawing detection results."""

    def test_draw_detections(self, yolo_config, sample_frame):
        """Test drawing detections on a frame."""
        detector = YoloDetector(yolo_config)

        detections = [
            Detection(
                class_name="person",
                confidence=0.85,
                bbox=(100, 100, 200, 200),
                class_id=0
            ),
            Detection(
                class_name="car",
                confidence=0.92,
                bbox=(300, 300, 400, 400),
                class_id=1
            )
        ]

        annotated_frame = detector.draw_detections(sample_frame, detections)

        # Check that a new frame was created (not modified in place)
        assert annotated_frame is not sample_frame
        assert annotated_frame.shape == sample_frame.shape

        # Check that the frames are different (drawing happened)
        assert not np.array_equal(annotated_frame, sample_frame)

    def test_draw_detections_empty_list(self, yolo_config, sample_frame):
        """Test drawing with empty detection list."""
        detector = YoloDetector(yolo_config)

        annotated_frame = detector.draw_detections(sample_frame, [])

        # Should return a copy of the original frame
        assert annotated_frame is not sample_frame
        assert np.array_equal(annotated_frame, sample_frame)

    def test_draw_detections_preserves_original(self, yolo_config, sample_frame):
        """Test that drawing does not modify the original frame."""
        detector = YoloDetector(yolo_config)

        original_frame_copy = sample_frame.copy()

        detections = [
            Detection(
                class_name="person",
                confidence=0.85,
                bbox=(100, 100, 200, 200),
                class_id=0
            )
        ]

        detector.draw_detections(sample_frame, detections)

        # Original frame should be unchanged
        assert np.array_equal(sample_frame, original_frame_copy)

    def test_draw_detections_high_confidence(self, yolo_config, sample_frame):
        """Test drawing detections with various confidence levels."""
        detector = YoloDetector(yolo_config)

        detections = [
            Detection(
                class_name="person",
                confidence=0.99,
                bbox=(50, 50, 150, 150),
                class_id=0
            ),
            Detection(
                class_name="car",
                confidence=0.51,
                bbox=(200, 200, 300, 300),
                class_id=1
            )
        ]

        annotated_frame = detector.draw_detections(sample_frame, detections)

        assert annotated_frame.shape == sample_frame.shape
        assert not np.array_equal(annotated_frame, sample_frame)
