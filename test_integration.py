#!/usr/bin/env python3
"""Integration test for YOLO detector with real image."""

import sys
from pathlib import Path

import cv2
import numpy as np

from src.config import YoloConfig
from src.yolo_detector import YoloDetector


def download_sample_image() -> str:
    """
    Download a sample image with a person for testing.

    Returns:
        Path to the downloaded image
    """
    import urllib.request

    # Use a public domain test image from COCO dataset samples
    # This image is known to contain people
    url = "https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/zidane.jpg"
    output_path = ".auto-claude/test_data/test_person.jpg"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading test image from {url}...")
    try:
        urllib.request.urlretrieve(url, output_path)
        print(f"✓ Image downloaded to {output_path}")
        return output_path
    except Exception as e:
        print(f"✗ Failed to download image: {e}")
        raise


def test_detection_with_real_image():
    """Test YOLO detection with a real image containing a person."""
    print("\n" + "="*60)
    print("YOLO Detector Integration Test - Real Image with Person")
    print("="*60 + "\n")

    # Download test image
    image_path = download_sample_image()

    # Load image
    print(f"Loading image from {image_path}...")
    frame = cv2.imread(image_path)

    if frame is None:
        print(f"✗ Failed to load image from {image_path}")
        return False

    print(f"✓ Image loaded: {frame.shape[1]}x{frame.shape[0]} pixels\n")

    # Initialize detector with person detection
    print("Initializing YoloDetector...")
    config = YoloConfig(
        model="yolov8n.pt",
        confidence=0.5,
        classes=["person"]  # Only detect people
    )
    detector = YoloDetector(config)
    print("✓ Detector initialized\n")

    # Run detection
    print("Running detection on image...")
    detections = detector.detect(frame)
    print(f"✓ Detection complete: {len(detections)} object(s) detected\n")

    # Display results
    print("-" * 60)
    print("DETECTION RESULTS:")
    print("-" * 60)

    if len(detections) == 0:
        print("⚠ No objects detected (this may be unexpected)")
        return False

    person_found = False
    for i, det in enumerate(detections, 1):
        print(f"\nDetection #{i}:")
        print(f"  Class:      {det.class_name}")
        print(f"  Confidence: {det.confidence:.3f}")
        print(f"  BBox:       {det.bbox}")
        print(f"  Class ID:   {det.class_id}")

        if det.class_name == "person":
            person_found = True

    print("\n" + "-" * 60)

    # Verify results
    print("\nVERIFICATION:")
    print("-" * 60)

    success = True

    # Check 1: At least one detection
    if len(detections) > 0:
        print("✓ Detections returned")
    else:
        print("✗ No detections returned")
        success = False

    # Check 2: Person detected
    if person_found:
        print("✓ Person(s) detected")
    else:
        print("✗ No person detected (expected for test image)")
        success = False

    # Check 3: Confidence threshold
    min_confidence = min(det.confidence for det in detections)
    max_confidence = max(det.confidence for det in detections)
    print(f"✓ Confidence range: {min_confidence:.3f} - {max_confidence:.3f}")

    if min_confidence >= config.confidence:
        print(f"✓ All detections meet confidence threshold ({config.confidence})")
    else:
        print(f"✗ Some detections below threshold")
        success = False

    # Check 4: Bounding boxes valid
    all_boxes_valid = all(
        len(det.bbox) == 4 and
        det.bbox[0] < det.bbox[2] and  # x1 < x2
        det.bbox[1] < det.bbox[3]      # y1 < y2
        for det in detections
    )

    if all_boxes_valid:
        print("✓ All bounding boxes valid")
    else:
        print("✗ Invalid bounding boxes detected")
        success = False

    # Save annotated image
    print("\nDrawing detections on image...")
    annotated = detector.draw_detections(frame, detections)
    output_path = ".auto-claude/test_data/test_person_annotated.jpg"
    cv2.imwrite(output_path, annotated)
    print(f"✓ Annotated image saved to {output_path}")

    print("\n" + "="*60)
    if success:
        print("✓ INTEGRATION TEST PASSED")
    else:
        print("✗ INTEGRATION TEST FAILED")
    print("="*60 + "\n")

    return success


if __name__ == "__main__":
    try:
        success = test_detection_with_real_image()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
