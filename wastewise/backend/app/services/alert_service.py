"""Alert lifecycle: creation (deduplicated), listing, state transitions."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import conflict, not_found
from app.core.utils import utcnow
from app.db.models import Alert, AppSettings, Bin, BinReading

VALID_TRANSITIONS = {
    "OPEN": {"ACKNOWLEDGED", "RESOLVED"},
    "ACKNOWLEDGED": {"RESOLVED"},
    "RESOLVED": set(),
}


def get_alert_or_404(db: Session, alert_id: int) -> Alert:
    a = db.get(Alert, alert_id)
    if not a:
        raise not_found("alert", str(alert_id))
    return a


def create_alert(
    db: Session, *, bin_id: str | None, type_: str, severity: str, title: str, message: str
) -> Alert | None:
    """Create an alert unless an identical OPEN one exists (dedupe)."""
    existing = (
        db.execute(
            select(Alert).where(Alert.bin_id == bin_id, Alert.type == type_, Alert.status == "OPEN")
        )
        .scalars()
        .first()
    )
    if existing:
        return None
    alert = Alert(
        bin_id=bin_id, type=type_, severity=severity, title=title, message=message
    )
    db.add(alert)
    return alert


def evaluate_reading_alerts(
    db: Session, bin_: Bin, reading: BinReading, settings: AppSettings
) -> list[Alert]:
    """Auto-create alerts from a fresh reading (used by ingestion + simulator)."""
    created: list[Alert] = []
    from app.agents.bin_agent import compute_status
    from app.core.utils import hours_between

    status = compute_status(
        reading.fill_percent, settings.warning_threshold, settings.critical_threshold
    )
    if status == "CRITICAL":
        a = create_alert(
            db,
            bin_id=bin_.id,
            type_="OVERFLOW_RISK",
            severity="CRITICAL",
            title=f"{bin_.name} at {reading.fill_percent:.0f}% — overflow risk",
            message=(
                f"Bin {bin_.id} ({bin_.zone}) is at {reading.fill_percent:.0f}% fill "
                f"(critical threshold {settings.critical_threshold:.0f}%). Collection recommended immediately."
            ),
        )
        if a:
            created.append(a)
    if reading.quality_flag == "STALE" or hours_between(utcnow(), reading.measured_at) > settings.stale_after_hours:
        a = create_alert(
            db,
            bin_id=bin_.id,
            type_="SENSOR_STALE",
            severity="HIGH",
            title=f"{bin_.name} sensor data is stale",
            message=(
                f"No fresh telemetry for bin {bin_.id} (last reading "
                f"{reading.measured_at.isoformat()}Z). Reading marked STALE — not treated as live."
            ),
        )
        if a:
            created.append(a)
    if reading.battery_percent is not None and reading.battery_percent < 20:
        a = create_alert(
            db,
            bin_id=bin_.id,
            type_="BATTERY_LOW",
            severity="MEDIUM",
            title=f"{bin_.name} sensor battery at {reading.battery_percent:.0f}%",
            message=f"Sensor battery for bin {bin_.id} is low — schedule maintenance.",
        )
        if a:
            created.append(a)
    if created:
        db.commit()
    return created


def list_alerts(
    db: Session, *, status: str | None, severity: str | None
) -> list[Alert]:
    q = db.query(Alert)
    if status:
        q = q.filter(Alert.status == status)
    if severity:
        q = q.filter(Alert.severity == severity)
    return q.order_by(Alert.created_at.desc()).all()


def acknowledge_alert(db: Session, alert_id: int, by: str) -> Alert:
    alert = get_alert_or_404(db, alert_id)
    if "ACKNOWLEDGED" not in VALID_TRANSITIONS[alert.status]:
        raise conflict(
            "INVALID_TRANSITION",
            f"Cannot acknowledge an alert in status {alert.status}.",
        )
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = utcnow()
    alert.acknowledged_by = by
    db.commit()
    db.refresh(alert)
    return alert


def resolve_alert(db: Session, alert_id: int, by: str) -> Alert:
    alert = get_alert_or_404(db, alert_id)
    if "RESOLVED" not in VALID_TRANSITIONS[alert.status]:
        raise conflict(
            "INVALID_TRANSITION", f"Cannot resolve an alert in status {alert.status}."
        )
    alert.status = "RESOLVED"
    alert.resolved_at = utcnow()
    alert.resolved_by = by
    db.commit()
    db.refresh(alert)
    return alert
