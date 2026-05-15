from models.plan import RouteModel

# Karachi road network alternative routes
ROUTE_ALTERNATIVES = {
    "University Road": [
        RouteModel(
            name="Shahrah-e-Faisal Bypass",
            via=["Nursery", "Shahrah-e-Faisal", "Gulshan Chowrangi"],
            estimated_time_minutes=22,
            distance_km=8.4,
        ),
        RouteModel(
            name="Nagan Chowrangi Route",
            via=["Nagan Chowrangi", "Liaquatabad", "North Karachi"],
            estimated_time_minutes=30,
            distance_km=11.2,
        ),
    ],
    "Gulshan": [
        RouteModel(
            name="Rashid Minhas Road",
            via=["Rashid Minhas Road", "Baloch Colony"],
            estimated_time_minutes=18,
            distance_km=6.5,
        ),
        RouteModel(
            name="Johar-PECHS Route",
            via=["Gulistan-e-Johar", "PECHS", "Shahrah-e-Faisal"],
            estimated_time_minutes=25,
            distance_km=9.1,
        ),
    ],
    "Nazimabad": [
        RouteModel(
            name="Liaquatabad Bypass",
            via=["Liaquatabad", "FB Area", "North Karachi"],
            estimated_time_minutes=20,
            distance_km=7.3,
        ),
    ],
    "Korangi": [
        RouteModel(
            name="Landhi-Malir Route",
            via=["Landhi", "Malir", "Superhighway"],
            estimated_time_minutes=35,
            distance_km=14.0,
        ),
        RouteModel(
            name="Shah Faisal Colony Route",
            via=["Shah Faisal Colony", "Drigh Road"],
            estimated_time_minutes=28,
            distance_km=10.8,
        ),
    ],
    "Orangi Town": [
        RouteModel(
            name="Manghopir Road",
            via=["Manghopir Road", "Hub Chowki Bypass"],
            estimated_time_minutes=25,
            distance_km=9.6,
        ),
    ],
    "Lyari": [
        RouteModel(
            name="Keamari Bypass",
            via=["Keamari Road", "West Wharf"],
            estimated_time_minutes=15,
            distance_km=5.2,
        ),
    ],
    "Saddar": [
        RouteModel(
            name="MA Jinnah Road",
            via=["MA Jinnah Road", "Clifton"],
            estimated_time_minutes=12,
            distance_km=4.5,
        ),
    ],
    "Malir": [
        RouteModel(
            name="Superhighway Route",
            via=["Superhighway", "Scheme 33"],
            estimated_time_minutes=20,
            distance_km=8.0,
        ),
    ],
    "DHA": [
        RouteModel(
            name="Khayaban-e-Hafiz Route",
            via=["Khayaban-e-Hafiz", "Zamzama"],
            estimated_time_minutes=10,
            distance_km=3.8,
        ),
    ],
    "North Karachi": [
        RouteModel(
            name="Sohrab Goth Route",
            via=["Sohrab Goth", "Superhighway"],
            estimated_time_minutes=18,
            distance_km=7.0,
        ),
    ],
}

DEFAULT_ROUTES = [
    RouteModel(
        name="Alternate Main Route",
        via=["City bypass", "Ring road"],
        estimated_time_minutes=30,
        distance_km=10.0,
    )
]


def get_alternative_routes(location: str, severity: int) -> list[RouteModel]:
    """
    Return reroute options based on location and severity.
    Higher severity = more options returned.
    """
    routes = ROUTE_ALTERNATIVES.get(location, DEFAULT_ROUTES)
    if severity >= 8:
        return routes  # All routes
    return routes[:1]  # Just primary alternative


def estimate_delay_minutes(congestion_level: int, severity: int) -> int:
    """Estimate traffic delay based on congestion and flood severity."""
    base_delay = congestion_level * 4
    flood_multiplier = 1.0 + (severity / 10) * 1.5
    return int(base_delay * flood_multiplier)
