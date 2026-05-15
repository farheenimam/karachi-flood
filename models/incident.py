from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class IncidentModel(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    location: str
    severity: int = Field(ge=1, le=10)
    confidence: float = Field(ge=0.0, le=1.0)
    signal_sources: list[str]
    event_type: str = "urban_flood"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    raw_signals: Optional[dict] = None
    false_alarm: bool = False


class SignalInput(BaseModel):
    location: str
    weather_data: Optional[dict] = None
    traffic_data: Optional[dict] = None
    social_posts: Optional[list[str]] = None
