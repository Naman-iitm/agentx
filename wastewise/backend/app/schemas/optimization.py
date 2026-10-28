"""Optimization run schemas (request + full response)."""
from pydantic import BaseModel, Field

from app.schemas.common import AgentResultOut, RunStatus, UTCDatetime


class OptimizationRunIn(BaseModel):
    depot_id: str
    truck_id: str
    planning_horizon_hours: int = Field(default=12, ge=1, le=72)
    include_predicted_overflow: bool = True


class SelectedBinOut(BaseModel):
    bin_id: str
    name: str
    zone: str
    fill_percent: float
    status: str
    priority: float
    demand_litres: float
    predicted_fill_at_horizon: float | None = None
    reasons: list[str] = []


class RouteStopOut(BaseModel):
    sequence: int
    bin_id: str
    name: str
    zone: str
    distance_from_previous_km: float
    demand_litres: float


class BaselineOut(BaseModel):
    method: str
    distance_km: float
    fuel_litres: float
    fuel_cost: float


class RecyclingSummaryOut(BaseModel):
    distribution: dict[str, int]
    recommendations: list[dict]
    diversion_estimate_percent: float | None = None
    note: str = ""


class OptimizationRunOut(BaseModel):
    run_id: str
    status: RunStatus
    solver: str
    algorithm_version: str
    requested_by: str | None = None
    depot_id: str
    truck_id: str
    planning_horizon_hours: int
    bins_evaluated: int
    selected_bins: list[SelectedBinOut]
    stops: list[RouteStopOut]
    unserved_bin_ids: list[str]
    total_distance_km: float
    return_leg_km: float
    estimated_fuel_litres: float
    estimated_fuel_cost: float
    baseline: BaselineOut | None = None
    savings_percent: float | None = None
    warnings: list[str]
    agents: list[AgentResultOut]
    recycling_summary: RecyclingSummaryOut | None = None
    started_at: UTCDatetime
    completed_at: UTCDatetime | None = None
    duration_ms: int = 0


class AgentBriefOut(BaseModel):
    agent_name: str
    status: str
    duration_ms: int
    warnings: list[str] = []


class OptimizationRunListItem(BaseModel):
    run_id: str
    status: RunStatus
    started_at: UTCDatetime
    completed_at: UTCDatetime | None = None
    total_distance_km: float
    estimated_fuel_litres: float
    estimated_fuel_cost: float
    savings_percent: float | None = None
    selected_count: int
    solver: str
    warnings: list[str]
    agents: list[AgentBriefOut]


class RunListOut(BaseModel):
    items: list[OptimizationRunListItem]
    total: int
    limit: int
    offset: int
