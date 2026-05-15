from pydantic import BaseModel, Field
from typing import Optional


class RouteModel(BaseModel):
    name: str
    via: list[str]
    estimated_time_minutes: int
    distance_km: float


class PlanModel(BaseModel):
    incident_id: str
    priority: str  # critical | high | medium | low
    validated: bool
    affected_population: int
    reroute_required: bool
    alternative_routes: list[RouteModel] = []
    estimated_delay_minutes: int
    mitigation_strategy: Optional[str] = None
    validation_sources: list[str] = []
    rejected_reason: Optional[str] = None
