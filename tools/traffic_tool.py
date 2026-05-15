import httpx
import structlog
from core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

KARACHI_SEGMENTS = {
    "University Road":  {"segment_id": "kar_uni_001", "lat": 24.9420, "lng": 67.1099},
    "DHA":              {"segment_id": "kar_dha_001", "lat": 24.8116, "lng": 67.0598},
    "Gulshan":          {"segment_id": "kar_gul_001", "lat": 24.9271, "lng": 67.0837},
    "Nazimabad":        {"segment_id": "kar_naz_001", "lat": 24.9167, "lng": 67.0375},
    "Saddar":           {"segment_id": "kar_sad_001", "lat": 24.8555, "lng": 67.0104},
    "Korangi":          {"segment_id": "kar_kor_001", "lat": 24.8324, "lng": 67.1235},
    "Malir":            {"segment_id": "kar_mal_001", "lat": 24.8889, "lng": 67.2026},
    "North Karachi":    {"segment_id": "kar_nk_001",  "lat": 24.9805, "lng": 67.0633},
    "Orangi Town":      {"segment_id": "kar_ori_001", "lat": 24.9619, "lng": 66.9944},
    "Lyari":            {"segment_id": "kar_lya_001", "lat": 24.8726, "lng": 67.0174},
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
                "unit": "KMPH",
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
