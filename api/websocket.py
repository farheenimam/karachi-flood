import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_service import ws_manager
import structlog

logger = structlog.get_logger()
ws_router = APIRouter()


@ws_router.websocket("/ws/live-trace")
async def live_trace_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket endpoint.
    Streams agent reasoning traces, incident updates, and alerts.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; handle client pings
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws_manager.send_personal(websocket, {"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("ws_client_disconnected_gracefully")
    except Exception as e:
        logger.warning("ws_error", error=str(e))
        ws_manager.disconnect(websocket)
