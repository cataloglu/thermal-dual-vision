import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.dependencies import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()

_KEEPALIVE_INTERVAL = 30  # seconds between server-side pings
_KEEPALIVE_TIMEOUT = 10   # seconds to wait for pong response


@router.websocket("/api/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time event and status updates."""
    await websocket_manager.connect(websocket)
    try:
        while True:
            try:
                # Wait for client message with a keepalive deadline
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=_KEEPALIVE_INTERVAL + _KEEPALIVE_TIMEOUT,
                )
                logger.debug(f"Received WebSocket message: {data}")
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Client silent for too long — send a server ping to detect dead connections
                try:
                    await asyncio.wait_for(websocket.send_text("ping"), timeout=_KEEPALIVE_TIMEOUT)
                except Exception:
                    logger.info("WebSocket keepalive failed — closing dead connection")
                    break
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    finally:
        await websocket_manager.disconnect(websocket)
