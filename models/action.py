from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class GeofenceModel(BaseModel):
    center_location: str
    radius_km: float
    lat: Optional[float] = None
    lng: Optional[float] = None


class ActionModel(BaseModel):
    incident_id: str
    actions: list[str]
    alert_message: str
    geofence_radius_km: float
    geofence: Optional[GeofenceModel] = None
    ticket_id: Optional[str] = None
    alert_channels: list[str] = ["sms", "app_push", "dashboard"]
    executed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    simulation_id: Optional[str] = None


class SimulateRequest(BaseModel):
    location: str
    rainfall_mm: Optional[float] = None
    congestion_level: Optional[int] = None
    social_posts: Optional[list[str]] = None
