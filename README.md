# Karachi Flood Command Center

Multi-agent AI backend for urban flood monitoring and emergency response.

## Architecture

```
karachi-flood-command/
├── main.py                    # FastAPI app entry point
├── requirements.txt
├── .env.example
├── core/
│   ├── config.py              # Environment config
│   ├── orchestrator.py        # Google ADK orchestrator
│   └── state.py               # Workflow state management
├── agents/
│   ├── detector_agent.py      # Flood signal detection
│   ├── planner_agent.py       # Impact analysis & planning
│   └── executor_agent.py      # Action execution
├── tools/
│   ├── weather_tool.py        # Meteosource API
│   ├── traffic_tool.py        # TomTom API
│   ├── social_signal_tool.py  # Roman Urdu signal parsing
│   ├── geofence_tool.py       # Radius calculation
│   ├── reroute_tool.py        # Alternate route generation
│   └── alert_tool.py          # Alert object creation
├── services/
│   ├── firestore_service.py   # Firestore CRUD
│   └── websocket_service.py   # WebSocket manager
├── models/
│   ├── incident.py            # Pydantic models
│   ├── plan.py
│   └── action.py
└── api/
    ├── routes.py              # REST endpoints
    └── websocket.py           # WS endpoints
```

## Agent Flow

```
[Detector Agent]
    ↓ IncidentModel
[Planner Agent]
    ↓ PlanModel
[Executor Agent]
    ↓ ActionModel
[Firestore + WebSocket broadcast]
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in API keys
uvicorn main:app --reload
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /incidents | All stored incidents |
| GET | /alerts | All alerts |
| GET | /traces | Reasoning traces |
| POST | /simulate | Trigger simulation |
| GET | /live-status | System status |
| WS | /ws/live-trace | Live reasoning stream |
