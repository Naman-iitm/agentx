"""SQLAlchemy models — mirrors docs/data_model.md.

Deviations for the documented local prototype:
- SQLite instead of PostgreSQL+PostGIS (lat/lng as plain floats, haversine in Python)
- create_all() + idempotent seed instead of Alembic migrations (production step documented)
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.utils import utcnow
from app.db.session import Base


class Bin(Base):
    __tablename__ = "bins"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # BIN-001
    external_code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    zone: Mapped[str] = mapped_column(String(60), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    bin_type: Mapped[str] = mapped_column(String(30), default="general")
    capacity_litres: Mapped[int] = mapped_column(Integer, default=600)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    readings: Mapped[list["BinReading"]] = relationship(
        back_populates="bin", cascade="all, delete-orphan"
    )


class BinReading(Base):
    __tablename__ = "bin_readings"
    __table_args__ = (Index("ix_bin_readings_bin_time", "bin_id", "measured_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bin_id: Mapped[str] = mapped_column(ForeignKey("bins.id"))
    fill_percent: Mapped[float] = mapped_column(Float)
    measured_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    source: Mapped[str] = mapped_column(String(20), default="sensor")  # sensor|simulator|manual|import
    battery_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_flag: Mapped[str] = mapped_column(String(10), default="GOOD")  # GOOD|SUSPECT|STALE
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    bin: Mapped[Bin] = relationship(back_populates="readings")


class Truck(Base):
    __tablename__ = "trucks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    registration_label: Mapped[str] = mapped_column(String(40))
    capacity_litres: Mapped[int] = mapped_column(Integer)
    fuel_type: Mapped[str] = mapped_column(String(20), default="diesel")
    consumption_l_per_100km: Mapped[float] = mapped_column(Float, default=18.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Depot(Base):
    __tablename__ = "depots"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # run_<hex>
    requested_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    depot_id: Mapped[str] = mapped_column(String(32))
    truck_id: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(20))  # PENDING..FEASIBLE/PARTIAL/INFEASIBLE/FAILED
    solver_name: Mapped[str] = mapped_column(String(60), default="")
    algorithm_version: Mapped[str] = mapped_column(String(40), default="")
    total_distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    baseline_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_fuel_litres: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_fuel_cost: Mapped[float] = mapped_column(Float, default=0.0)
    savings_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    selected_bin_ids: Mapped[list] = mapped_column(JSON, default=list)
    # Full API response cached at run time (GET /runs/{id} returns exactly
    # what the run produced, even if live bin data changes afterwards).
    result_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    stops: Mapped[list["RouteStop"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class RouteStop(Base):
    __tablename__ = "route_stops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("optimization_runs.id"))
    sequence_number: Mapped[int] = mapped_column(Integer)
    bin_id: Mapped[str] = mapped_column(String(32))
    distance_from_previous_km: Mapped[float] = mapped_column(Float, default=0.0)
    demand_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    collected: Mapped[bool] = mapped_column(Boolean, default=False)

    run: Mapped[OptimizationRun] = relationship(back_populates="stops")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    optimization_run_id: Mapped[str] = mapped_column(ForeignKey("optimization_runs.id"))
    agent_name: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))  # success|partial|skipped|failed
    input_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    output_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    run: Mapped[OptimizationRun] = relationship(back_populates="agent_runs")


class WasteClassification(Base):
    __tablename__ = "waste_classifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bin_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str] = mapped_column(String(20), index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="operator")  # operator|model|import
    model_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="confirmed")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Forecast(Base):
    """Reserved for scheduled/persisted forecasts (Phase 10).

    The MVP computes forecasts on demand from bin_readings; the table exists
    so a scheduled refresh job has a home without a schema change."""

    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bin_id: Mapped[str] = mapped_column(String(32), index=True)
    target_at: Mapped[datetime] = mapped_column(DateTime)
    predicted_fill_percent: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(40))
    model_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    lower_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    evaluation_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bin_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(30))  # OVERFLOW_RISK|SENSOR_STALE|BATTERY_LOW|ROUTE_INFEASIBLE|FORECAST_ANOMALY
    severity: Mapped[str] = mapped_column(String(12))  # CRITICAL|HIGH|MEDIUM|LOW
    status: Mapped[str] = mapped_column(String(14), default="OPEN", index=True)  # OPEN|ACKNOWLEDGED|RESOLVED
    title: Mapped[str] = mapped_column(String(140))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(80), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    resource_type: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[str] = mapped_column(String(60))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AppSettings(Base):
    """Singleton row (id=1) of safe operational settings."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    warning_threshold: Mapped[float] = mapped_column(Float, default=70.0)
    critical_threshold: Mapped[float] = mapped_column(Float, default=90.0)
    collection_threshold: Mapped[float] = mapped_column(Float, default=75.0)
    stale_after_hours: Mapped[float] = mapped_column(Float, default=24.0)
    fuel_price_per_litre: Mapped[float] = mapped_column(Float, default=94.5)
    default_consumption_l_per_100km: Mapped[float] = mapped_column(Float, default=18.0)
    planning_horizon_hours: Mapped[int] = mapped_column(Integer, default=12)
    road_distance_factor: Mapped[float] = mapped_column(Float, default=1.30)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
