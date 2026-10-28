"""Safe operational settings (singleton row) with validation + audit trail."""
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import bad_request
from app.core.utils import utcnow
from app.db.models import AppSettings, AuditEvent


def get_settings_row(db: Session) -> AppSettings:
    row = db.get(AppSettings, 1)
    if not row:
        row = AppSettings(id=1)
        env = get_settings()
        row.fuel_price_per_litre = env.fuel_price_per_litre
        row.default_consumption_l_per_100km = env.fuel_consumption_l_per_100km
        row.road_distance_factor = env.road_distance_factor
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def settings_out(row: AppSettings) -> dict:
    return {
        "warning_threshold": row.warning_threshold,
        "critical_threshold": row.critical_threshold,
        "collection_threshold": row.collection_threshold,
        "stale_after_hours": row.stale_after_hours,
        "fuel_price_per_litre": row.fuel_price_per_litre,
        "default_consumption_l_per_100km": row.default_consumption_l_per_100km,
        "planning_horizon_hours": row.planning_horizon_hours,
        "road_distance_factor": row.road_distance_factor,
        "routing_provider": get_settings().routing_provider,
        "demo_mode": get_settings().demo_mode,
        "updated_at": row.updated_at,
    }


PATCHABLE_FIELDS = (
    "warning_threshold",
    "critical_threshold",
    "collection_threshold",
    "stale_after_hours",
    "fuel_price_per_litre",
    "default_consumption_l_per_100km",
    "planning_horizon_hours",
    "road_distance_factor",
)


def patch_settings(db: Session, patch: dict, actor: str) -> AppSettings:
    row = get_settings_row(db)
    # Validate the *merged* result, not just the patch fragment.
    updated = {f: getattr(row, f) for f in PATCHABLE_FIELDS}
    updated.update({k: v for k, v in patch.items() if v is not None})

    if not (0 <= updated["warning_threshold"] < updated["critical_threshold"] <= 100):
        raise bad_request(
            "INVALID_THRESHOLDS",
            "Require 0 ≤ warning_threshold < critical_threshold ≤ 100.",
        )
    if not (updated["warning_threshold"] <= updated["collection_threshold"] <= 100):
        raise bad_request(
            "INVALID_THRESHOLDS",
            "collection_threshold must be between warning_threshold and 100.",
        )

    changes: dict = {}
    for key, value in patch.items():
        if value is not None and getattr(row, key) != value:
            changes[key] = {"from": getattr(row, key), "to": value}
            setattr(row, key, value)
    row.updated_at = utcnow()
    db.add(
        AuditEvent(
            actor_id=actor,
            action="settings.update",
            resource_type="app_settings",
            resource_id="1",
            details={"changes": {k: v["to"] for k, v in changes.items()}},
        )
    )
    db.commit()
    db.refresh(row)
    return row
