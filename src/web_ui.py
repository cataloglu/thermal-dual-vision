"""Web UI for Home Assistant Ingress."""

import asyncio
import base64
import io
import time
from typing import Optional
import cv2
import numpy as np
from aiohttp import web
from src.logger import get_logger

logger = get_logger("web_ui")

# HTML template for the web UI
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Motion Detector</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .header h1 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .status {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        .status-item {
            flex: 1;
            min-width: 200px;
        }
        .status-label {
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }
        .status-value {
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }
        .status-value.online {
            color: #4caf50;
        }
        .status-value.offline {
            color: #f44336;
        }
        .video-container {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .video-wrapper {
            position: relative;
            width: 100%;
            padding-bottom: 56.25%; /* 16:9 aspect ratio */
            background: #000;
            border-radius: 8px;
            overflow: hidden;
        }
        #video-stream {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        .controls {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .controls h2 {
            color: #667eea;
            margin-bottom: 15px;
        }
        .control-group {
            margin-bottom: 15px;
        }
        .control-group label {
            display: block;
            margin-bottom: 5px;
            color: #666;
            font-weight: 500;
        }
        .control-group input,
        .control-group select {
            width: 100%;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 5px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        .control-group input:focus,
        .control-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        .button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
            margin-right: 10px;
        }
        .button:hover {
            background: #5568d3;
        }
        .button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .button.danger {
            background: #f44336;
        }
        .button.danger:hover {
            background: #d32f2f;
        }
        .info-box {
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            margin-top: 20px;
            border-radius: 5px;
        }
        .info-box h3 {
            color: #1976d2;
            margin-bottom: 10px;
        }
        .info-box p {
            color: #555;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎥 Smart Motion Detector</h1>
            <div class="status">
                <div class="status-item">
                    <div class="status-label">Camera Status</div>
                    <div class="status-value" id="camera-status">Checking...</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Motion Detection</div>
                    <div class="status-value" id="motion-status">Active</div>
                </div>
                <div class="status-item">
                    <div class="status-label">FPS</div>
                    <div class="status-value" id="fps-value">--</div>
                </div>
            </div>
        </div>

        <div class="video-container">
            <div class="video-wrapper">
                <img id="video-stream" src="/stream.mjpeg" alt="Live Stream" />
            </div>
        </div>

        <div class="controls">
            <h2>System Information</h2>
            <div class="info-box">
                <h3>About</h3>
                <p>This is a Smart Motion Detector add-on for Home Assistant. It uses RTSP for camera input and provides AI-powered motion detection with YOLO and GPT-4 Vision analysis.</p>
                <p style="margin-top: 10px;"><strong>Features:</strong> Real-time motion detection, object recognition, threat assessment, and MQTT integration for Home Assistant.</p>
            </div>
        </div>
    </div>

    <script>
        let frameCount = 0;
        let lastTime = Date.now();
        
        // Update FPS counter
        function updateFPS() {
            frameCount++;
            const now = Date.now();
            const elapsed = (now - lastTime) / 1000;
            
            if (elapsed >= 1) {
                const fps = Math.round(frameCount / elapsed);
                document.getElementById('fps-value').textContent = fps + ' fps';
                frameCount = 0;
                lastTime = now;
            }
        }
        
        // Check camera status
        async function checkStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                const statusEl = document.getElementById('camera-status');
                if (data.connected) {
                    statusEl.textContent = 'Connected';
                    statusEl.className = 'status-value online';
                } else {
                    statusEl.textContent = 'Disconnected';
                    statusEl.className = 'status-value offline';
                }
            } catch (error) {
                console.error('Status check failed:', error);
                const statusEl = document.getElementById('camera-status');
                statusEl.textContent = 'Error';
                statusEl.className = 'status-value offline';
            }
        }
        
        // Image load handler for FPS calculation
        const img = document.getElementById('video-stream');
        img.addEventListener('load', updateFPS);
        img.addEventListener('error', function() {
            this.src = '/stream.mjpeg?t=' + Date.now();
        });
        
        // Refresh status every 5 seconds
        setInterval(checkStatus, 5000);
        checkStatus();
    </script>
