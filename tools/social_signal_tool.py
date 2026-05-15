import re
import structlog
from dataclasses import dataclass

logger = structlog.get_logger()

# Roman Urdu flood signal patterns and their weights
FLOOD_SIGNALS = {
    # Direct water/flood mentions
    "pani bhar gaya":      {"weight": 0.95, "type": "flooding"},
    "pani aa gaya":        {"weight": 0.90, "type": "flooding"},
    "pani zyada hai":      {"weight": 0.85, "type": "flooding"},
    "sab doob gaya":       {"weight": 0.95, "type": "flooding"},
    "ghar mein pani":      {"weight": 0.90, "type": "flooding"},
    "barish ka pani":      {"weight": 0.80, "type": "flooding"},

    # Road/traffic blocks
    "road block hai":      {"weight": 0.85, "type": "road_block"},
    "rasta band hai":      {"weight": 0.85, "type": "road_block"},
    "raasta band":         {"weight": 0.80, "type": "road_block"},
    "road jam":            {"weight": 0.70, "type": "road_block"},
    "traffic jam":         {"weight": 0.60, "type": "road_block"},

    # Vehicle stranded
    "gari phas gayi":      {"weight": 0.90, "type": "vehicle_stranded"},
    "gari doob gayi":      {"weight": 0.95, "type": "vehicle_stranded"},
    "gari nahi chal rahi": {"weight": 0.75, "type": "vehicle_stranded"},

    # Heavy rain mentions
    "bohot zyada barish":  {"weight": 0.85, "type": "heavy_rain"},
    "barish ruk nahi rahi":{"weight": 0.80, "type": "heavy_rain"},
    "tez barish":          {"weight": 0.75, "type": "heavy_rain"},
    "barish bahut hai":    {"weight": 0.75, "type": "heavy_rain"},

    # Emergency/help
    "madad karo":          {"weight": 0.80, "type": "emergency"},
    "help chahiye":        {"weight": 0.75, "type": "emergency"},
    "rescue chahiye":      {"weight": 0.90, "type": "emergency"},
    "koi rescue":          {"weight": 0.85, "type": "emergency"},
    "bachao":              {"weight": 0.90, "type": "emergency"},

    # Negative/false alarm indicators
    "thodi barish":        {"weight": -0.3, "type": "false_alarm"},
    "sab theek hai":       {"weight": -0.5, "type": "false_alarm"},
    "barish band ho gayi": {"weight": -0.2, "type": "false_alarm"},
}

# Known Karachi locations in Roman Urdu text
LOCATION_PATTERNS = [
    r'\b(university road|uni road)\b',
    r'\b(dha|defence)\b',
    r'\b(gulshan|gulshan-e-iqbal)\b',
    r'\b(nazimabad)\b',
    r'\b(saddar)\b',
    r'\b(korangi)\b',
    r'\b(malir)\b',
    r'\b(north karachi|nk)\b',
    r'\b(orangi|orangi town)\b',
    r'\b(lyari)\b',
    r'\b(gulistan-e-johar|johar)\b',
    r'\b(clifton)\b',
    r'\b(fb area|federal b)\b',
    r'\b(liaquatabad)\b',
    r'\b(landhi)\b',
]

LOCATION_NORMALIZE = {
    "uni road": "University Road",
    "university road": "University Road",
    "defence": "DHA",
    "dha": "DHA",
    "gulshan-e-iqbal": "Gulshan",
    "gulshan": "Gulshan",
    "north karachi": "North Karachi",
    "nk": "North Karachi",
    "orangi town": "Orangi Town",
    "orangi": "Orangi Town",
    "gulistan-e-johar": "Gulistan-e-Johar",
    "johar": "Gulistan-e-Johar",
    "fb area": "FB Area",
    "federal b": "FB Area",
}


