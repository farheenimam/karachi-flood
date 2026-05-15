import httpx
import structlog
from core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Karachi location coords
KARACHI_LOCATIONS = {
    "University Road":      {"lat": 24.9420, "lng": 67.1099},
    "DHA":                  {"lat": 24.8116, "lng": 67.0598},
    "Gulshan":              {"lat": 24.9271, "lng": 67.0837},
    "Nazimabad":            {"lat": 24.9167, "lng": 67.0375},
    "Saddar":               {"lat": 24.8555, "lng": 67.0104},
    "Korangi":              {"lat": 24.8324, "lng": 67.1235},
    "Malir":                {"lat": 24.8889, "lng": 67.2026},
    "North Karachi":        {"lat": 24.9805, "lng": 67.0633},
    "Orangi Town":          {"lat": 24.9619, "lng": 66.9944},
    "Lyari":                {"lat": 24.8726, "lng": 67.0174},
}

MOCK_WEATHER = {
    "University Road": {"rainfall_mm": 48.5, "intensity": "heavy", "wind_kmh": 34},
    "DHA":             {"rainfall_mm": 22.1, "intensity": "moderate", "wind_kmh": 20},
    "Gulshan":         {"rainfall_mm": 61.0, "intensity": "extreme", "wind_kmh": 45},
    "Nazimabad":       {"rainfall_mm": 35.4, "intensity": "heavy", "wind_kmh": 28},
    "Saddar":          {"rainfall_mm": 14.2, "intensity": "light", "wind_kmh": 12},
    "Korangi":         {"rainfall_mm": 55.8, "intensity": "extreme", "wind_kmh": 40},
    "Malir":           {"rainfall_mm": 40.0, "intensity": "heavy", "wind_kmh": 33},
    "North Karachi":   {"rainfall_mm": 29.3, "intensity": "moderate", "wind_kmh": 22},
    "Orangi Town":     {"rainfall_mm": 52.1, "intensity": "extreme", "wind_kmh": 38},
    "Lyari":           {"rainfall_mm": 18.7, "intensity": "moderate", "wind_kmh": 15},
}


async def get_weather_data(location: str) -> dict:
    """
    Fetch rainfall and weather data for a Karachi location.
    Uses Meteosource API in production; falls back to mock in simulation mode.
    """
    if settings.simulation_mode or not settings.meteosource_api_key:
        return _mock_weather(location)

    coords = KARACHI_LOCATIONS.get(location, {"lat": 24.8607, "lng": 67.0011})
    url = "https://www.meteosource.com/api/v1/free/point"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params={
                "lat": coords["lat"],
                "lon": coords["lng"],
                "sections": "current",
                "units": "metric",
                "key": settings.meteosource_api_key,
            })
            resp.raise_for_status()
            data = resp.json()

            current = data.get("current", {})
            precipitation = current.get("precipitation", {})
            rainfall_mm = precipitation.get("total", 0.0)

            return {
                "location": location,
                "rainfall_mm": rainfall_mm,
                "intensity": _classify_intensity(rainfall_mm),
                "wind_kmh": current.get("wind", {}).get("speed", 0),
                "source": "meteosource",
            }
    except Exception as e:
        logger.warning("weather_api_failed", location=location, error=str(e))
        return _mock_weather(location)


def _mock_weather(location: str) -> dict:
    base = MOCK_WEATHER.get(location, {"rainfall_mm": 25.0, "intensity": "moderate", "wind_kmh": 18})
    return {
        "location": location,
        "rainfall_mm": base["rainfall_mm"],
        "intensity": base["intensity"],
        "wind_kmh": base["wind_kmh"],
        "source": "mock",
    }


def _classify_intensity(mm: float) -> str:
    if mm >= 50:
        return "extreme"
    if mm >= 30:
        return "heavy"
    if mm >= 10:
        return "moderate"
    return "light"
