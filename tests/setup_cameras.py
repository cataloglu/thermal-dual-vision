import requests
import time
import sys

API_URL = "http://127.0.0.1:8000/api"

CAMERAS = [
    {
        "name": "Color Camera",
        "type": "color",
        "rtsp_url_color": "rtsp://host.docker.internal:8554/color",
        "enabled": True,
        "stream_roles": ["live", "detect"],
        "detection_source": "color"
    },
    {
        "name": "Thermal Camera 1",
        "type": "thermal",
        "rtsp_url_thermal": "rtsp://host.docker.internal:8554/thermal1",
        "enabled": True,
        "stream_roles": ["live", "detect"],
        "detection_source": "thermal"
    },
    {
        "name": "Thermal Camera 2",
        "type": "thermal",
        "rtsp_url_thermal": "rtsp://host.docker.internal:8554/thermal2",
        "enabled": True,
        "stream_roles": ["live", "detect"],
        "detection_source": "thermal"
    }
]

def wait_for_api():
    print("Waiting for API to be ready...")
    for i in range(30):
        try:
            response = requests.get(f"{API_URL}/health", timeout=2)
            if response.status_code == 200:
                print("API is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
        sys.stdout.write(".")
        sys.stdout.flush()
    print("\nAPI timeout!")
    return False

def add_cameras():
    print("\nAdding cameras...")
    for cam_config in CAMERAS:
        try:
            # Check if exists (optional, but good for idempotency if name unique, 
            # here we assume fresh start so we just post)
            response = requests.post(f"{API_URL}/cameras", json=cam_config)
            if response.status_code in [200, 201]:
                print(f"Successfully added: {cam_config['name']}")
            else:
                print(f"Failed to add {cam_config['name']}: {response.text}")
        except Exception as e:
            print(f"Error adding {cam_config['name']}: {e}")

if __name__ == "__main__":
    if wait_for_api():
        add_cameras()
    else:
        sys.exit(1)
