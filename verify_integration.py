#!/usr/bin/env python3
"""
Verification script for YOLO detector integration.

This script verifies that the YoloDetector implementation is correct
without requiring actual YOLO model dependencies.
"""

import sys
from unittest.mock import Mock, MagicMock, patch
import numpy as np


def verify_detector_interface():
    """Verify YoloDetector has correct interface and behavior."""
    print("\n" + "="*60)
    print("YOLO Detector Interface Verification")
    print("="*60 + "\n")

    success = True

    # Import modules
    try:
        from src.config import YoloConfig
        from src.yolo_detector import YoloDetector, Detection
        print("✓ Modules imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import modules: {e}")
        return False

    # Check Detection dataclass
    print("\nVerifying Detection dataclass...")
    det = Detection(
        class_name="person",
        confidence=0.85,
        bbox=(10, 20, 100, 200),
        class_id=0
    )

    if det.class_name == "person":
        print("  ✓ class_name field works")
    else:
        print("  ✗ class_name field incorrect")
        success = False

    if det.confidence == 0.85:
        print("  ✓ confidence field works")
    else:
        print("  ✗ confidence field incorrect")
        success = False

    if det.bbox == (10, 20, 100, 200):
        print("  ✓ bbox field works")
    else:
        print("  ✗ bbox field incorrect")
        success = False

    if det.class_id == 0:
        print("  ✓ class_id field works")
    else:
        print("  ✗ class_id field incorrect")
        success = False

    # Check YoloDetector initialization
    print("\nVerifying YoloDetector initialization...")
    config = YoloConfig(
        model="yolov8n.pt",
        confidence=0.5,
        classes=["person", "car"]
    )

    detector = YoloDetector(config)

    if detector.config == config:
        print("  ✓ Config stored correctly")
    else:
        print("  ✗ Config not stored")
        success = False

    if detector._model is None:
        print("  ✓ Model not loaded (lazy loading)")
    else:
        print("  ✗ Model should not be loaded on init")
        success = False

    # Check method signatures
    print("\nVerifying method signatures...")

    if hasattr(detector, 'detect'):
        print("  ✓ detect() method exists")
    else:
        print("  ✗ detect() method missing")
        success = False

    if hasattr(detector, 'detect_async'):
        print("  ✓ detect_async() method exists")
    else:
        print("  ✗ detect_async() method missing")
        success = False

    if hasattr(detector, 'set_classes'):
        print("  ✓ set_classes() method exists")
    else:
        print("  ✗ set_classes() method missing")
        success = False

    if hasattr(detector, 'draw_detections'):
        print("  ✓ draw_detections() method exists")
    else:
        print("  ✗ draw_detections() method missing")
        success = False

    # Test set_classes
    print("\nVerifying set_classes()...")
    detector.set_classes(["person"])
    if detector.config.classes == ["person"]:
        print("  ✓ set_classes() updates config")
    else:
        print("  ✗ set_classes() doesn't work")
        success = False

    # Mock test of detect with YOLO results
    print("\nVerifying detect() with mocked YOLO...")
    with patch('src.yolo_detector.YoloDetector._load_model'):
        # Create mock YOLO model
        mock_model = MagicMock()

        # Mock result object
        mock_result = Mock()
        mock_boxes = Mock()

        # Mock detection: person at (10,10,100,100) with confidence 0.85
        mock_boxes.xyxy.cpu.return_value.numpy.return_value = np.array([
            [10.0, 10.0, 100.0, 100.0]
        ])
        mock_boxes.conf.cpu.return_value.numpy.return_value = np.array([0.85])
        mock_boxes.cls.cpu.return_value.numpy.return_value = np.array([0])
        mock_boxes.__len__ = lambda self: 1

        mock_result.boxes = mock_boxes
        mock_model.return_value = [mock_result]

        detector._model = mock_model
        detector._class_names = {0: "person", 1: "car"}

        # Run detection
        frame = np.zeros((640, 480, 3), dtype=np.uint8)
        detections = detector.detect(frame)

        if len(detections) == 1:
            print("  ✓ Returns list of detections")
        else:
            print(f"  ✗ Expected 1 detection, got {len(detections)}")
            success = False

        if detections and detections[0].class_name == "person":
            print("  ✓ Detection has correct class_name")
        else:
            print("  ✗ Detection class_name incorrect")
            success = False

        if detections and detections[0].confidence == 0.85:
            print("  ✓ Detection has correct confidence")
        else:
            print("  ✗ Detection confidence incorrect")
            success = False

        if detections and detections[0].bbox == (10, 10, 100, 100):
            print("  ✓ Detection has correct bbox")
        else:
            print("  ✗ Detection bbox incorrect")
            success = False

    # Test confidence filtering
    print("\nVerifying confidence filtering...")
    detector.config.confidence = 0.9
    with patch('src.yolo_detector.YoloDetector._load_model'):
        mock_model = MagicMock()
        mock_result = Mock()
        mock_boxes = Mock()

        # Mock detection with low confidence (should be filtered)
        mock_boxes.xyxy.cpu.return_value.numpy.return_value = np.array([
            [10.0, 10.0, 100.0, 100.0]
        ])
        mock_boxes.conf.cpu.return_value.numpy.return_value = np.array([0.5])  # Below threshold
        mock_boxes.cls.cpu.return_value.numpy.return_value = np.array([0])
        mock_boxes.__len__ = lambda self: 1

        mock_result.boxes = mock_boxes
        mock_model.return_value = [mock_result]

        detector._model = mock_model
        detector._class_names = {0: "person"}

        frame = np.zeros((640, 480, 3), dtype=np.uint8)
        detections = detector.detect(frame)

        if len(detections) == 0:
            print("  ✓ Low confidence detections filtered out")
        else:
            print("  ✗ Confidence filtering not working")
            success = False

    # Test class filtering
    print("\nVerifying class filtering...")
    detector.config.confidence = 0.5
    detector.config.classes = ["person"]  # Only allow person

    with patch('src.yolo_detector.YoloDetector._load_model'):
        mock_model = MagicMock()
        mock_result = Mock()
        mock_boxes = Mock()

        # Mock detection of a car (should be filtered)
        mock_boxes.xyxy.cpu.return_value.numpy.return_value = np.array([
            [10.0, 10.0, 100.0, 100.0]
        ])
        mock_boxes.conf.cpu.return_value.numpy.return_value = np.array([0.85])
        mock_boxes.cls.cpu.return_value.numpy.return_value = np.array([2])  # car class
        mock_boxes.__len__ = lambda self: 1

        mock_result.boxes = mock_boxes
        mock_model.return_value = [mock_result]

        detector._model = mock_model
        detector._class_names = {0: "person", 2: "car"}

        frame = np.zeros((640, 480, 3), dtype=np.uint8)
        detections = detector.detect(frame)

        if len(detections) == 0:
            print("  ✓ Unwanted classes filtered out")
        else:
            print("  ✗ Class filtering not working")
            success = False

    print("\n" + "="*60)
    if success:
        print("✓ ALL VERIFICATION CHECKS PASSED")
        print("\nThe YoloDetector implementation is correct.")
        print("To test with a real image, run: python3 test_integration.py")
        print("(Requires opencv-python and ultralytics packages)")
    else:
        print("✗ SOME CHECKS FAILED")
    print("="*60 + "\n")

    return success


if __name__ == "__main__":
    try:
        success = verify_detector_interface()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Verification failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
