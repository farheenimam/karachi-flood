import uuid
from datetime import datetime
from models.incident import IncidentModel
from models.plan import PlanModel


SEVERITY_LABELS = {
    range(1, 4):   "LOW",
    range(4, 7):   "MODERATE",
    range(7, 9):   "HIGH",
    range(9, 11):  "CRITICAL",
}

ALERT_TEMPLATES = {
    "CRITICAL": (
        "CRITICAL FLOOD ALERT: Severe urban flooding detected at {location}. "
        "Immediate evacuation recommended. Avoid all roads in the area."
    ),
    "HIGH": (
        "FLOOD WARNING at {location}. Heavy water logging reported. "
        "Avoid travel to this area. Emergency teams en route."
    ),
    "MODERATE": (
        "Flood Advisory: Moderate flooding at {location}. "
        "Use alternate routes. Stay updated."
    ),
    "LOW": (
        "Weather Notice: Minor flooding possible at {location}. "
        "Exercise caution while driving."
    ),
}


def get_severity_label(severity: int) -> str:
    for r, label in SEVERITY_LABELS.items():
        if severity in r:
            return label
    return "MODERATE"


def create_alert(incident: IncidentModel, plan: PlanModel | None = None) -> dict:
    """
    Create a structured emergency alert object.
    """
    severity_label = get_severity_label(incident.severity)
    template = ALERT_TEMPLATES[severity_label]
    message = template.format(location=incident.location)

    # Add reroute info if available
    if plan and plan.reroute_required and plan.alternative_routes:
        first_route = plan.alternative_routes[0]
        message += f" Suggested alternate: {first_route.name} via {', '.join(first_route.via)}."

    channels = ["dashboard"]
    if incident.severity >= 7:
        channels += ["sms", "app_push"]
    if incident.severity >= 9:
        channels += ["emergency_broadcast", "civic_api"]

    actions = ["trigger_alert"]
    if plan and plan.reroute_required:
        actions.append("reroute_traffic")
    if incident.severity >= 7:
        actions.append("dispatch_ticket")
    if incident.severity >= 9:
        actions.append("activate_emergency_ops")

    return {
        "alert_id": str(uuid.uuid4()),
        "incident_id": incident.incident_id,
        "severity_label": severity_label,
        "severity_score": incident.severity,
        "location": incident.location,
        "message": message,
        "channels": channels,
        "actions": actions,
        "created_at": datetime.utcnow().isoformat(),
    }


def create_emergency_ticket(incident: IncidentModel) -> dict:
    return {
        "ticket_id": f"KHI-{str(uuid.uuid4())[:8].upper()}",
        "incident_id": incident.incident_id,
        "location": incident.location,
        "priority": "P1" if incident.severity >= 7 else "P2",
        "assigned_to": "Karachi Emergency Response Team",
        "status": "open",
        "created_at": datetime.utcnow().isoformat(),
    }
