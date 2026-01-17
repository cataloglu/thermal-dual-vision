"""WebSocket handler for real-time event streaming."""

from typing import Any, Dict, List, Optional, Callable
from flask import request
from flask_socketio import SocketIO, emit, disconnect

from src.logger import get_logger

logger = get_logger("websocket")

# Global SocketIO instance (will be initialized by create_app)
socketio: Optional[SocketIO] = None


class WebSocketManager:
    """
    WebSocket manager for real-time event broadcasting.

    Handles client connections, disconnections, and event broadcasting
    for motion detection events and system status updates.
    """

    def __init__(self, socketio_instance: SocketIO) -> None:
        """
        Initialize WebSocket manager.

        Args:
            socketio_instance: Flask-SocketIO instance
        """
        self.socketio = socketio_instance
        self._connected_clients: List[str] = []
        self._event_callbacks: List[Callable] = []

        logger.info("WebSocket manager initialized")

    def get_connected_clients_count(self) -> int:
        """
        Get the number of currently connected clients.

        Returns:
            Number of connected clients
        """
        return len(self._connected_clients)

    def broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Broadcast event to all connected clients.

        Args:
            event_type: Type of event (e.g., 'motion_detected', 'system_status')
            data: Event data payload
        """
        try:
            logger.debug(f"Broadcasting event: {event_type} to {len(self._connected_clients)} clients")
            self.socketio.emit(event_type, data, namespace='/events')
            logger.info(f"Event broadcasted: {event_type}")
        except Exception as e:
            logger.error(f"Failed to broadcast event {event_type}: {e}")

    def broadcast_motion_event(self, event_data: Dict[str, Any]) -> None:
        """
        Broadcast motion detection event to all connected clients.

        Args:
            event_data: Motion event data including timestamp, confidence, analysis, etc.
        """
        self.broadcast_event('motion_detected', event_data)

    def broadcast_status_update(self, status_data: Dict[str, Any]) -> None:
        """
        Broadcast system status update to all connected clients.

        Args:
            status_data: System status data including component states
        """
        self.broadcast_event('status_update', status_data)

    def on_client_connect(self, sid: str) -> None:
        """
        Handle client connection.

        Args:
            sid: Session ID of the connected client
        """
        if sid not in self._connected_clients:
            self._connected_clients.append(sid)
        logger.info(f"Client connected: {sid} (total: {len(self._connected_clients)})")

    def on_client_disconnect(self, sid: str) -> None:
        """
        Handle client disconnection.

        Args:
            sid: Session ID of the disconnected client
        """
        if sid in self._connected_clients:
            self._connected_clients.remove(sid)
        logger.info(f"Client disconnected: {sid} (total: {len(self._connected_clients)})")


# Global WebSocket manager instance
ws_manager: Optional[WebSocketManager] = None


def init_socketio(app) -> SocketIO:
    """
    Initialize Flask-SocketIO with the Flask app.

    Args:
        app: Flask application instance

    Returns:
        Configured SocketIO instance
    """
    global socketio, ws_manager

    logger.info("Initializing Flask-SocketIO")

    # Create SocketIO instance with CORS support
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",  # Configure based on security requirements
        async_mode='threading',     # Use threading for compatibility
        logger=False,               # Disable SocketIO's default logger
        engineio_logger=False       # Disable Engine.IO's default logger
    )

    # Create WebSocket manager
    ws_manager = WebSocketManager(socketio)

    # Register event handlers
    register_handlers(socketio)

    logger.info("Flask-SocketIO initialized successfully")

    return socketio


def register_handlers(socketio_instance: SocketIO) -> None:
    """
    Register WebSocket event handlers.

    Args:
        socketio_instance: Flask-SocketIO instance
    """
    @socketio_instance.on('connect', namespace='/events')
    def handle_connect():
        """Handle client connection to /events namespace."""
        client_ip = request.remote_addr
        sid = request.sid
        logger.info(f"Client connecting from {client_ip} (sid: {sid})")

        if ws_manager:
            ws_manager.on_client_connect(sid)

        # Send welcome message
        emit('connected', {
            'message': 'Connected to Smart Motion Detector event stream',
            'sid': sid
        })

    @socketio_instance.on('disconnect', namespace='/events')
    def handle_disconnect():
        """Handle client disconnection from /events namespace."""
        sid = request.sid
        logger.info(f"Client disconnecting (sid: {sid})")

        if ws_manager:
            ws_manager.on_client_disconnect(sid)

    @socketio_instance.on('ping', namespace='/events')
    def handle_ping():
        """Handle ping from client (for connection keepalive)."""
        emit('pong', {'timestamp': request.sid})

    @socketio_instance.on_error(namespace='/events')
    def handle_error(e):
        """Handle WebSocket errors."""
        logger.error(f"WebSocket error: {e}")

    logger.debug("WebSocket event handlers registered")


def get_ws_manager() -> Optional[WebSocketManager]:
    """
    Get the global WebSocket manager instance.

    Returns:
        WebSocketManager instance or None if not initialized
    """
    return ws_manager
