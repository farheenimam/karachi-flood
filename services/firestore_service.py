import structlog
from datetime import datetime
from typing import Any

from core.config import get_settings
from core.state import WorkflowState

logger = structlog.get_logger()
settings = get_settings()

# In-memory store when Firestore is not configured (simulation mode)
_mem_store: dict[str, list] = {
    "incidents": [],
    "reasoning_traces": [],
    "alerts": [],
    "simulations": [],
    "agent_logs": [],
    "live_status": [],
}

_db = None


def _get_db():
    global _db
    if _db:
        return _db

    if settings.simulation_mode or not settings.firebase_project_id:
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.firebase_credentials_path)
            firebase_admin.initialize_app(cred)

        _db = firestore.client()
        logger.info("firestore_connected", project=settings.firebase_project_id)
        return _db
    except Exception as e:
        logger.warning("firestore_init_failed", error=str(e))
        return None


async def save_incident(incident_data: dict) -> str:
    db = _get_db()
    doc_id = incident_data.get("incident_id", "unknown")

    if db:
        try:
            db.collection("incidents").document(doc_id).set(incident_data)
        except Exception as e:
            logger.error("firestore_save_incident_failed", error=str(e))
    else:
        _mem_store["incidents"].append(incident_data)

    logger.info("incident_saved", incident_id=doc_id)
    return doc_id


async def save_plan(plan_data: dict) -> str:
    db = _get_db()
    doc_id = plan_data.get("incident_id", "unknown")

    if db:
        try:
            db.collection("simulations").document(doc_id).set(plan_data)
        except Exception as e:
            logger.error("firestore_save_plan_failed", error=str(e))
    else:
        _mem_store["simulations"].append(plan_data)

    return doc_id


async def save_alert(alert_data: dict) -> str:
    db = _get_db()
    doc_id = alert_data.get("incident_id", "unknown")

    if db:
        try:
            db.collection("alerts").document(doc_id).set(alert_data)
        except Exception as e:
            logger.error("firestore_save_alert_failed", error=str(e))
    else:
        _mem_store["alerts"].append(alert_data)

    return doc_id


async def save_trace(state: WorkflowState) -> str:
    db = _get_db()
    trace_data = state.to_dict()

    if db:
        try:
            db.collection("reasoning_traces").document(state.session_id).set(trace_data)
        except Exception as e:
            logger.error("firestore_save_trace_failed", error=str(e))
    else:
        _mem_store["reasoning_traces"].append(trace_data)

    return state.session_id


async def log_agent_event(agent: str, event: str, data: Any = None):
    db = _get_db()
    log_entry = {
        "agent": agent,
        "event": event,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if db:
        try:
            db.collection("agent_logs").add(log_entry)
        except Exception as e:
            logger.error("firestore_log_failed", error=str(e))
    else:
        _mem_store["agent_logs"].append(log_entry)


async def get_all_incidents() -> list:
    db = _get_db()
    if db:
        try:
            docs = db.collection("incidents").order_by("timestamp", direction="DESCENDING").limit(50).stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error("firestore_get_incidents_failed", error=str(e))
    return list(reversed(_mem_store["incidents"][-50:]))


async def get_all_alerts() -> list:
    db = _get_db()
    if db:
        try:
            docs = db.collection("alerts").stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error("firestore_get_alerts_failed", error=str(e))
    return list(reversed(_mem_store["alerts"][-50:]))


async def get_all_traces() -> list:
    db = _get_db()
    if db:
        try:
            docs = db.collection("reasoning_traces").order_by("started_at", direction="DESCENDING").limit(20).stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error("firestore_get_traces_failed", error=str(e))
    return list(reversed(_mem_store["reasoning_traces"][-20:]))


def get_memory_store_summary() -> dict:
    return {
        col: len(items) for col, items in _mem_store.items()
    }
