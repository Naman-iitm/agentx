"""Health, bins/readings and demo-simulation routes."""
import random

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_demo_mode, settings_row
from app.core.config import get_settings
from app.core.errors import bad_request
from app.core.utils import paginate, utcnow
from app.db.models import AppSettings, Bin, BinReading
from app.db.session import get_db
from app.schemas.bins import BinListOut, BinOut, ReadingIn, ReadingListOut, ReadingOut, SimulateIn
from app.services import bin_service
from app.seed.seed_data import reset_telemetry

router = APIRouter()


# -------------------------------------------------------------------- health --
@router.get("/health", tags=["health"])
def health():
    return {
        "status": "ok",
        "service": get_settings().app_name,
        "version": get_settings().version,
    }


# ----------------------------------------------------------------------- bins --
@router.get("/bins", response_model=BinListOut, tags=["bins"])
def list_bins(
    zone: str | None = None,
    status: str | None = Query(default=None, pattern="^(NORMAL|WARNING|CRITICAL)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    settings: AppSettings = Depends(settings_row),
):
    items = bin_service.list_bins(db, settings, zone=zone, status=status)
    return paginate(
        [BinOut(**b).model_dump() for b in items], limit=limit, offset=offset
    )


@router.get("/bins/{bin_id}", response_model=BinOut, tags=["bins"])
def get_bin(
    bin_id: str,
    db: Session = Depends(get_db),
    settings: AppSettings = Depends(settings_row),
):
    return BinOut(**bin_service.get_bin_detail(db, bin_id, settings))


@router.post(
    "/bins/{bin_id}/readings", response_model=ReadingOut, status_code=201, tags=["bins"]
)
def create_reading(
    bin_id: str,
    payload: ReadingIn,
    db: Session = Depends(get_db),
    settings: AppSettings = Depends(settings_row),
):
    reading = bin_service.add_reading(db, bin_id, payload, settings)
    return ReadingOut(
        id=reading.id,
        bin_id=reading.bin_id,
        fill_percent=reading.fill_percent,
        measured_at=reading.measured_at,
        source=reading.source,
        battery_percent=reading.battery_percent,
        quality_flag=reading.quality_flag,
    )


@router.get("/bins/{bin_id}/readings", response_model=ReadingListOut, tags=["bins"])
def list_readings(
    bin_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    rows = bin_service.list_readings(db, bin_id)
    items = [
        ReadingOut(
            id=r.id, bin_id=r.bin_id, fill_percent=r.fill_percent, measured_at=r.measured_at,
            source=r.source, battery_percent=r.battery_percent, quality_flag=r.quality_flag,
        ).model_dump()
        for r in rows
    ]
    return paginate(items, limit=limit, offset=offset)


# ----------------------------------------------------------------------- demo --
@router.post("/demo/simulate", tags=["demo"], dependencies=[Depends(require_demo_mode)])
def simulate(payload: SimulateIn, db: Session = Depends(get_db),
             settings: AppSettings = Depends(settings_row)):
    """Advance simulated telemetry by N ticks. DEMO DATA — clearly labelled."""
    from app.services.alert_service import evaluate_reading_alerts

    bins = db.query(Bin).filter(Bin.is_active.is_(True)).all()
    now = utcnow()
    for step in range(payload.steps):
        for b in bins:
            latest = (
                db.query(BinReading)
                .filter(BinReading.bin_id == b.id)
                .order_by(BinReading.measured_at.desc())
                .first()
            )
            current = latest.fill_percent if latest else 0.0
            new_fill = min(100.0, current + random.uniform(2.0, 8.0))
            new_battery = max(
                0.0, (latest.battery_percent if latest and latest.battery_percent else 100.0)
                - random.uniform(0.1, 0.8),
            )
            reading = BinReading(
                bin_id=b.id,
                fill_percent=round(new_fill, 2),
                measured_at=now,
                source="simulator",
                battery_percent=round(new_battery, 1),
                quality_flag="GOOD",
            )
            db.add(reading)
            evaluate_reading_alerts(db, b, reading, settings)
    db.commit()
    return {
        "simulated": True,
        "steps": payload.steps,
        "bins_updated": len(bins),
        "note": "Demo simulation — values are synthetic, not sensor measurements.",
    }


@router.post("/demo/reset", tags=["demo"], dependencies=[Depends(require_demo_mode)])
def reset_demo(db: Session = Depends(get_db)):
    """Regenerate seeded telemetry (useful for repeated exhibition demos)."""
    count = reset_telemetry(db)
    if count == 0:
        raise bad_request("SEED_EMPTY", "No bins found — seed the database first.")
    return {"reset": True, "bins": count, "note": "Demo telemetry regenerated."}