</body>
</html>
"""


class WebUI:
    """Web UI handler for Home Assistant Ingress."""

    def __init__(self, camera_callback) -> None:
        """
        Initialize Web UI handler.

        Args:
            camera_callback: Callback function to get current camera frame
        """
        self.camera_callback = camera_callback
        self._app: Optional[web.Application] = None

    def create_app(self) -> web.Application:
        """
        Create aiohttp web application with routes.

        Returns:
            Configured aiohttp Application
        """
        import os
        
        app = web.Application()
        
        # Get ingress path from environment (Home Assistant Supervisor)
        ingress_entry = os.getenv("SUPERVISOR_INGRESS_ENTRY", "/")
        if not ingress_entry.startswith("/"):
            ingress_entry = "/" + ingress_entry
        if not ingress_entry.endswith("/"):
            ingress_entry = ingress_entry + "/"
        
        # Normalize routes to work with ingress entry point
        # Home Assistant ingress typically uses "/" as entry point
        # Routes are relative to entry point, so we use absolute paths
        base_path = ingress_entry.rstrip("/") if ingress_entry != "/" else ""
        
        # Main UI route
        app.router.add_get(f"{base_path}/", self._handle_index)
        
        # MJPEG stream route
        app.router.add_get(f"{base_path}/stream.mjpeg", self._handle_mjpeg_stream)
        
        # API routes
        app.router.add_get(f"{base_path}/api/status", self._handle_api_status)
        app.router.add_get(f"{base_path}/api/health", self._handle_api_health)
        
        # Also support routes without base path for backward compatibility
        if base_path:
            app.router.add_get("/", self._handle_index)
            app.router.add_get("/stream.mjpeg", self._handle_mjpeg_stream)
            app.router.add_get("/api/status", self._handle_api_status)
            app.router.add_get("/api/health", self._handle_api_health)
        
        self._app = app
        return app

    async def _handle_index(self, request: web.Request) -> web.Response:
        """Handle main UI page request."""
        return web.Response(text=HTML_TEMPLATE, content_type="text/html")

    async def _handle_mjpeg_stream(self, request: web.Request) -> web.StreamResponse:
        """
        Handle MJPEG stream request for live video feed.

        Returns:
            StreamResponse with multipart MJPEG stream
        """
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'multipart/x-mixed-replace; boundary=--jpgboundary'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Pragma'] = 'no-cache'
        
        await response.prepare(request)

        frame_interval = 0.1  # Target ~10 FPS for web stream
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        try:
            while True:
                # Check if client disconnected
                try:
                    if request.transport is None or request.transport.is_closing():
                        logger.debug("Client disconnected from MJPEG stream")
                        break
                except (AttributeError, RuntimeError) as e:
                    logger.debug(f"Client disconnect check failed: {e}")
                    break
                except Exception as e:
                    logger.warning(f"Unexpected error checking client connection: {e}")
                    break
                
                try:
                    frame = self.camera_callback()
                    if frame is not None:
                        # Encode frame to JPEG
                        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                        success, buffer = cv2.imencode('.jpg', frame, encode_param)
                        
                        if success and buffer is not None:
                            try:
                                # Send MJPEG frame
                                frame_header = (
                                    b'--jpgboundary\r\n'
                                    b'Content-Type: image/jpeg\r\n'
                                    b'Content-Length: ' + str(len(buffer)).encode() + b'\r\n\r\n'
                                )
                                await response.write(frame_header)
                                await response.write(buffer.tobytes())
                                await response.write(b'\r\n')
                                
                                consecutive_errors = 0  # Reset error counter
                                
                                # Control frame rate (target ~10 FPS for web stream)
                                await asyncio.sleep(frame_interval)
                            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                                logger.debug(f"Client disconnected during write: {e}")
                                break
                            except Exception as e:
                                logger.error(f"Error writing MJPEG frame: {e}")
                                consecutive_errors += 1
                                if consecutive_errors >= max_consecutive_errors:
                                    logger.error("Too many consecutive errors, closing stream")
                                    break
                                await asyncio.sleep(0.1)
                        else:
                            logger.warning("Failed to encode frame to JPEG")
                            consecutive_errors += 1
                            if consecutive_errors >= max_consecutive_errors:
                                logger.error("Too many consecutive encoding errors, closing stream")
                                break
                            await asyncio.sleep(0.1)
                    else:
                        # No frame available, wait a bit
                        await asyncio.sleep(0.1)
                
                except Exception as e:
                    logger.error(f"Error in MJPEG stream loop: {e}", exc_info=True)
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("Too many consecutive errors, closing stream")
                        break
                    await asyncio.sleep(0.1)

        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            logger.debug(f"Client disconnected: {e}")
        except asyncio.CancelledError:
            logger.debug("MJPEG stream cancelled")
            raise
        except Exception as e:
            logger.error(f"MJPEG stream error: {e}", exc_info=True)
        finally:
            try:
                await response.write_eof()
            except (ConnectionResetError, BrokenPipeError, OSError):
                pass  # Client already disconnected
            except Exception as e:
                logger.debug(f"Error closing stream response: {e}")

    async def _handle_api_status(self, request: web.Request) -> web.Response:
        """Handle API status request."""
        frame = self.camera_callback()
        status = {
            "connected": frame is not None,
            "timestamp": time.time()
        }
        return web.json_response(status)

    async def _handle_api_health(self, request: web.Request) -> web.Response:
        """Handle API health check request."""
        return web.json_response({"status": "ok"})
