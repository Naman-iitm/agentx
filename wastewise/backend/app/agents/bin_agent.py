"""Bin Agent — telemetry → status + collection priority.

Deterministic, versioned, unit-tested. No LLM involved in any calculation
(per agents_config.md LLM usage policy).

Priority formula — documented simplification (agents_config.md §1):
    priority = fill_percent            (v1)
The weighted formula (0.70*fill + 0.20*overdue + 0.10*predicted_overflow) is
intentionally NOT used until every input term is implemented; v1 uses fill
percentage only and this is stated in the agent output.
"""
from datetime import datetime

from app.core.utils import hours_between

AGENT_NAME = "bin_agent"
AGENT_VERSION = "bin-agent-v1.1"


def compute_status(fill_percent: float, warning_threshold: float, critical_threshold: float) -> str:
    """Threshold classification. Boundaries (defaults 70/90):
    69.9 → NORMAL, 70 → WARNING, 89.9 → WARNING, 90 → CRITICAL."""
    if fill_percent >= critical_threshold:
        return "CRITICAL"
    if fill_percent >= warning_threshold:
        return "WARNING"
    return "NORMAL"


def evaluate_bin(
    bin_snapshot: dict,
    *,
    warning_threshold: float,
    critical_threshold: float,
    collection_threshold: float,
    stale_after_hours: float,
    now: datetime,
) -> dict:
    """Evaluate one bin snapshot → status, flags, priority, should_collect, reasons.

    bin_snapshot keys: bin_id, name, zone, fill_percent, measured_at,
    battery_percent (optional), capacity_litres.
    """
    fill = bin_snapshot["fill_percent"]
    measured_at = bin_snapshot["measured_at"]
    battery = bin_snapshot.get("battery_percent")

    status = compute_status(fill, warning_threshold, critical_threshold)

    reasons: list[str] = []
    warnings: list[str] = []
    flags: list[str] = []

    age_h = hours_between(now, measured_at) if measured_at else None
    is_stale = age_h is not None and age_h > stale_after_hours
    if is_stale:
        flags.append("STALE")
        warnings.append(
            f"Reading is {age_h:.1f}h old (> {stale_after_hours}h) — treated as stale, not live."
        )
        reasons.append("Reading marked STALE (sensor may be offline).")

    if status == "CRITICAL":
        reasons.append(f"Fill {fill:.0f}% ≥ critical threshold {critical_threshold:.0f}%.")
    elif status == "WARNING":
        reasons.append(f"Fill {fill:.0f}% ≥ warning threshold {warning_threshold:.0f}%.")

    if battery is not None and battery < 20:
        flags.append("BATTERY_LOW")
        warnings.append(f"Battery at {battery:.0f}% — schedule sensor maintenance.")

    # v1 priority: documented simplification — fill percentage only.
    priority = round(fill, 2)

    should_collect = status == "CRITICAL" or fill >= collection_threshold
    if should_collect and "Fill" not in " ".join(reasons):
        reasons.append(f"Fill {fill:.0f}% ≥ collection threshold {collection_threshold:.0f}%.")

    return {
        "bin_id": bin_snapshot["bin_id"],
        "name": bin_snapshot.get("name", ""),
        "zone": bin_snapshot.get("zone", ""),
        "latitude": bin_snapshot.get("latitude"),
        "longitude": bin_snapshot.get("longitude"),
        "fill_percent": fill,
        "status": status,
        "flags": flags,
        "is_stale": is_stale,
        "battery_percent": battery,
        "priority": priority,
        "should_collect": should_collect,
        "reasons": reasons,
        "warnings": warnings,
    }
