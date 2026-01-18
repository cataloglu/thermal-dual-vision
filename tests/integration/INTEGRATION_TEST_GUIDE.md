# Web UI Integration Test Guide

This guide documents how to test the full integration of the Web UI with Home Assistant ingress support.

## Overview

The integration tests verify:
1. ✅ Frontend loads under ingress path
2. ✅ API calls work with ingress prefix
3. ✅ WebSocket connection works
4. ✅ Live stream displays
5. ✅ Theme toggle persists
6. ✅ SPA routing works correctly

## Prerequisites

- Docker (for containerized testing)
- Python 3.11+ (for local testing)
- Node.js 20+ (for frontend build)
- curl (for API testing)
- wscat (optional, for WebSocket testing)

## Quick Start

### Option 1: Automated Test Script

```bash
# Start the web server
export DEV_MODE=true
export WEB_PORT=8099
python src/web_server.py &

# Wait for server to start
sleep 3

# Run integration tests
./tests/integration/verify_integration.sh
```

### Option 2: Docker Build Test

```bash
# Build Docker image with frontend
docker build -t motion-detector-web-test .

# Run container
docker run -p 8099:8099 -e DEV_MODE=true motion-detector-web-test

# In another terminal, run integration tests
./tests/integration/verify_integration.sh
```

### Option 3: Python Pytest

```bash
# Install test dependencies
pip install pytest requests

# Run integration tests
pytest tests/integration/test_web_ui_integration.py -v
```

## Manual Verification Steps

### 1. Start Web Server with Ingress Path

```bash
export DEV_MODE=true
export WEB_PORT=8099
export ALLOWED_IPS=172.30.32.2
python src/web_server.py
```

Expected output:
```
Starting Smart Motion Detector Web Server on port 8099
Debug mode: False
WebSocket endpoint: ws://0.0.0.0:8099/events
```

### 2. Verify Frontend Loads Under Ingress Path

```bash
curl -H 'X-Ingress-Path: /api/hassio_ingress/test123' \
     -H 'X-Forwarded-For: 172.30.32.2' \
     http://localhost:8099/
```

Expected: HTML content with `<div id="app">`

**Browser Test:**
```bash
# Open browser to http://localhost:8099
# Should see the Web UI dashboard
```

### 3. Test API Calls Work with Ingress Prefix

```bash
# Test status endpoint
curl -H 'X-Ingress-Path: /api/hassio_ingress/test123' \
     -H 'X-Forwarded-For: 172.30.32.2' \
     http://localhost:8099/api/status

# Test stats endpoint
curl -H 'X-Ingress-Path: /api/hassio_ingress/test123' \
     -H 'X-Forwarded-For: 172.30.32.2' \
     http://localhost:8099/api/stats

# Test events endpoint
curl -H 'X-Ingress-Path: /api/hassio_ingress/test123' \
     -H 'X-Forwarded-For: 172.30.32.2' \
     http://localhost:8099/api/events

# Test config endpoint
curl -H 'X-Ingress-Path: /api/hassio_ingress/test123' \
     -H 'X-Forwarded-For: 172.30.32.2' \
     http://localhost:8099/api/config
```

Expected: JSON responses with appropriate data

### 4. Test WebSocket Connection Works

**Using wscat:**
```bash
# Install wscat
npm install -g wscat

# Connect to WebSocket
wscat -c 'ws://localhost:8099/socket.io/?EIO=4&transport=websocket'
```

Expected: Connection established, receives messages

**Using Browser Console:**
```javascript
// Open http://localhost:8099 in browser
// Open browser console and run:
const socket = io('/events');
socket.on('connect', () => console.log('Connected'));
socket.on('motion_detected', (data) => console.log('Motion:', data));
socket.on('status_update', (data) => console.log('Status:', data));
```

### 5. Test Live Stream Displays

```bash
# Test MJPEG stream endpoint
curl -N -H 'X-Ingress-Path: /api/hassio_ingress/test123' \
     -H 'X-Forwarded-For: 172.30.32.2' \
     http://localhost:8099/api/stream --max-time 5
```

Expected: multipart/x-mixed-replace stream with JPEG frames

**Browser Test:**
```bash
# Open http://localhost:8099/live
# Should see live camera stream (or placeholder if camera not configured)
```

### 6. Test Theme Toggle Persists

**Browser Test:**
1. Open http://localhost:8099
2. Click the sun/moon icon in the header to toggle theme
3. Check browser localStorage:
   ```javascript
   localStorage.getItem('theme')  // Should be 'light' or 'dark'
   ```
4. Refresh the page
5. Verify theme persists

**Verification:**
- Theme should switch between light and dark
- Theme should persist after page refresh
- System preference should be respected on first load

### 7. Test All Pages Load

