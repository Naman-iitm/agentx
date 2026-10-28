"""Bin + reading use-cases (DB logic stays out of route handlers)."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.bin_agent import compute_status
from app.core.errors import bad_request, not_found
from app.core.utils import hours_between, to_utc, utcnow
from app.db.models import AppSettings, Bin, BinReading
from app.schemas.bins import ReadingIn


def get_bin_or_404(db: Session, bin_id: str) -> Bin:
    b = db.get(Bin, bin_id)
    if not b:
        raise not_found("bin", bin_id)
    return b


def _latest_reading(db: Session, bin_id: str) -> BinReading | None:
    return (
        db.execute(
            select(BinReading)
            .where(BinReading.bin_id == bin_id)
            .order_by(BinReading.measured_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )


def bin_to_out(db: Session, bin_: Bin, settings: AppSettings) -> dict:
    latest = _latest_reading(db, bin_.id)
    stale = False
    status = None
    if latest:
        status = compute_status(
            latest.fill_percent, settings.warning_threshold, settings.critical_threshold
        )
        stale = hours_between(utcnow(), latest.measured_at) > settings.stale_after_hours
    return {
        "id": bin_.id,
        "external_code": bin_.external_code,
        "name": bin_.name,
        "zone": bin_.zone,
        "latitude": bin_.latitude,
        "longitude": bin_.longitude,
        "bin_type": bin_.bin_type,
        "capacity_litres": bin_.capacity_litres,
        "is_active": bin_.is_active,
        "fill_percent": latest.fill_percent if latest else None,
        "status": status,
        "battery_percent": latest.battery_percent if latest else None,
        "measured_at": latest.measured_at if latest else None,
        "is_stale": stale,
        "reading_source": latest.source if latest else None,
    }


def list_bins(
    db: Session, settings: AppSettings, *, zone: str | None, status: str | None
) -> list[dict]:
    q = db.query(Bin).filter(Bin.is_active.is_(True))
    if zone:
        q = q.filter(Bin.zone == zone)
    bins = q.order_by(Bin.id).all()
    out = [bin_to_out(db, b, settings) for b in bins]
    if status:
        out = [b for b in out if b["status"] == status]
    return out


def get_bin_detail(db: Session, bin_id: str, settings: AppSettings) -> dict:
    return bin_to_out(db, get_bin_or_404(db, bin_id), settings)


def add_reading(db: Session, bin_id: str, payload: ReadingIn, settings: AppSettings) -> BinReading:
    """Ingest one validated reading. Status is computed server-side only."""
    bin_ = get_bin_or_404(db, bin_id)
    measured_at = to_utc(payload.measured_at) if payload.measured_at else utcnow()
    if measured_at > utcnow():
        raise bad_request("READING_IN_FUTURE", "measured_at cannot be in the future.")

    stale = hours_between(utcnow(), measured_at) > settings.stale_after_hours
    reading = BinReading(
        bin_id=bin_.id,
        fill_percent=payload.fill_percent,
        measured_at=measured_at,
        source=payload.source,
        battery_percent=payload.battery_percent,
        quality_flag="STALE" if stale else "GOOD",
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    # Alert evaluation lives in alert_service (import here to avoid cycles)
    from app.services.alert_service import evaluate_reading_alerts

    evaluate_reading_alerts(db, bin_, reading, settings)
    return reading


def list_readings(db: Session, bin_id: str) -> list[BinReading]:
    get_bin_or_404(db, bin_id)
    return (
        db.query(BinReading)
        .filter(BinReading.bin_id == bin_id)
        .order_by(BinReading.measured_at.desc())
        .all()
    )


def reading_history(db: Session, bin_id: str, limit: int = 200) -> list[tuple[datetime, float]]:
    """Oldest→newest (fill, measured_at) pairs for forecasting."""
    rows = (
        db.query(BinReading)
        .filter(BinReading.bin_id == bin_id)
        .order_by(BinReading.measured_at.desc())
        .limit(limit)
        .all()
    )
    return [(r.measured_at, r.fill_percent) for r in reversed(rows)]
