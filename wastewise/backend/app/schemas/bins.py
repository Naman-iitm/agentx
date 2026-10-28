"""Bin + reading schemas."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import FillStatus, ReadingSource, UTCDatetime


class BinOut(BaseModel):
    id: str
    external_code: str
    name: str
    zone: str
    latitude: float
    longitude: float
    bin_type: str
    capacity_litres: int
    is_active: bool
    # latest telemetry (computed)
    fill_percent: float | None = None
    status: FillStatus | None = None
    battery_percent: float | None = None
    measured_at: UTCDatetime | None = None
    is_stale: bool = False
    reading_source: str | None = None


class BinListOut(BaseModel):
    items: list[BinOut]
    total: int
    limit: int
    offset: int


class ReadingIn(BaseModel):
    fill_percent: float = Field(ge=0, le=100)
    measured_at: datetime | None = None  # defaults to server UTC now
    source: ReadingSource = "sensor"
    battery_percent: float | None = Field(default=None, ge=0, le=100)


class ReadingOut(BaseModel):
    id: int
    bin_id: str
    fill_percent: float
    measured_at: UTCDatetime
    source: str
    battery_percent: float | None = None
    quality_flag: str


class ReadingListOut(BaseModel):
    items: list[ReadingOut]
    total: int
    limit: int
    offset: int


class SimulateIn(BaseModel):
    steps: int = Field(default=1, ge=1, le=6, description="Simulation ticks to apply")
