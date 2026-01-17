"""Flask web server with Home Assistant ingress support."""

import os
from typing import Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from api import api_bp
from api.websocket import init_socketio


def create_app() -> Flask:
    """Create and configure Flask application with HA ingress support."""
    # Configure static file serving for frontend
    # In Docker: /app/web/dist/, Local dev: ./web/dist/
    static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'dist')
    app = Flask(__name__,
                static_folder=static_folder,
                static_url_path='/assets')

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

    # Register API Blueprint (must be before catch-all routes)
    app.register_blueprint(api_bp)

    # Serve index.html for root route
    @app.route('/', methods=['GET'])
    def index():
        """Serve frontend index.html."""
        return send_from_directory(app.static_folder, 'index.html')

    # Catch-all route for SPA client-side routing
    # This must be AFTER API blueprint registration to avoid catching API routes
    @app.route('/<path:path>', methods=['GET'])
    def catch_all(path):
        """Serve index.html for all non-API routes (SPA routing)."""
        # Check if file exists in static folder (CSS, JS, images, etc.)
        file_path = os.path.join(app.static_folder, path)
        if os.path.isfile(file_path):
            return send_from_directory(app.static_folder, path)

        # Otherwise serve index.html for client-side routing
        return send_from_directory(app.static_folder, 'index.html')

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
