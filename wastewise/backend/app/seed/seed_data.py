"""Idempotent demo seed — a simulated Jaipur deployment.

All data is SIMULATED and labelled as such (source="simulator"). Rerunning
the seed never duplicates rows. Coordinates are real Jaipur landmarks so the
map feels authentic; fill levels are chosen to demonstrate every status.
"""
import random
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.utils import utcnow
from app.db.models import (
    Alert, AppSettings, Bin, BinReading, Depot, Truck, WasteClassification,
)
from app.services.alert_service import evaluate_reading_alerts
from app.services.settings_service import get_settings_row

DEPOT = {
    "id": "DEPOT-001",
    "name": "Transport Nagar Depot (Demo)",
    "latitude": 26.9050,
    "longitude": 75.7870,
}

# id, name, zone, lat, lng, type, target fill %, battery %, hours stale
BINS = [
    ("BIN-001", "MI Road Corner",        "Central", 26.9138, 75.8070, "general",   94, 71, 0),
    ("BIN-002", "Johari Bazaar",         "Central", 26.9207, 75.8230, "general",   88, 63, 0),
    ("BIN-003", "Bapu Bazaar",           "Central", 26.9152, 75.8175, "general",   72, 80, 0),
    ("BIN-004", "C-Scheme",              "Central", 26.9060, 75.7930, "recycling", 41, 92, 0),
    ("BIN-005", "Ram Niwas Garden",      "Central", 26.9230, 75.8180, "organic",   55, 58, 0),
    ("BIN-006", "Malviya Nagar Market",  "South",   26.8560, 75.8130, "general",   96, 44, 0),
    ("BIN-007", "Tonk Road",             "South",   26.8770, 75.8020, "general",   79, 88, 0),
    ("BIN-008", "Mansarovar Metro",      "South",   26.8500, 75.7600, "general",   63, 90, 0),
    ("BIN-009", "Vaishali Nagar",        "West",    26.9120, 75.7400, "recycling", 33, 76, 0),
    ("BIN-010", "Shastri Nagar",         "North",   26.9450, 75.7900, "general",   91, 69, 30),  # stale sensor
    ("BIN-011", "Vidyadhar Nagar",       "North",   26.9600, 75.7700, "organic",   47, 83, 0),
    ("BIN-012", "Ambabari Circle",       "North",   26.9350, 75.7600, "general",   68, 12, 0),   # low battery
]

TRUCKS = [
    ("TRUCK-001", "Compactor Truck A", "RJ14 GA 0901", 8000, "diesel", 18.0),
    ("TRUCK-002", "Compactor Truck B", "RJ14 GB 1187", 6000, "diesel", 21.0),
    ("TRUCK-003", "Tipper Truck C (CNG)", "RJ14 GC 3345", 4000, "cng", 12.0),
]

CLASSIFICATIONS = [
    ("BIN-001", "MIXED",     "operator", None, None),
    ("BIN-002", "PLASTIC",   "operator", None, None),
    ("BIN-003", "ORGANIC",   "operator", None, None),
    ("BIN-004", "PAPER",     "operator", None, None),
    ("BIN-004", "GLASS",     "model",    0.82, "waste-img-v0 (demo)"),
    ("BIN-005", "ORGANIC",   "operator", None, None),
    ("BIN-006", "MIXED",     "operator", None, None),
    ("BIN-007", "PLASTIC",   "operator", None, None),
    ("BIN-008", "METAL",     "model",    0.41, "waste-img-v0 (demo)"),  # low confidence → review
    ("BIN-009", "PAPER",     "operator", None, None),
    ("BIN-010", "E_WASTE",   "operator", None, None),
    ("BIN-011", "ORGANIC",   "operator", None, None),
    ("BIN-012", "MIXED",     "operator", None, None),
]

HISTORY_HOURS = 48


