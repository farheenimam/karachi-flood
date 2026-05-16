import json
import uuid
import structlog
from datetime import datetime

from core.config import get_settings
from core.state import WorkflowState
from models.incident import IncidentModel, SignalInput
from tools.weather_tool import get_weather_data
from tools.traffic_tool import get_traffic_data
from tools.social_signal_tool import parse_social_signals, get_mock_posts

logger = structlog.get_logger()
settings = get_settings()


class DetectorAgent:
    """
    Reads multi-source signals (weather, traffic, social) and detects
    flooding incidents. Assigns severity and confidence scores.
    """

    SYSTEM_PROMPT = """You are a flood detection AI for Karachi, Pakistan.
You analyze weather data, traffic congestion, and social media signals to detect urban flooding events.

Given the signal data, you must:
1. Determine if a real flooding event is occurring
2. Assign a severity score (1-10)
3. Assign a confidence score (0.0-1.0)
4. Classify the event type
5. Identify if this is a false alarm

Karachi context: The city is highly vulnerable to urban flooding during monsoon season.
High-risk areas include Gulshan, Korangi, Orangi Town, University Road, Nazimabad.

Respond with ONLY valid JSON. No explanation. No markdown. Pure JSON only."""

    def __init__(self):
        self.model = None
        if settings.gemini_api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=settings.gemini_api_key)
                self.model = "gemini-3-flash-preview"
            except Exception:
                self._client = None
        else:
            self._client = None

    async def run(self, signal_input: SignalInput, state: WorkflowState) -> IncidentModel | None:
        state.current_agent = "detector"
        state.add_trace("Detector", f"Starting signal analysis for {signal_input.location}")

        # Step 1: Gather signals
        weather = await get_weather_data(signal_input.location)
        traffic = await get_traffic_data(signal_input.location)

        posts = signal_input.social_posts or get_mock_posts(signal_input.location)
        social = await parse_social_signals(posts, signal_input.location)

        state.add_trace("Detector", f"Weather: {weather['intensity']} rainfall ({weather['rainfall_mm']}mm)")
        state.add_trace("Detector", f"Traffic: congestion level {traffic['congestion_level']}/10, {traffic['incidents']} incidents")
        state.add_trace("Detector", f"Social: {social['flood_signal_count']} flood signals (score: {social['aggregate_score']})")

        # Step 2: Fast false-alarm check
        if self._is_obvious_false_alarm(weather, traffic, social):
            state.add_trace("Detector", "Signal strength below threshold. Classifying as false alarm.")
            logger.info("detector_false_alarm", location=signal_input.location)
            return None

        # Step 3: Use Gemini for reasoning (or deterministic fallback)
        if self._client and not settings.simulation_mode:
            incident = await self._gemini_analysis(signal_input.location, weather, traffic, social, state)
        else:
            incident = self._deterministic_analysis(signal_input.location, weather, traffic, social)

        if incident:
            state.add_trace("Detector", f"Incident detected: severity={incident.severity}, confidence={incident.confidence}")
            state.detector_output = incident.model_dump()
            logger.info("detector_incident_created",
                incident_id=incident.incident_id,
                location=incident.location,
                severity=incident.severity,
            )

        return incident

    async def _gemini_analysis(
        self, location: str, weather: dict, traffic: dict, social: dict, state: WorkflowState
    ) -> IncidentModel | None:
        prompt = f"""Analyze these flood signals for {location}, Karachi:

WEATHER: {json.dumps(weather)}
TRAFFIC: {json.dumps(traffic)}
SOCIAL SIGNALS: {json.dumps(social)}

Return JSON:
{{
  "severity": <1-10>,
  "confidence": <0.0-1.0>,
  "signal_sources": <list of active sources>,
  "event_type": "urban_flood",
  "is_false_alarm": <bool>,
  "reasoning": "<brief reasoning>"
}}"""

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=self.SYSTEM_PROMPT + "\n\n" + prompt,
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text)

            if data.get("is_false_alarm"):
                state.add_trace("Detector", f"Gemini classified as false alarm: {data.get('reasoning', '')}")
                return None

            state.add_trace("Detector", f"Gemini reasoning: {data.get('reasoning', 'N/A')}")

            return IncidentModel(
                incident_id=str(uuid.uuid4()),
                location=location,
                severity=int(data["severity"]),
                confidence=float(data["confidence"]),
                signal_sources=data.get("signal_sources", ["weather", "traffic", "social"]),
                event_type=data.get("event_type", "urban_flood"),
                timestamp=datetime.utcnow().isoformat(),
                raw_signals={"weather": weather, "traffic": traffic, "social": social},
            )
        except Exception as e:
            logger.warning("gemini_analysis_failed", error=str(e))
            state.add_trace("Detector", f"Gemini unavailable, using deterministic fallback: {str(e)}")
            return self._deterministic_analysis(location, weather, traffic, social)

    def _deterministic_analysis(
        self, location: str, weather: dict, traffic: dict, social: dict
    ) -> IncidentModel | None:
        """
        Rule-based scoring when Gemini is unavailable.
        """
        score = 0.0
        sources = []

        # Weather score
        rainfall = weather.get("rainfall_mm", 0)
        if rainfall >= 50:
            score += 4.0
            sources.append("weather")
        elif rainfall >= 30:
            score += 2.5
            sources.append("weather")
        elif rainfall >= 10:
            score += 1.0
            sources.append("weather")

        # Traffic score
        congestion = traffic.get("congestion_level", 0)
        if congestion >= 8:
            score += 3.0
            sources.append("traffic")
        elif congestion >= 6:
            score += 2.0
            sources.append("traffic")
        elif congestion >= 4:
            score += 1.0
            sources.append("traffic")

        # Social score
        social_score = social.get("aggregate_score", 0)
        false_alarms = social.get("false_alarm_count", 0)
        if social_score >= 0.7:
            score += 3.0
            sources.append("social")
        elif social_score >= 0.4:
            score += 1.5
            sources.append("social")

        # False alarm penalty
        if false_alarms > 2:
            score -= 1.5

        # Minimum threshold
        if score < 2.0:
            return None

        severity = min(10, max(1, int(score)))
        confidence = min(0.99, score / 10.0 + 0.1 * len(sources))

        return IncidentModel(
            incident_id=str(uuid.uuid4()),
            location=location,
            severity=severity,
            confidence=round(confidence, 2),
            signal_sources=list(set(sources)),
            event_type="urban_flood",
            timestamp=datetime.utcnow().isoformat(),
            raw_signals={"weather": weather, "traffic": traffic, "social": social},
        )

    def _is_obvious_false_alarm(self, weather: dict, traffic: dict, social: dict) -> bool:
        rainfall = weather.get("rainfall_mm", 0)
        congestion = traffic.get("congestion_level", 0)
        social_score = social.get("aggregate_score", 0)
        false_alarms = social.get("false_alarm_count", 0)

        # All three sources show no signal
        no_rain = rainfall < 5
        no_congestion = congestion < 3
        no_social = social_score < 0.2
        many_false_alarms = false_alarms >= 3

        return (no_rain and no_congestion) or (many_false_alarms and social_score < 0.3)
