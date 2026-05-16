import json
import structlog
from datetime import datetime

from core.config import get_settings
from core.state import WorkflowState
from models.incident import IncidentModel
from models.plan import PlanModel, RouteModel
from tools.geofence_tool import calculate_geofence
from tools.reroute_tool import get_alternative_routes, estimate_delay_minutes
from tools.weather_tool import get_weather_data
from tools.traffic_tool import get_traffic_data

logger = structlog.get_logger()
settings = get_settings()

PRIORITY_MAP = {
    range(9, 11): "critical",
    range(7, 9):  "high",
    range(4, 7):  "medium",
    range(1, 4):  "low",
}


class PlannerAgent:
    """
    Validates detector incidents via cross-source checks, performs impact
    analysis, estimates population and delay, generates rerouting plans.
    """

    SYSTEM_PROMPT = """You are a flood response planner for Karachi urban emergency management.
Given a detected incident, your job is to:
1. Validate whether the incident is real using multi-source evidence
2. Estimate the affected population
3. Determine if traffic rerouting is needed
4. Prioritize the incident based on severity and density
5. Generate mitigation strategy

Karachi population densities vary widely: Orangi Town ~35k/km2, DHA ~8k/km2.
Respond ONLY with valid JSON. No markdown. No explanation."""

    def __init__(self):
        self._client = None
        self.model = None
        if settings.gemini_api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=settings.gemini_api_key)
                self.model = "gemini-3-flash-preview"
            except Exception:
                pass

    async def run(self, incident: IncidentModel, state: WorkflowState) -> PlanModel | None:
        state.current_agent = "planner"
        state.add_trace("Planner", f"Analyzing incident at {incident.location} (severity: {incident.severity})")

        # Step 1: Cross-validate with fresh data
        is_valid, rejection_reason = await self._validate_incident(incident, state)

        if not is_valid:
            state.add_trace("Planner", f"Incident rejected: {rejection_reason}")
            logger.info("planner_rejected_incident",
                incident_id=incident.incident_id,
                reason=rejection_reason,
            )
            return PlanModel(
                incident_id=incident.incident_id,
                priority="low",
                validated=False,
                affected_population=0,
                reroute_required=False,
                alternative_routes=[],
                estimated_delay_minutes=0,
                rejected_reason=rejection_reason,
            )

        # Step 2: Geofence and population estimate
        state.add_trace("Planner", "Running geofence and population estimation")
        geofence = calculate_geofence(incident)
        estimated_population = geofence["estimated_population"]

        # Step 3: Rerouting decision
        traffic = incident.raw_signals.get("traffic", {}) if incident.raw_signals else {}
        congestion = traffic.get("congestion_level", 5)
        reroute_needed = congestion >= 6 or incident.severity >= 7
        delay_minutes = estimate_delay_minutes(congestion, incident.severity)

        routes: list[RouteModel] = []
        if reroute_needed:
            state.add_trace("Planner", f"Traffic congestion {congestion}/10 requires rerouting")
            routes = get_alternative_routes(incident.location, incident.severity)
            state.add_trace("Planner", f"Generated {len(routes)} alternative routes")

        # Step 4: Priority classification
        priority = self._classify_priority(incident.severity)
        state.add_trace("Planner", f"Incident priority: {priority.upper()}")

        # Step 5: Mitigation strategy (Gemini or rule-based)
        if self._client and not settings.simulation_mode:
            strategy = await self._gemini_strategy(incident, geofence, state)
        else:
            strategy = self._rule_based_strategy(incident, estimated_population)

        plan = PlanModel(
            incident_id=incident.incident_id,
            priority=priority,
            validated=True,
            affected_population=estimated_population,
            reroute_required=reroute_needed,
            alternative_routes=routes,
            estimated_delay_minutes=delay_minutes,
            mitigation_strategy=strategy,
            validation_sources=incident.signal_sources,
        )

        state.planner_output = plan.model_dump()
        state.add_trace("Planner", f"Plan complete: {estimated_population:,} people affected, delay {delay_minutes}min")

        logger.info("planner_plan_created",
            incident_id=incident.incident_id,
            priority=priority,
            population=estimated_population,
        )

        return plan

    async def _validate_incident(
        self, incident: IncidentModel, state: WorkflowState
    ) -> tuple[bool, str]:
        """
        Re-check signals to validate or reject the incident.
        """
        state.add_trace("Planner", "Cross-validating with fresh data sources")

        weather = await get_weather_data(incident.location)
        traffic = await get_traffic_data(incident.location)

        validation_failures = 0
        reasons = []

        if weather.get("rainfall_mm", 0) < 5 and "weather" in incident.signal_sources:
            validation_failures += 1
            reasons.append("weather data does not confirm rainfall")

        if traffic.get("congestion_level", 0) < 3 and "traffic" in incident.signal_sources:
            validation_failures += 1
            reasons.append("traffic data shows normal flow")

        # Self-correction: if low confidence and multiple failures, reject
        if incident.confidence < 0.4 and validation_failures >= 2:
            return False, f"Validation failed: {'; '.join(reasons)}"

        if incident.severity <= 2 and validation_failures >= 1:
            return False, "Severity too low to warrant response"

        state.add_trace("Planner", f"Validation passed with {len(incident.signal_sources)} confirmed sources")
        return True, ""

    async def _gemini_strategy(
        self, incident: IncidentModel, geofence: dict, state: WorkflowState
    ) -> str:
        prompt = f"""Incident at {incident.location}, Karachi.
Severity: {incident.severity}/10
Affected area: {geofence['area_km2']} km2
Population at risk: {geofence['estimated_population']:,}
Signal sources: {', '.join(incident.signal_sources)}

Provide a brief 2-sentence mitigation strategy as plain text."""

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=self.SYSTEM_PROMPT + "\n\n" + prompt,
            )
            return response.text.strip()
        except Exception as e:
            logger.warning("gemini_strategy_failed", error=str(e))
            return self._rule_based_strategy(incident, geofence["estimated_population"])

    def _rule_based_strategy(self, incident: IncidentModel, population: int) -> str:
        if incident.severity >= 9:
            return (
                f"Activate full emergency response for {incident.location}. "
                f"Deploy rescue teams, issue mandatory evacuation for {population:,} residents, "
                "coordinate with PDMA and NDMA."
            )
        if incident.severity >= 7:
            return (
                f"Deploy water pumping units to {incident.location}. "
                f"Issue traffic advisory and alert {population:,} residents via SMS and app notifications."
            )
        if incident.severity >= 4:
            return (
                f"Monitor {incident.location} for escalation. "
                "Alert traffic management for potential diversions."
            )
        return f"Issue weather advisory for {incident.location}. No immediate action required."

    def _classify_priority(self, severity: int) -> str:
        for r, label in PRIORITY_MAP.items():
            if severity in r:
                return label
        return "medium"
