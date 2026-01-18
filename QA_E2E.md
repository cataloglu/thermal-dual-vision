# QA E2E Verification

## Goal
Verify the end-to-end event flow: 5 frames -> collage -> AI (optional) -> Telegram collage + MP4.

## Docker build/run
```
docker build --no-cache -t thermal-dual-vision .
docker run --rm -p 8000:8000 \
  -e CAMERA_TYPE=color \
  -e CAMERA_URL="rtsp://USER:PASS@IP/STREAM" \
  -e MQTT_DISCOVERY=false \
  -e OPENAI_API_KEY="sk-***" \
  -e TELEGRAM_ENABLED=true \
  -e TELEGRAM_BOT_TOKEN="***REDACTED***" \
  -e TELEGRAM_CHAT_ID="123456789" \
  thermal-dual-vision
```

## Health checks
```
curl -i http://localhost:8000/api/health
curl -i http://localhost:8000/ready
curl -i http://localhost:8000/
```

## Event -> collage -> AI -> Telegram
1. Trigger a motion event (use a real RTSP camera or a test feed).
2. Verify events are captured:
```
curl http://localhost:8000/api/screenshots
```
3. Pick the latest `id` and verify media endpoints:
```
curl -I http://localhost:8000/api/screenshots/<id>/collage
curl -I http://localhost:8000/api/screenshots/<id>/clip.mp4
```
4. If `OPENAI_API_KEY` is set, confirm `ai_enabled=true` in `/api/health` and AI analysis appears in UI Event Detail.
5. Telegram should receive:
   - 5-frame collage image
   - 20s MP4 clip with overlays

## UI verification
1. Dashboard shows camera status, pipeline status, and latest event summary.
2. Events page shows detail panel with collage, AI summary, and MP4 playback/download.

## Expected results
- No RTSP usernames/passwords appear in UI or logs.
- `/api/health` and `/ready` return HTTP 200.
- Telegram receives collage + MP4 when enabled.
