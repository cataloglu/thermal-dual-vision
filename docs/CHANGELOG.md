# Changelog

All notable changes to Thermal Dual Vision are documented here.

## v3.10.79 (2026-02-19)

### Fixed
- Added `person_count` DB column migration so existing databases upgrade without errors
- Removed stale `eslint-disable` directive in ZoneEditor
- Resolved all UI audit issues (critical, high, medium, low severity)

---

## v3.10.78 (2026-02-19)

### Fixed
- Live view: switched to 3fps snapshot polling when go2rtc is unavailable — bypasses CDN/proxy buffering issues that caused the live stream to stall

---

## v3.10.77 (2026-02-19)

### Fixed
- Live view: cache go2rtc probe result per camera to avoid hammering go2rtc on repeated checks
- Downgraded noisy debug log levels to reduce log spam

---

## v3.10.76 (2026-02-19)

### Fixed
- Live view: added go2rtc `_detect` stream fallback when main stream is unavailable
- Fixed frontend live view stall after returning to the Live page

---

## v3.10.75 (2026-02-19)

### Fixed
- AI analysis: send box-free collage (no bounding boxes drawn) to OpenAI for independent analysis — prevents YOLO box artifacts from biasing AI judgment

---

## v3.10.74 (2026-02-19)

### Fixed
- AI false confirmation: pass YOLO confidence score to prompt so the model is warned when confidence is low, reducing false positives from AI confirming borderline detections

---

## v3.10.73 (2026-02-19)

### Added
- Parallel event processing: media generation (collage, MP4) and notifications (Telegram, MQTT) now run in parallel threads, reducing total event latency

### Fixed
- Postbuffer sanitizer: fixed hardcoded `15.0s` fallback in media service — now correctly uses `config.event.postbuffer_seconds` (default `5.0s`)

---

## v3.10.71 (2026-02-19)

### Fixed
- Prevent empty video file from overwriting a valid buffer MP4
- UI: improved error handling for failed media operations

---

## v3.10.70 (2026-02-19)

### Fixed
- Multiprocessing (MP) mode: prevent camera disconnects by draining the go2rtc frame buffer at camera FPS, avoiding backpressure accumulation

---

## v3.10.69 (2026-02-19)

### Changed
- Removed pre-AI quick Telegram alert; fast alert path now relies solely on postbuffer reduction
- Reduced default postbuffer latency for faster notification delivery

---

## v3.10.68 (2026-02-19)

### Fixed
- Fixed video loss caused by a failed delayed MP4 replacement overwriting the existing valid file

---

## v3.10.67 (2026-02-18)

### Changed
- Tuned default motion detection presets (sensitivity, min area) for better thermal/color balance
- Improved RTSP reconnect logic for faster camera recovery after network glitches

---

## v3.10.66 (2026-02-18)

### Fixed
- Enabled stall snapshot fallback in the live view: if go2rtc stream stalls, falls back to single-frame JPEG snapshots

---

## v3.10.65 (2026-02-18)

### Fixed
- Fixed collage bounding box scaling — boxes were incorrectly scaled when inference resolution differed from stream resolution

---

## v3.10.64 (2026-02-18)

### Fixed
- Hardened Telegram video sending to handle transient Telegram API errors and retry on failure

---

## v3.10.63 (2026-02-18)

### Fixed
- Allow sending legacy MP4 format (not just accelerated) on Telegram when accelerated version is unavailable

---

## v3.10.62 (2026-02-18)

### Added
- Live snapshot fallback: `GET /api/live/{id}.jpg` returns a single JPEG frame when MJPEG stream fails

---

## v3.10.61 (2026-02-18)

### Changed
- Live view: prefer detector worker frame buffer as fallback before falling back to direct RTSP

---

## v3.10.60 (2026-02-18)

### Changed
- Live view: switched primary fallback to worker frames (lower latency than RTSP reconnect)

---

## v3.10.59 (2026-02-18)

### Added
- Live debug info: `/api/live/{id}.mjpeg?probe=true` returns JSON with source selection details

---

## v3.10.58 (2026-02-18)

### Fixed
- Improved live view fallback detection — more reliable source selection order (go2rtc → worker → RTSP)

---

## v3.10.57 (2026-02-18)

### Fixed
- Fixed startup crash when go2rtc is not yet ready during addon initialization

---

## v3.10.56 (2026-02-18)

### Fixed
- Stabilized live view MJPEG streaming under Home Assistant Ingress proxy — fixed buffering and content-type passthrough issues

---

## v3.10.55 (2026-02-18)

### Fixed
- Multiprocessing mode: added per-camera motion cooldown to prevent motion events from stacking up across processes

---

## v3.10.54 (2026-02-18)

### Changed
- Aligned performance presets; default inference FPS and resolution values tuned for typical hardware

---

## v3.10.53 (2026-02-18)

### Fixed
- Detection resilience improvements: better error recovery when a camera thread crashes
- Various UI fixes for the Settings and Events pages

---

## v3.10.52 (2026-02-17)

### Added
- Motion detection logging: log when motion is detected/suppressed per camera for easier debugging

### Fixed
- go2rtc connection retry logic — now retries with exponential backoff after connection loss

---

## v3.10.51 (2026-02-17)

### Fixed
- Stabilized live MJPEG stream — fixed race condition between go2rtc probe and stream handoff
