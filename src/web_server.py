"""Flask web server with Home Assistant ingress support."""

import os
from typing import Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from api import api_bp
from api.websocket import init_socketio


def create_app() -> Flask:
    """Create and configure Flask application with HA ingress support."""
    app = Flask(__name__, static_folder=None)

    # Enable CORS for development
    CORS(app)

    # Trust proxy headers (required for HA ingress)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())
    app.config['JSON_SORT_KEYS'] = False

    # Home Assistant ingress middleware
    @app.before_request
    def handle_ingress():
        """Handle Home Assistant ingress path prefix."""
        ingress_path = request.headers.get('X-Ingress-Path', '')
        if ingress_path:
            # Store ingress path in request context for use in responses
            request.environ['SCRIPT_NAME'] = ingress_path

    @app.before_request
    def check_ip_whitelist():
        """Verify request comes from allowed IP addresses."""
        allowed_ips = os.getenv('ALLOWED_IPS', '172.30.32.2').split(',')
        allowed_ips = [ip.strip() for ip in allowed_ips]

        # Get real IP from X-Forwarded-For or X-Real-IP headers (for HA ingress)
        client_ip = request.headers.get('X-Forwarded-For', request.headers.get('X-Real-IP', request.remote_addr))
        if client_ip:
            # X-Forwarded-For can contain multiple IPs, take the first one
            client_ip = client_ip.split(',')[0].strip()

        # Allow localhost and Docker networks in development
        dev_mode = os.getenv('DEV_MODE', 'false').lower() == 'true'
        if dev_mode or client_ip in ['127.0.0.1', '::1', 'localhost']:
            return None

        if client_ip not in allowed_ips:
            return jsonify({'error': 'Forbidden', 'message': 'Access denied'}), 403

        return None

    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint for container orchestration."""
        return jsonify({'status': 'ok', 'service': 'motion-detector-web'}), 200

    # Basic info endpoint
    @app.route('/', methods=['GET'])
    def index():
        """Root endpoint with basic service information."""
        return jsonify({
            'service': 'Smart Motion Detector Web Server',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'api': '/api',
                'health': '/health',
                'stream': '/api/stream'
            }
        }), 200

    # Register API Blueprint
    app.register_blueprint(api_bp)

    # Initialize WebSocket support
    socketio = init_socketio(app)

    return app


# Create app instance
app = create_app()

# Get socketio instance for running the app
from api.websocket import socketio


if __name__ == '__main__':
    """Run development server."""
    port = int(os.getenv('WEB_PORT', '8099'))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    print(f"Starting Smart Motion Detector Web Server on port {port}")
    print(f"Debug mode: {debug}")
    print(f"WebSocket endpoint: ws://0.0.0.0:{port}/events")

    # Use socketio.run() instead of app.run() for WebSocket support
    if socketio:
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=debug,
            allow_unsafe_werkzeug=True  # Required for development mode with WebSocket
        )
    else:
        # Fallback to regular Flask if socketio not initialized
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug
        )