def _history(target_fill: float, bin_id: str, stale_hours: float) -> list[tuple]:
    """Deterministic hourly history ending at the target fill."""
    rng = random.Random(f"demo-{bin_id}")
    growth = [rng.uniform(0.6, 2.1) for _ in range(HISTORY_HOURS - 1)]
    total_growth = sum(growth)
    base = max(2.0, target_fill - total_growth)
    points, fill = [], base
    now = utcnow()
    start = now - timedelta(hours=HISTORY_HOURS - 1 + stale_hours)
    for i in range(HISTORY_HOURS):
        measured_at = start + timedelta(hours=i)
        battery_drift = 100 - (i / HISTORY_HOURS) * 35  # slow battery drain
        points.append((measured_at, round(min(100.0, max(0.0, fill)), 2), round(battery_drift, 1)))
        if i < HISTORY_HOURS - 1:
            fill += growth[i] + rng.uniform(-0.4, 0.4)  # small daily jitter
    # force the final point to the exact target
    last = points[-1]
    points[-1] = (last[0], float(target_fill), last[2])
    return points


def seed(db: Session) -> None:
    """Create demo data if the database is empty. Idempotent."""
    if db.query(Bin).count() > 0:
        return
    db.add(Depot(**DEPOT, is_active=True))
    for tid, name, reg, cap, fuel, cons in TRUCKS:
        db.add(
            Truck(
                id=tid, name=name, registration_label=reg, capacity_litres=cap,
                fuel_type=fuel, consumption_l_per_100km=cons, is_active=True,
            )
        )
    settings = get_settings_row(db)
    for bid, name, zone, lat, lng, btype, target, battery, stale_h in BINS:
        bin_ = Bin(
            id=bid, external_code=f"WW-{bid[-3:]}", name=f"{name} (Demo)", zone=zone,
            latitude=lat, longitude=lng, bin_type=btype,
            capacity_litres=600 if btype != "organic" else 400, is_active=True,
        )
        db.add(bin_)
        for measured_at, fill, battery_level in _history(target, bid, stale_h):
            db.add(
                BinReading(
                    bin_id=bid, fill_percent=fill, measured_at=measured_at,
                    source="simulator",
                    battery_percent=min(battery_level, battery) if battery else battery_level,
                    quality_flag="STALE" if stale_h and measured_at == _history(target, bid, stale_h)[-1][0] else "GOOD",
                )
            )
        # Flush pending inserts so the latest-reading query below sees them
        # (sessions may run with autoflush=False).
        db.flush()
        # evaluate alerts on the latest reading
        latest = (
            db.query(BinReading)
            .filter(BinReading.bin_id == bid)
            .order_by(BinReading.measured_at.desc())
            .first()
        )
        if latest:
            evaluate_reading_alerts(db, bin_, latest, settings)
    for bid, cat, source, conf, model in CLASSIFICATIONS:
        db.add(
            WasteClassification(
                bin_id=bid, category=cat, source=source, confidence=conf,
                model_version=model,
                review_status="review_required"
                if (source == "model" and conf is not None and conf < 0.55)
                else "confirmed",
            )
        )
    db.commit()


def reset_telemetry(db: Session) -> int:
    """Wipe readings + open alerts and regenerate demo history (exhibition loop)."""
    from app.services.settings_service import get_settings_row as _gsr

    db.query(BinReading).delete()
    db.query(Alert).filter(Alert.status != "RESOLVED").delete()
    settings = _gsr(db)
    for bid, name, zone, lat, lng, btype, target, battery, stale_h in BINS:
        bin_ = db.get(Bin, bid)
        if not bin_:
            continue
        history = _history(target, bid, stale_h)
        last_t = None
        for measured_at, fill, battery_level in history:
            last_t = measured_at
            db.add(
                BinReading(
                    bin_id=bid, fill_percent=fill, measured_at=measured_at,
                    source="simulator",
                    battery_percent=min(battery_level, battery) if battery else battery_level,
                    quality_flag="STALE" if (stale_h and measured_at == history[-1][0]) else "GOOD",
                )
            )
        db.flush()
        latest = (
            db.query(BinReading)
            .filter(BinReading.bin_id == bid)
            .order_by(BinReading.measured_at.desc())
            .first()
        )
        if latest:
            evaluate_reading_alerts(db, bin_, latest, settings)
    db.commit()
    return db.query(Bin).count()