@dataclass
class ParsedSignal:
    text: str
    flood_score: float
    signal_types: list[str]
    extracted_location: str | None
    is_flood_related: bool
    is_false_alarm: bool


async def parse_social_signals(posts: list[str], target_location: str = None) -> dict:
    """
    Parse Roman Urdu social posts for flooding signals.
    Returns aggregated signal strength and location evidence.
    """
    if not posts:
        return _empty_signal(target_location)

    parsed = [_parse_single_post(p) for p in posts]
    flood_posts = [p for p in parsed if p.is_flood_related and not p.is_false_alarm]
    false_alarms = [p for p in parsed if p.is_false_alarm]

    if not flood_posts:
        return {
            "location": target_location,
            "flood_signal_count": 0,
            "false_alarm_count": len(false_alarms),
            "aggregate_score": 0.0,
            "signal_types": [],
            "source": "social_mock",
        }

    avg_score = sum(p.flood_score for p in flood_posts) / len(flood_posts)
    all_types = list({t for p in flood_posts for t in p.signal_types})
    extracted_locations = [p.extracted_location for p in flood_posts if p.extracted_location]

    resolved_location = target_location
    if extracted_locations:
        resolved_location = extracted_locations[0]

    logger.info("social_signals_parsed",
        total=len(posts),
        flood_signals=len(flood_posts),
        false_alarms=len(false_alarms),
        avg_score=round(avg_score, 2),
    )

    return {
        "location": resolved_location,
        "flood_signal_count": len(flood_posts),
        "false_alarm_count": len(false_alarms),
        "aggregate_score": round(avg_score, 3),
        "signal_types": all_types,
        "sample_posts": [p.text for p in flood_posts[:3]],
        "source": "social_mock",
    }


def _parse_single_post(text: str) -> ParsedSignal:
    lower = text.lower().strip()
    score = 0.0
    types = []
    false_alarm = False

    for phrase, meta in FLOOD_SIGNALS.items():
        if phrase in lower:
            w = meta["weight"]
            if w < 0:
                false_alarm = True
                score += w
            else:
                score += w
                types.append(meta["type"])

    score = max(0.0, min(1.0, score))
    location = _extract_location(lower)

    return ParsedSignal(
        text=text,
        flood_score=score,
        signal_types=list(set(types)),
        extracted_location=location,
        is_flood_related=score >= 0.5 and bool(types),
        is_false_alarm=false_alarm,
    )


def _extract_location(text: str) -> str | None:
    for pattern in LOCATION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found = match.group(1).lower().strip()
            return LOCATION_NORMALIZE.get(found, found.title())
    return None


def _empty_signal(location: str | None) -> dict:
    return {
        "location": location,
        "flood_signal_count": 0,
        "false_alarm_count": 0,
        "aggregate_score": 0.0,
        "signal_types": [],
        "source": "social_mock",
    }


# Mock post generator for simulations
def get_mock_posts(location: str) -> list[str]:
    MOCK_DB = {
        "University Road": [
            "University Road pe pani bhar gaya yaar, gari phas gayi",
            "Bohot zyada barish ho rahi hai uni road pe",
            "Road block hai university road, koi alternative batao",
            "Help chahiye university road pe car doob gayi",
        ],
        "Gulshan": [
            "Gulshan block 13 mein pani aa gaya ghar mein",
            "Sab doob gaya gulshan mein, rescue chahiye",
            "Tez barish gulshan mein, rasta band hai",
        ],
        "Korangi": [
            "Korangi mein pani zyada hai bohot, gari nahi chal rahi",
            "Korangi road pe flood aa gaya, madad karo",
            "Bachao korangi mein sab kuch doob raha hai",
        ],
        "DHA": [
            "DHA phase 6 mein thodi barish ho rahi hai",
            "Sab theek hai DHA mein abhi",
        ],
    }
    return MOCK_DB.get(location, [
        f"{location} mein barish ho rahi hai",
        f"Road block hai {location} mein",
    ])