Visit each page and verify it loads:
- http://localhost:8099/ (Dashboard)
- http://localhost:8099/live (Live View)
- http://localhost:8099/gallery (Gallery)
- http://localhost:8099/events (Events)
- http://localhost:8099/settings (Settings)

All routes should serve the frontend app and display appropriate content.

### 8. Test SPA Routing

```bash
# All these routes should return index.html (not 404)
curl -s http://localhost:8099/dashboard | grep "div id=\"app\""
curl -s http://localhost:8099/live | grep "div id=\"app\""
curl -s http://localhost:8099/gallery | grep "div id=\"app\""
curl -s http://localhost:8099/events | grep "div id=\"app\""
curl -s http://localhost:8099/settings | grep "div id=\"app\""
curl -s http://localhost:8099/unknown-route | grep "div id=\"app\""
```

### 9. Test Responsive Design

**Browser Test:**
1. Open http://localhost:8099
2. Open browser dev tools (F12)
3. Toggle device toolbar (Ctrl+Shift+M)
4. Test at different widths:
   - 320px (mobile)
   - 768px (tablet)
   - 1920px (desktop)
5. Verify:
   - Sidebar collapses on mobile
   - Cards stack properly
   - Tables are scrollable on small screens
   - No horizontal overflow

### 10. Test IP Whitelist

**With Allowed IP:**
```bash
curl -H 'X-Forwarded-For: 172.30.32.2' \
     http://localhost:8099/api/status
```
Expected: 200 OK with JSON response

**With Blocked IP (if DEV_MODE=false):**
```bash
curl -H 'X-Forwarded-For: 192.168.1.100' \
     http://localhost:8099/api/status
```
Expected: 403 Forbidden (unless DEV_MODE=true)

## Expected Results Summary

| Test | Expected Result |
|------|----------------|
| Frontend loads | HTML with `<div id="app">` |
| API endpoints | JSON responses with correct data |
| WebSocket | Connection established, events received |
| MJPEG stream | multipart/x-mixed-replace stream |
| Theme toggle | Theme switches and persists in localStorage |
| SPA routing | All routes serve index.html |
| Static assets | CSS/JS files served correctly |
| IP whitelist | Blocked IPs return 403 |
| Health check | Returns `{"status": "ok"}` |
| CORS | Access-Control headers present |

## Troubleshooting

### Frontend doesn't load
- Check that `web/dist/` directory exists
- Run `cd web && npm run build` to build frontend
- Verify Flask is serving from correct static_folder

### API endpoints return 403
- Check X-Forwarded-For header includes whitelisted IP (172.30.32.2)
- Enable DEV_MODE for local testing: `export DEV_MODE=true`

### WebSocket doesn't connect
- Verify Flask-SocketIO is installed: `pip install flask-socketio`
- Check that socketio.run() is used instead of app.run()
- Test Socket.IO endpoint: `curl http://localhost:8099/socket.io/`

### Stream doesn't display
- Verify camera is configured and accessible
- Check /api/stream endpoint returns multipart/x-mixed-replace
- Test in browser that supports MJPEG streaming

### Theme doesn't persist
- Check browser localStorage is enabled
- Verify ThemeProvider component is wrapped around App
- Check for JavaScript errors in browser console

## Performance Verification

### Bundle Size
```bash
cd web
npm run build
ls -lh dist/assets/*.js
# Should be <100KB gzipped
```

### Lighthouse Score
```bash
# Install Lighthouse
npm install -g lighthouse

# Run Lighthouse test
lighthouse http://localhost:8099 --view
# Performance score should be >90
```

## Docker Build Verification

```bash
# Build image
docker build -t motion-detector-web-test .

# Verify frontend assets are copied
docker run --rm motion-detector-web-test ls -la /app/web/dist/

# Should show:
# index.html
# assets/index-*.js
# assets/index-*.css
```

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test-web-ui.yml
name: Test Web UI Integration

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build Docker image
        run: docker build -t test-web-ui .
      - name: Run container
        run: docker run -d -p 8099:8099 -e DEV_MODE=true test-web-ui
      - name: Wait for server
        run: sleep 5
      - name: Run integration tests
        run: ./tests/integration/verify_integration.sh
```

## Success Criteria

All tests must pass:
- ✅ Frontend builds without errors
- ✅ Bundle size <100KB gzipped
- ✅ All API endpoints return correct responses
- ✅ WebSocket connections work
- ✅ MJPEG stream displays
- ✅ Theme toggles and persists
- ✅ SPA routing works
- ✅ IP whitelist enforced
- ✅ Ingress path handling works
- ✅ Responsive design verified
- ✅ No console errors in browser
- ✅ Health check passes
- ✅ CORS headers present

## Next Steps

After all tests pass:
1. Deploy to Home Assistant as add-on
2. Test with real Home Assistant ingress
3. Verify SSL/TLS works with HA proxy
4. Test with real camera feed
5. Perform load testing with multiple clients
6. Monitor WebSocket connection stability
