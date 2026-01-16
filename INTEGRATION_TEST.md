# YOLO Detector Integration Test

This document describes how to run the integration test for the YOLO detector with a real image containing a person.

## Prerequisites

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

Required packages:
- `opencv-python-headless>=4.8.0`
- `numpy>=1.24.0`
- `ultralytics>=8.0.0`

## Running the Integration Test

### Option 1: Automated Test Script

Run the provided integration test script:

```bash
python3 test_integration.py
```

This script will:
1. Download a sample image with people (from YOLOv5 test images)
2. Initialize the YoloDetector with person detection
3. Run detection on the image
4. Verify the results
5. Save an annotated image with bounding boxes

### Option 2: Manual Test

You can also test manually with your own image:

```python
from src.config import YoloConfig
from src.yolo_detector import YoloDetector
import cv2

# Initialize detector
config = YoloConfig(
    model="yolov8n.pt",
    confidence=0.5,
    classes=["person"]
)
detector = YoloDetector(config)

# Load your image
frame = cv2.imread("path/to/your/image.jpg")

# Run detection
detections = detector.detect(frame)

# Print results
for det in detections:
    print(f"{det.class_name}: {det.confidence:.2f} at {det.bbox}")

# Draw and save
annotated = detector.draw_detections(frame, detections)
cv2.imwrite("output.jpg", annotated)
```

## Expected Results

The test should:
- ✓ Successfully load the YOLO model
- ✓ Detect person(s) in the test image
- ✓ Return Detection objects with:
  - `class_name='person'`
  - `confidence >= 0.5` (default threshold)
  - Valid bounding box coordinates (x1, y1, x2, y2)
  - Correct class_id for person class
- ✓ Generate annotated image with bounding boxes and labels

## Success Criteria

1. **Detection Objects**: At least one Detection object with `class_name='person'`
2. **Confidence**: All detections have confidence >= configured threshold
3. **Bounding Boxes**: Valid coordinates (x1 < x2, y1 < y2)
4. **Performance**: Detection completes in reasonable time (< 500ms on CPU)

## Troubleshooting

### Model Download
On first run, YOLOv8n model will be automatically downloaded (~6MB). This is normal and only happens once.

### No Detections
If no persons are detected:
- Verify the image actually contains people
- Try lowering the confidence threshold
- Check image is loaded correctly (not None)

### Memory Issues
For memory testing over 1000 inferences, see `tests/test_yolo_detector.py::test_memory_leak`

## Test Images

The integration test uses this public test image:
- URL: `https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/zidane.jpg`
- Content: Photo of Zinedine Zidane (contains 2 people)
- Expected detections: 2 persons with high confidence

You can also use your own test images with people.
