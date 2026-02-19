import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.dependencies import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/api/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time event and status updates."""
    await websocket_manager.connect(websocket)
    try:
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received WebSocket message: {data}")
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    finally:
        await websocket_manager.disconnect(websocket)
