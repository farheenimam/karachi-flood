import json
import structlog
from datetime import datetime
from fastapi import WebSocket

logger = structlog.get_logger()


class WebSocketManager:
    """
    Manages active WebSocket connections and broadcasts
    real-time agent reasoning traces and incident updates.
    """

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("ws_client_connected", total=len(self.active_connections))

        # Send welcome pulse
        await self.send_personal(websocket, {
            "type": "system",
            "message": "Connected to Karachi Flood Command Center",
            "timestamp": datetime.utcnow().isoformat(),
        })

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("ws_client_disconnected", total=len(self.active_connections))

    async def send_personal(self, websocket: WebSocket, data: dict):
        try:
            await websocket.send_text(json.dumps(data))
        except Exception as e:
            logger.warning("ws_send_failed", error=str(e))

    async def broadcast(self, data: dict):
        if not self.active_connections:
            return
        message = json.dumps(data)
        disconnected = []
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)

    async def broadcast_trace(self, agent: str, message: str, data: dict = None):
        await self.broadcast({
            "type": "trace",
            "agent": agent,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def broadcast_incident(self, incident_data: dict):
        await self.broadcast({
            "type": "incident",
            "data": incident_data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def broadcast_alert(self, alert_data: dict):
        await self.broadcast({
            "type": "alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def broadcast_status(self, status: str, session_id: str):
        await self.broadcast({
            "type": "workflow_status",
            "status": status,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        })


# Singleton
ws_manager = WebSocketManager()
