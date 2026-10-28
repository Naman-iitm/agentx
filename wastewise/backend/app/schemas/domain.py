"""Forecast, recycling, alert, settings, fleet schemas."""
from pydantic import BaseModel, Field

from app.schemas.common import UTCDatetime

# ---------------------------------------------------------------- forecasts --
class ForecastPointOut(BaseModel):
    target_at: UTCDatetime
    predicted_fill_percent: float
    lower_bound: float
    upper_bound: float


class ForecastOut(BaseModel):
    bin_id: str
    status: str  # ok | insufficient_history
    method: str
    model_version: str
    generated_at: UTCDatetime
    horizon_hours: int
    points: list[ForecastPointOut]
    warnings: list[str] = []
    note: str = ""


# ---------------------------------------------------------------- recycling --
WASTE_CATEGORIES = [
    "ORGANIC",
    "PAPER",
    "PLASTIC",
    "METAL",
    "GLASS",
    "E_WASTE",
    "HAZARDOUS",
    "MIXED",
    "UNKNOWN",
]

HANDLING_RECOMMENDATIONS: dict[str, dict] = {
    "ORGANIC": {
        "recommendation": "Send to composting or biomethanation plant; keep separate from dry waste.",
        "caution": None,
    },
    "PAPER": {
        "recommendation": "Bale and send to paper mill recycler; keep dry.",
        "caution": None,
    },
    "PLASTIC": {
        "recommendation": "Sort by resin code, rinse containers, send to registered plastic recycler.",
        "caution": None,
    },
    "METAL": {
        "recommendation": "Segregate ferrous/non-ferrous; sell to scrap processor.",
        "caution": None,
    },
    "GLASS": {
        "recommendation": "Colour-sort and deliver to cullet processor; avoid breakage in transit.",
        "caution": None,
    },
    "E_WASTE": {
        "recommendation": "Hand over to a CPCB-registered authorised e-waste recycler.",
        "caution": "Never landfill or incinerate.",
    },
    "HAZARDOUS": {
        "recommendation": "Quarantine and route to a authorised hazardous-waste facility (TSDF).",
        "caution": "Requires mandatory human review — this system is not a certified hazardous-waste detector.",
    },
    "MIXED": {
        "recommendation": "Route to a material recovery facility for manual sorting.",
        "caution": None,
    },
    "UNKNOWN": {
        "recommendation": "Manual inspection required before disposal or recycling.",
        "caution": "Low-confidence result — do not auto-route.",
    },
}


class ClassificationIn(BaseModel):
    bin_id: str | None = None
    category: str
    source: str = "operator"
    note: str | None = Field(default=None, max_length=500)
    confidence: float | None = Field(default=None, ge=0, le=1)


class ClassificationOut(BaseModel):
    id: int
    bin_id: str | None
    category: str
    confidence: float | None
    source: str
    model_version: str | None
    review_status: str
    recommendation: str
    caution: str | None = None
    note: str | None = None
    created_at: UTCDatetime


class ClassificationListOut(BaseModel):
    items: list[ClassificationOut]
    total: int
    limit: int
    offset: int


class CategoryDistributionOut(BaseModel):
    category: str
    count: int
    share_percent: float


class RecyclingSummaryAPIOut(BaseModel):
    total_classifications: int
    distribution: list[CategoryDistributionOut]
    recommendations: list[dict]
    review_required_count: int


# -------------------------------------------------------------------- alerts --
class AlertOut(BaseModel):
    id: int
    bin_id: str | None
    type: str
    severity: str
    status: str
    title: str
    message: str
    created_at: UTCDatetime
    acknowledged_at: UTCDatetime | None = None
    resolved_at: UTCDatetime | None = None
    acknowledged_by: str | None = None
    resolved_by: str | None = None


class AlertListOut(BaseModel):
    items: list[AlertOut]
    total: int
    limit: int
    offset: int


# ------------------------------------------------------------------ settings --
class SettingsOut(BaseModel):
    warning_threshold: float
    critical_threshold: float
    collection_threshold: float
    stale_after_hours: float
    fuel_price_per_litre: float
    default_consumption_l_per_100km: float
    planning_horizon_hours: int
    road_distance_factor: float
    routing_provider: str
    demo_mode: bool
    updated_at: UTCDatetime


class SettingsPatchIn(BaseModel):
    warning_threshold: float | None = Field(default=None, ge=0, le=100)
    critical_threshold: float | None = Field(default=None, ge=0, le=100)
    collection_threshold: float | None = Field(default=None, ge=0, le=100)
    stale_after_hours: float | None = Field(default=None, gt=0, le=720)
    fuel_price_per_litre: float | None = Field(default=None, gt=0, le=1000)
    default_consumption_l_per_100km: float | None = Field(default=None, gt=0, le=200)
    planning_horizon_hours: int | None = Field(default=None, ge=1, le=72)
    road_distance_factor: float | None = Field(default=None, ge=1.0, le=3.0)


# -------------------------------------------------------------------- fleet --
class TruckOut(BaseModel):
    id: str
    name: str
    registration_label: str
    capacity_litres: int
    fuel_type: str
    consumption_l_per_100km: float
    is_active: bool


class DepotOut(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    is_active: bool


# ---------------------------------------------------------------- dashboard --
class ZoneStatOut(BaseModel):
    zone: str
    bins: int
    avg_fill_percent: float
    critical_count: int


class LatestRunOut(BaseModel):
    run_id: str
    status: str
    started_at: UTCDatetime
    total_distance_km: float
    estimated_fuel_cost: float
    savings_percent: float | None
    selected_count: int


class DashboardSummaryOut(BaseModel):
    bins_total: int
    bins_critical: int
    bins_warning: int
    bins_normal: int
    bins_stale: int
    avg_fill_percent: float
    open_alerts: int
    critical_alerts: int
    zones: list[ZoneStatOut]
    fleet_active: int
    latest_run: LatestRunOut | None
    demo_mode: bool
