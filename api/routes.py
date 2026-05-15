from fastapi import APIRouter, HTTPException
from datetime import datetime

from models.action import SimulateRequest
from models.incident import SignalInput
from core.orchestrator import FloodOrchestrator
from services.firestore_service import (
    get_all_incidents, get_all_alerts, get_all_traces, get_memory_store_summary
)
from tools.social_signal_tool import get_mock_posts

router = APIRouter()
orchestrator = FloodOrchestrator()


@router.get("/incidents")
async def get_incidents():
    """Return all detected flooding incidents."""
    incidents = await get_all_incidents()
    return {"count": len(incidents), "incidents": incidents}


@router.get("/alerts")
async def get_alerts():
    """Return all generated emergency alerts."""
    alerts = await get_all_alerts()
    return {"count": len(alerts), "alerts": alerts}


@router.get("/traces")
async def get_traces():
    """Return all agent reasoning traces."""
    traces = await get_all_traces()
    return {"count": len(traces), "traces": traces}


@router.post("/simulate")
async def simulate(request: SimulateRequest):
    """
    Trigger a full multi-agent workflow simulation.
    Accepts location + optional signal overrides.
    """
    posts = request.social_posts or get_mock_posts(request.location)

    signal_input = SignalInput(
        location=request.location,
        social_posts=posts,
    )

    result = await orchestrator.run_workflow(signal_input)
    return result


@router.get("/live-status")
async def live_status():
    """System health and current agent state."""
    store_summary = get_memory_store_summary()
    return {
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "system": "Karachi Flood Command Center",
        "agents": ["detector", "planner", "executor"],
        "store": store_summary,
        "websocket_connections": 0,  # Updated dynamically by ws_manager
    }
