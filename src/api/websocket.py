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

        logger.info("WebSocket manager initialized")

    def get_connected_clients_count(self) -> int:
        """
        Get the number of currently connected clients.

        Returns:
            Number of connected clients
        """
        return len(self._connected_clients)

    @property
    def has_clients(self) -> bool:
        """
        Check if there are any connected clients.

        Returns:
            True if at least one client is connected, False otherwise
        """
        return len(self._connected_clients) > 0

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

    def publish_motion(
        self, detected: bool, analysis: Optional[Any] = None
    ) -> None:
        """
        Publish motion detection event and analysis results to WebSocket clients.

        This method is called by the detection system when motion is detected.
        It broadcasts the event to all connected WebSocket clients.

        Args:
            detected: Motion detected flag
            analysis: Optional analysis result from LLM (AnalysisResult type when available)
        """
        try:
            # Build event data payload
            event_data: Dict[str, Any] = {
                'detected': detected,
                'timestamp': None,
            }

            # Add analysis results if available
            if analysis is not None:
                # Extract analysis data
                if hasattr(analysis, 'timestamp'):
                    event_data['timestamp'] = str(analysis.timestamp)

                if hasattr(analysis, 'real_motion'):
                    event_data['real_motion'] = analysis.real_motion

                if hasattr(analysis, 'confidence'):
                    # Convert confidence to percentage if needed
                    confidence_value = analysis.confidence
                    if isinstance(confidence_value, float) and confidence_value <= 1.0:
                        confidence_value = int(confidence_value * 100)
                    event_data['confidence'] = confidence_value

                if hasattr(analysis, 'description'):
                    event_data['description'] = analysis.description

                if hasattr(analysis, 'detected_objects'):
                    event_data['detected_objects'] = analysis.detected_objects

                if hasattr(analysis, 'threat_level'):
                    event_data['threat_level'] = analysis.threat_level

                if hasattr(analysis, 'recommended_action'):
                    event_data['recommended_action'] = analysis.recommended_action

                if hasattr(analysis, 'detailed_analysis'):
                    event_data['detailed_analysis'] = analysis.detailed_analysis

                if hasattr(analysis, 'processing_time'):
                    event_data['processing_time'] = analysis.processing_time

            # Broadcast to all connected WebSocket clients
            logger.debug(
                f"Publishing motion event (detected={detected}) to "
                f"{len(self._connected_clients)} WebSocket clients"
            )
            self.broadcast_motion_event(event_data)
            logger.info(f"Successfully published motion event (detected={detected})")

        except Exception as e:
            logger.error(f"Failed to publish motion event to WebSocket: {e}")

    def publish_state(self, state_type: str, state: Dict[str, Any]) -> None:
        """
        Publish generic state update to WebSocket clients.

        Broadcasts arbitrary state updates to all connected clients.
        Useful for custom state beyond standard motion/analysis events.

        Args:
            state_type: Type of state update (e.g., "camera_status", "system_health")
            state: State data dictionary to broadcast

        Raises:
            Exception: If broadcasting fails
        """
        try:
            logger.debug(
                f"Publishing state update ({state_type}) to "
                f"{len(self._connected_clients)} WebSocket clients"
            )

            # Broadcast state update
            self.broadcast_event(state_type, state)

            logger.info(f"Successfully published state update: {state_type}")

        except Exception as e:
            logger.error(f"Failed to publish state update ({state_type}): {e}")
            raise


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
