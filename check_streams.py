import cv2
import time

STREAMS = {
    "Color": "rtsp://127.0.0.1:8554/color",
    "Thermal 1": "rtsp://127.0.0.1:8554/thermal1",
    "Thermal 2": "rtsp://127.0.0.1:8554/thermal2"
}

print("Testing RTSP streams...")

for name, url in STREAMS.items():
    print(f"Checking {name} ({url})...", end=" ", flush=True)
    try:
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            print("FAILED (Could not open)")
            continue
            
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"OK ({frame.shape[1]}x{frame.shape[0]})")
        else:
            print("FAILED (No frame)")
            
        cap.release()
    except Exception as e:
        print(f"ERROR: {e}")

print("Done.")
