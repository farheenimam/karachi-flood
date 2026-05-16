import math
from models.incident import IncidentModel

LOCATION_COORDS = {
    "University Road":  (24.9420, 67.1099),
    "DHA":              (24.8116, 67.0598),
    "Gulshan":          (24.9271, 67.0837),
    "Nazimabad":        (24.9167, 67.0375),
    "Saddar":           (24.8555, 67.0104),
    "Korangi":          (24.8324, 67.1235),
    "Malir":            (24.8889, 67.2026),
    "North Karachi":    (24.9805, 67.0633),
    "Orangi Town":      (24.9619, 66.9944),
    "Lyari":            (24.8726, 67.0174),
}

# Population density estimates (people/km2)
POPULATION_DENSITY = {
    # existing ones stay same, add:
    "Clifton":              6000,
    "PECHS":                20000,
    "Gulistan-e-Johar":     25000,
    "FB Area":              28000,
    "Liaquatabad":          32000,
    "Landhi":               30000,
    "Shah Faisal Colony":   27000,
    "Surjani Town":         29000,
    "Baldia Town":          33000,
    "Kemari":               18000,
    "Garden":               24000,
    "Johar More":           26000,
    "Sohrab Goth":          31000,
    "Superhighway":         10000,
    "Scheme 33":            22000,
    "Bin Qasim":            15000,
    "Model Colony":         28000,
    "New Karachi":          30000,
    "Rashidabad":           25000,
    "Mauripur":             16000,
}

def calculate_geofence(incident: IncidentModel) -> dict:
    """
    Calculate geofence radius and affected area based on severity.
    Returns geofence polygon data and population estimate.
    """
    severity = incident.severity
    location = incident.location

    # Base radius scales with severity (1-10 → 0.5-5 km)
    base_radius_km = 0.5 + (severity / 10) * 4.5

    # Adjust for extreme rainfall signal
    if "weather" in incident.signal_sources:
        base_radius_km *= 1.2

    # Cap at realistic Karachi neighborhood bounds
    radius_km = min(round(base_radius_km, 2), 6.0)

    coords = LOCATION_COORDS.get(location, (24.8607, 67.0011))
    lat, lng = coords

    # Calculate bounding box
    lat_delta = radius_km / 111.0
    lng_delta = radius_km / (111.0 * math.cos(math.radians(lat)))

    area_km2 = math.pi * (radius_km ** 2)
    density = POPULATION_DENSITY.get(location, 20000)
    estimated_population = int(area_km2 * density)

    return {
        "center": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
        "area_km2": round(area_km2, 2),
        "estimated_population": estimated_population,
        "bounding_box": {
            "north": round(lat + lat_delta, 6),
            "south": round(lat - lat_delta, 6),
            "east":  round(lng + lng_delta, 6),
            "west":  round(lng - lng_delta, 6),
        },
    }


def check_overlap(location_a: str, location_b: str, radius_km: float = 3.0) -> bool:
    """Check if two geofences overlap for incident clustering."""
    coords_a = LOCATION_COORDS.get(location_a)
    coords_b = LOCATION_COORDS.get(location_b)
    if not coords_a or not coords_b:
        return False

    distance = _haversine(coords_a[0], coords_a[1], coords_b[0], coords_b[1])
    return distance <= (radius_km * 2)


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
