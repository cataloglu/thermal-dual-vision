"""
WebSocket service for Smart Motion Detector v2.

Handles real-time event and status updates via WebSocket connections.
"""
import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket
import asyncio


logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    WebSocket connection manager.
    
    Manages active WebSocket connections and broadcasts messages
    to all connected clients.
    """
    
    def __init__(self):
        """Initialize WebSocket manager."""
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
        logger.info("WebSocketManager initialized")
    
    async def connect(self, websocket: WebSocket):
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection to register
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: WebSocket connection to remove
        """
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast_event(self, event_data: Dict[str, Any]):
        """
        Broadcast event to all connected clients.
        
        Args:
            event_data: Event data to broadcast
        """
        message = {
            "type": "event",
            "data": event_data
        }
        
        await self._broadcast(message)
        logger.debug(f"Broadcasted event: {event_data.get('id', 'unknown')}")
    
    async def broadcast_status(self, status_data: Dict[str, Any]):
        """
        Broadcast system status to all connected clients.
        
        Args:
            status_data: Status data to broadcast
        """
        message = {
            "type": "status",
            "data": status_data
        }
        
        await self._broadcast(message)
        logger.debug("Broadcasted status update")

    def broadcast_event_sync(self, event_data: Dict[str, Any]) -> None:
        self._run_async(self.broadcast_event(event_data))

    def broadcast_status_sync(self, status_data: Dict[str, Any]) -> None:
        self._run_async(self.broadcast_status(status_data))

    def _run_async(self, coro: asyncio.Future) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            asyncio.run(coro)
    
    async def _broadcast(self, message: Dict[str, Any]):
        """
        Send message to all connected clients.
        
        Args:
            message: Message to broadcast
        """
        if not self.active_connections:
            return
        
        # Convert message to JSON
        message_json = json.dumps(message)
        
        # Send to all connections
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Failed to send message to client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        if disconnected:
            async with self._lock:
                for connection in disconnected:
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)
            logger.info(f"Removed {len(disconnected)} disconnected clients")
    
    async def send_to_client(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Send message to a specific client.
        
        Args:
            websocket: Target WebSocket connection
            message: Message to send
        """
        try:
            message_json = json.dumps(message)
            await websocket.send_text(message_json)
        except Exception as e:
            logger.error(f"Failed to send message to client: {e}")
            await self.disconnect(websocket)


# Global singleton instance
_websocket_manager: WebSocketManager | None = None


def get_websocket_manager() -> WebSocketManager:
    """
    Get or create the global WebSocket manager instance.
    
    Returns:
        WebSocketManager: Global WebSocket manager instance
    """
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager
