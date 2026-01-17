# Edge Optimization Profiles

This document defines target device classes and optimization profiles for edge deployments.

## Target device classes
- **Class A (Low)**: 2 CPU / 2 GB RAM / SD card
- **Class B (Mid)**: 4 CPU / 4-8 GB RAM / SSD
- **Class C (High)**: 8 CPU / 16 GB RAM / NVMe

## CPU / RAM / IO targets
- **Class A**: CPU < 60%, RAM < 1.2 GB, IO < 10 MB/s
- **Class B**: CPU < 50%, RAM < 2.5 GB, IO < 20 MB/s
- **Class C**: CPU < 40%, RAM < 4.0 GB, IO < 40 MB/s

## Profile parameters
- `camera_fps`
- `motion_sensitivity`
- `motion_min_area`
- `yolo_model`
- `yolo_confidence`
- `screenshot_before_sec` / `screenshot_after_sec`
- `buffer_seconds`
- `telegram_enabled` / `mqtt_discovery`

## Measurement approach
- Collect CPU/RAM/IO with 5-minute averages.
- Run each profile for 30 minutes on target class.
- Track event throughput and average latency.
