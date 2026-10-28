"""Optimization runs, forecasts, recycling, alerts, fleet, settings, dashboard."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import settings_row
from app.core.errors import AppError, bad_request
from app.core.utils import paginate, utcnow
from app.db.models import AppSettings, Depot, Truck, WasteClassification
from app.db.session import get_db
from app.schemas.domain import (
    AlertListOut, AlertOut, ClassificationIn, ClassificationListOut, ClassificationOut,
    DashboardSummaryOut, DepotOut, ForecastOut, LatestRunOut, RecyclingSummaryAPIOut,
    SettingsOut, SettingsPatchIn, TruckOut, ZoneStatOut,
)
from app.schemas.optimization import (
    OptimizationRunIn, OptimizationRunListItem, OptimizationRunOut, RunListOut,
)
from app.services import alert_service, bin_service, optimization_service
from app.services.settings_service import settings_out as settings_to_out

optimization_router = APIRouter(prefix="/optimization")
alerts_router = APIRouter(prefix="/alerts")
forecasts_router = APIRouter(prefix="/forecasts")
recycling_router = APIRouter(prefix="/recycling")
fleet_router = APIRouter(prefix="/fleet")
settings_router = APIRouter(prefix="/settings")
dashboard_router = APIRouter(prefix="/dashboard")


# --------------------------------------------------------------- optimization --
@optimization_router.post("/runs", response_model=OptimizationRunOut, status_code=201, tags=["optimization"])
def create_run(
    payload: OptimizationRunIn,
    db: Session = Depends(get_db),
):
    try:
        detail = optimization_service.run_optimization(db, payload, requested_by="demo-operator")
    except RuntimeError as exc:
        raise AppError("RUN_PERSIST_FAILED", str(exc), status_code=500) from exc
    return OptimizationRunOut(**detail)


@optimization_router.get("/runs", response_model=RunListOut, tags=["optimization"])
def list_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return RunListOut(**optimization_service.list_runs(db, limit, offset))


@optimization_router.get("/runs/latest", response_model=OptimizationRunOut, tags=["optimization"])
def latest_run(db: Session = Depends(get_db)):
    runs = optimization_service.list_runs(db, limit=1, offset=0)
    if not runs.items:
        raise AppError("NO_RUNS_YET", "No optimization runs recorded yet.", status_code=404)
    return OptimizationRunOut(
        **optimization_service.build_run_detail(db, runs.items[0]["run_id"])
    )


@optimization_router.get("/runs/{run_id}", response_model=OptimizationRunOut, tags=["optimization"])
def get_run(run_id: str, db: Session = Depends(get_db)):
    return OptimizationRunOut(**optimization_service.build_run_detail(db, run_id))


# ------------------------------------------------------------------ forecasts --
@forecasts_router.get("", response_model=ForecastOut, tags=["forecasts"])
def forecast(
    bin_id: str = Query(...),
    horizon_hours: int = Query(24, ge=1, le=72),
    db: Session = Depends(get_db),
):
    from app.agents import prediction_agent as pred

    bin_service.get_bin_or_404(db, bin_id)
    history = bin_service.reading_history(db, bin_id, limit=300)
    result = pred.forecast_for_bin(history, utcnow(), horizon_hours)
    return ForecastOut(
        bin_id=bin_id,
        status=result["status"],
        method=result["method"],
        model_version=result["model_version"],
        generated_at=utcnow(),
        horizon_hours=horizon_hours,
        points=result["points"],
        warnings=result["warnings"],
        note=result["note"],
    )


# ------------------------------------------------------------------ recycling --
def _classification_out(row: WasteClassification) -> ClassificationOut:
    from app.agents.recycling_agent import handling_for

    rec = handling_for(row.category)
    return ClassificationOut(
        id=row.id, bin_id=row.bin_id, category=row.category, confidence=row.confidence,
        source=row.source, model_version=row.model_version, review_status=row.review_status,
        recommendation=rec["recommendation"], caution=rec.get("caution"), note=row.note,
        created_at=row.created_at,
    )


@recycling_router.post(
    "/classifications", response_model=ClassificationOut, status_code=201, tags=["recycling"]
)
def classify(payload: ClassificationIn, db: Session = Depends(get_db)):
    from app.agents.recycling_agent import classify as agent_classify

    if payload.bin_id:
        bin_service.get_bin_or_404(db, payload.bin_id)
    result = agent_classify(
        category=payload.category,
        bin_id=payload.bin_id,
        source=payload.source,
        confidence=payload.confidence,
    )
    if not result["ok"]:
        raise bad_request("INVALID_CATEGORY", result["error"])
    row = WasteClassification(
        bin_id=payload.bin_id,
        category=result["category"],
        confidence=payload.confidence,
        source=payload.source,
        model_version=result["model_version"],
        review_status=result["review_status"],
        note=payload.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _classification_out(row)


@recycling_router.get("/classifications", response_model=ClassificationListOut, tags=["recycling"])
def list_classifications(
    category: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(WasteClassification)
    if category:
        q = q.filter(WasteClassification.category == category.upper())
    rows = q.order_by(WasteClassification.created_at.desc()).all()
    items = [_classification_out(r).model_dump() for r in rows]
    return paginate(items, limit=limit, offset=offset)


@recycling_router.get("/summary", response_model=RecyclingSummaryAPIOut, tags=["recycling"])
def recycling_summary(db: Session = Depends(get_db)):
    from app.agents.recycling_agent import handling_for

    rows = db.query(WasteClassification).all()
    dist: dict[str, int] = {}
    for r in rows:
        dist[r.category] = dist.get(r.category, 0) + 1
    total = len(rows)
    return RecyclingSummaryAPIOut(
        total_classifications=total,
        distribution=[
            {"category": cat, "count": n, "share_percent": round(100.0 * n / total, 1)}
            for cat, n in sorted(dist.items(), key=lambda kv: -kv[1])
        ] if total else [],
        recommendations=[handling_for(cat) for cat in sorted(dist)],
        review_required_count=sum(1 for r in rows if r.review_status == "review_required"),
    )


# --------------------------------------------------------------------- alerts --
@alerts_router.get("", response_model=AlertListOut, tags=["alerts"])
def list_alerts(
    status: str | None = Query(default=None, pattern="^(OPEN|ACKNOWLEDGED|RESOLVED)$"),
    severity: str | None = Query(default=None, pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    rows = alert_service.list_alerts(db, status=status, severity=severity)
    items = [AlertOut.model_validate(a, from_attributes=True).model_dump() for a in rows]
    return paginate(items, limit=limit, offset=offset)


@alerts_router.post("/{alert_id}/acknowledge", response_model=AlertOut, tags=["alerts"])
def acknowledge(alert_id: int, db: Session = Depends(get_db)):
    alert = alert_service.acknowledge_alert(db, alert_id, by="demo-operator")
    return AlertOut.model_validate(alert, from_attributes=True)


@alerts_router.post("/{alert_id}/resolve", response_model=AlertOut, tags=["alerts"])
def resolve(alert_id: int, db: Session = Depends(get_db)):
    alert = alert_service.resolve_alert(db, alert_id, by="demo-operator")
    return AlertOut.model_validate(alert, from_attributes=True)


# ----------------------------------------------------------------------- fleet --
@fleet_router.get("/trucks", response_model=list[TruckOut], tags=["fleet"])
def list_trucks(db: Session = Depends(get_db)):
    trucks = db.query(Truck).filter(Truck.is_active.is_(True)).order_by(Truck.id).all()
    return [TruckOut.model_validate(t, from_attributes=True) for t in trucks]


@fleet_router.get("/depots", response_model=list[DepotOut], tags=["fleet"])
def list_depots(db: Session = Depends(get_db)):
    depots = db.query(Depot).filter(Depot.is_active.is_(True)).order_by(Depot.id).all()
    return [DepotOut.model_validate(d, from_attributes=True) for d in depots]


# --------------------------------------------------------------------- settings --
@settings_router.get("", response_model=SettingsOut, tags=["settings"])
def get_settings_values(db: Session = Depends(get_db)):
    from app.services.settings_service import get_settings_row

    return SettingsOut(**settings_to_out(get_settings_row(db)))


@settings_router.patch("", response_model=SettingsOut, tags=["settings"])
def patch_settings_values(
    payload: SettingsPatchIn, db: Session = Depends(get_db)
):
    from app.services.settings_service import patch_settings

    row = patch_settings(db, payload.model_dump(exclude_unset=True), actor="demo-operator")
    return SettingsOut(**settings_to_out(row))


# --------------------------------------------------------------------- dashboard --
@dashboard_router.get("/summary", response_model=DashboardSummaryOut, tags=["dashboard"])
def dashboard_summary(
    db: Session = Depends(get_db),
    settings: AppSettings = Depends(settings_row),
):
    from app.core.config import get_settings as _gs
    from app.db.models import Alert, OptimizationRun

    bins = bin_service.list_bins(db, settings, zone=None, status=None)
    zones: dict[str, dict] = {}
    for b in bins:
        z = zones.setdefault(b["zone"], {"zone": b["zone"], "bins": 0, "fill_sum": 0.0, "critical": 0})
        z["bins"] += 1
        if b["fill_percent"] is not None:
            z["fill_sum"] += b["fill_percent"]
        if b["status"] == "CRITICAL":
            z["critical"] += 1
    fills = [b["fill_percent"] for b in bins if b["fill_percent"] is not None]
    open_alerts = db.query(Alert).filter(Alert.status != "RESOLVED").count()
    critical_alerts = (
        db.query(Alert)
        .filter(Alert.status != "RESOLVED", Alert.severity == "CRITICAL")
        .count()
    )
    latest = (
        db.query(OptimizationRun)
        .order_by(OptimizationRun.started_at.desc())
        .first()
    )
    latest_out = None
    if latest:
        latest_out = LatestRunOut(
            run_id=latest.id, status=latest.status, started_at=latest.started_at,
            total_distance_km=latest.total_distance_km,
            estimated_fuel_cost=latest.estimated_fuel_cost,
            savings_percent=latest.savings_percent,
            selected_count=len(latest.selected_bin_ids or []),
        )
    return DashboardSummaryOut(
        bins_total=len(bins),
        bins_critical=sum(1 for b in bins if b["status"] == "CRITICAL"),
        bins_warning=sum(1 for b in bins if b["status"] == "WARNING"),
        bins_normal=sum(1 for b in bins if b["status"] == "NORMAL"),
        bins_stale=sum(1 for b in bins if b["is_stale"]),
        avg_fill_percent=round(sum(fills) / len(fills), 1) if fills else 0.0,
        open_alerts=open_alerts,
        critical_alerts=critical_alerts,
        zones=[
            ZoneStatOut(
                zone=z["zone"], bins=z["bins"],
                avg_fill_percent=round(z["fill_sum"] / z["bins"], 1) if z["bins"] else 0.0,
                critical_count=z["critical"],
            )
            for z in sorted(zones.values(), key=lambda z: z["zone"])
        ],
        fleet_active=db.query(Truck).filter(Truck.is_active.is_(True)).count(),
        latest_run=latest_out,
        demo_mode=_gs().demo_mode,
    )
