import uuid
import structlog
from datetime import datetime

from core.config import get_settings
from core.state import WorkflowState
from models.incident import IncidentModel
from models.plan import PlanModel
from models.action import ActionModel
from tools.alert_tool import create_alert, create_emergency_ticket
from tools.geofence_tool import calculate_geofence

logger = structlog.get_logger()
settings = get_settings()


class ExecutorAgent:
    """
    Converts validated plans into executable emergency actions.
    Uses Gemini to generate smarter, context-aware alert messages.
    """

    def __init__(self):
        self._client = None
        self.model = None
        if settings.gemini_api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=settings.gemini_api_key)
                self.model = "gemini-3-flash-preview"
                logger.info("executor_gemini_ready", model=self.model)
            except Exception as e:
                logger.warning("executor_gemini_init_failed", error=str(e))
        else:
            logger.warning("executor_gemini_skipped", reason="no api key")

    async def _gemini_alert_message(
        self, incident: IncidentModel, plan: PlanModel, fallback: str
    ) -> str:
        if not self._client or settings.simulation_mode:
            return fallback

        routes_text = ""
        if plan.alternative_routes:
            route = plan.alternative_routes[0]
            routes_text = f"Suggested alternate route: {route.name} via {', '.join(route.via)}."

        prompt = f"""You are an emergency alert system for Karachi urban flooding.
Write a short, clear, urgent citizen alert message in simple English (max 2 sentences).
Do not use dramatic language. Be direct and helpful.

Incident details:
- Location: {incident.location}
- Severity: {incident.severity}/10
- Priority: {plan.priority.upper()}
- Affected population: {plan.affected_population:,}
- Estimated delay: {plan.estimated_delay_minutes} minutes
- {routes_text}

Write only the alert message. Nothing else."""

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            message = response.text.strip()
            logger.info("executor_gemini_alert_generated", location=incident.location)
            return message
        except Exception as e:
            logger.warning("executor_gemini_alert_failed", error=str(e))
            return fallback

    async def run(
        self, incident: IncidentModel, plan: PlanModel, state: WorkflowState
    ) -> ActionModel:
        state.current_agent = "executor"
        state.add_trace("Executor", f"Generating actions for incident {incident.incident_id[:8]}")

        actions = []
        ticket_id = None

        # Step 1: Alert creation (fallback message)
        alert_obj = create_alert(incident, plan)
        actions.append("trigger_alert")

        # Step 2: Gemini generates smarter alert message
        smart_message = await self._gemini_alert_message(incident, plan, alert_obj["message"])
        if smart_message != alert_obj["message"]:
            state.add_trace("Executor", f"Gemini alert: {smart_message}")
        else:
            state.add_trace("Executor", f"Alert created: {alert_obj['severity_label']} via {', '.join(alert_obj['channels'])}")

        # Step 3: Rerouting simulation
        if plan.reroute_required:
            actions.append("reroute_traffic")
            route_names = [r.name for r in plan.alternative_routes]
            state.add_trace("Executor",
                f"Reroute simulation activated: {', '.join(route_names) if route_names else 'default bypass'}"
            )

        # Step 4: Emergency ticket
        if incident.severity >= 7:
            ticket = create_emergency_ticket(incident)
            ticket_id = ticket["ticket_id"]
            actions.append("dispatch_ticket")
            state.add_trace("Executor", f"Emergency ticket dispatched: {ticket_id}")

        # Step 5: Emergency ops for critical incidents
        if incident.severity >= 9:
            actions.append("activate_emergency_ops")
            state.add_trace("Executor",
                "Critical severity: activating full emergency operations protocol"
            )

        # Step 6: Geofence warning zone
        geofence = calculate_geofence(incident)
        radius_km = geofence["radius_km"]
        state.add_trace("Executor",
            f"Geofence zone created: {radius_km}km radius around {incident.location}"
        )

        # Step 7: Real-time push
        actions.append("push_live_update")
        state.add_trace("Executor", "Live dashboard update queued via WebSocket")

        sim_id = str(uuid.uuid4())

        action = ActionModel(
            incident_id=incident.incident_id,
            actions=actions,
            alert_message=smart_message,
            geofence_radius_km=radius_km,
            geofence={
                "center_location": incident.location,
                "radius_km": radius_km,
                "lat": geofence["center"]["lat"],
                "lng": geofence["center"]["lng"],
            },
            ticket_id=ticket_id,
            alert_channels=alert_obj["channels"],
            executed_at=datetime.utcnow().isoformat(),
            simulation_id=sim_id,
        )

        state.executor_output = action.model_dump()
        state.add_trace("Executor", f"All actions complete: {', '.join(actions)}")

        logger.info("executor_actions_complete",
            incident_id=incident.incident_id,
            action_count=len(actions),
            ticket_id=ticket_id,
        )

        return action
