import httpx
import structlog
from core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

KARACHI_SEGMENTS = {
    "University Road":      {"lat": 24.9312, "lng": 67.1098},
    "DHA":                  {"lat": 24.8076, "lng": 67.0712},
    "Gulshan":              {"lat": 24.9215, "lng": 67.0908},
    "Nazimabad":            {"lat": 24.9189, "lng": 67.0542},
    "Saddar":               {"lat": 24.8601, "lng": 67.0104},
    "Korangi":              {"lat": 24.8412, "lng": 67.1289},
    "Malir":                {"lat": 24.8935, "lng": 67.1987},
    "North Karachi":        {"lat": 24.9723, "lng": 67.0721},
    "Orangi Town":          {"lat": 24.9501, "lng": 66.9987},
    "Lyari":                {"lat": 24.8689, "lng": 67.0221},
    "Clifton":              {"lat": 24.8126, "lng": 67.0312},
    "PECHS":                {"lat": 24.8721, "lng": 67.0589},
    "Gulistan-e-Johar":     {"lat": 24.9089, "lng": 67.1221},
    "FB Area":              {"lat": 24.9612, "lng": 67.0634},
    "Liaquatabad":          {"lat": 24.9089, "lng": 67.0401},
    "Landhi":               {"lat": 24.8512, "lng": 67.2134},
    "Shah Faisal Colony":   {"lat": 24.8712, "lng": 67.1456},
    "Surjani Town":         {"lat": 25.0123, "lng": 67.0634},
    "Baldia Town":          {"lat": 24.9234, "lng": 66.9789},
    "Kemari":               {"lat": 24.8234, "lng": 66.9789},
    "Garden":               {"lat": 24.8712, "lng": 67.0234},
    "Johar More":           {"lat": 24.9234, "lng": 67.1123},
    "Sohrab Goth":          {"lat": 24.9712, "lng": 67.0789},
    "Superhighway":         {"lat": 24.9923, "lng": 67.1234},
    "Scheme 33":            {"lat": 24.9534, "lng": 67.1456},
    "Bin Qasim":            {"lat": 24.7923, "lng": 67.3012},
    "Model Colony":         {"lat": 24.8923, "lng": 67.1567},
    "New Karachi":          {"lat": 24.9823, "lng": 67.0456},
    "Rashidabad":           {"lat": 24.8634, "lng": 67.0912},
    "Mauripur":             {"lat": 24.8423, "lng": 66.9567},
}
MOCK_TRAFFIC = {
    "University Road": {"congestion_level": 9, "speed_kmh": 5,  "free_flow_speed": 60, "incidents": 3},
    "DHA":             {"congestion_level": 4, "speed_kmh": 35, "free_flow_speed": 60, "incidents": 0},
    "Gulshan":         {"congestion_level": 8, "speed_kmh": 8,  "free_flow_speed": 60, "incidents": 4},
    "Nazimabad":       {"congestion_level": 7, "speed_kmh": 12, "free_flow_speed": 55, "incidents": 2},
    "Saddar":          {"congestion_level": 5, "speed_kmh": 25, "free_flow_speed": 50, "incidents": 1},
    "Korangi":         {"congestion_level": 9, "speed_kmh": 4,  "free_flow_speed": 55, "incidents": 5},
    "Malir":           {"congestion_level": 6, "speed_kmh": 18, "free_flow_speed": 60, "incidents": 2},
    "North Karachi":   {"congestion_level": 5, "speed_kmh": 28, "free_flow_speed": 65, "incidents": 1},
    "Orangi Town":     {"congestion_level": 8, "speed_kmh": 9,  "free_flow_speed": 55, "incidents": 3},
    "Lyari":           {"congestion_level": 6, "speed_kmh": 15, "free_flow_speed": 50, "incidents": 2},
}


async def get_traffic_data(location: str) -> dict:
    """
    Fetch congestion metrics for a Karachi road segment.
    Uses TomTom Traffic API in production; mock in simulation mode.
    """
    if settings.simulation_mode or not settings.tomtom_api_key:
        return _mock_traffic(location)

    seg = KARACHI_SEGMENTS.get(location, {"lat": 24.8607, "lng": 67.0011})
    url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params={
                "key": settings.tomtom_api_key,
                "point": f"{seg['lat']},{seg['lng']}",
            })
            resp.raise_for_status()
            data = resp.json().get("flowSegmentData", {})

            current_speed = data.get("currentSpeed", 30)
            free_flow = data.get("freeFlowSpeed", 60)
            congestion = max(1, min(10, int((1 - current_speed / free_flow) * 10)))

            return {
                "location": location,
                "congestion_level": congestion,
                "speed_kmh": current_speed,
                "free_flow_speed": free_flow,
                "incidents": data.get("incidents", 0),
                "source": "tomtom",
            }
    except Exception as e:
        logger.warning("traffic_api_failed", location=location, error=str(e))
        return _mock_traffic(location)


def _mock_traffic(location: str) -> dict:
    base = MOCK_TRAFFIC.get(location, {"congestion_level": 5, "speed_kmh": 20, "free_flow_speed": 60, "incidents": 1})
    return {
        "location": location,
        "congestion_level": base["congestion_level"],
        "speed_kmh": base["speed_kmh"],
        "free_flow_speed": base["free_flow_speed"],
        "incidents": base["incidents"],
        "source": "mock",
    }
