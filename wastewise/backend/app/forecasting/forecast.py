"""Prediction Agent forecasting — transparent baseline model.

Method `rolling-slope-v1`:
  1. Bucket history to hourly means (dedupe bursts).
  2. Estimate the recent fill rate (%/hour) via least-squares slope over the
     most recent window (default 24 points, clamped to available data).
  3. Project forward hour by hour, clamped to 0–100.
  4. Uncertainty band: ±k·σ of the fit residuals, widening with √horizon.

Deliberately simple and inspectable per agents_config.md: "start with a
transparent rolling-average baseline before a more complex model". A
scikit-learn model with hourly/weekday features is a documented Phase 10
upgrade — not required for the MVP. Predictions are labelled predictions and
must never be presented as measured sensor readings.
"""
import math
from datetime import datetime

METHOD = "rolling-slope-v1"
MODEL_VERSION = "baseline-1.0"
MIN_READINGS = 6
MIN_SPAN_HOURS = 3.0
DEFAULT_WINDOW = 24
INSUFFICIENT_NOTE = (
    "Not enough valid history for a meaningful forecast. Showing last known "
    "value only — this is not a prediction."
)


def _bucket_hourly(
    readings: list[tuple[datetime, float]],
) -> list[tuple[datetime, float]]:
    """Average readings per whole hour, ordered oldest → newest."""
    buckets: dict[str, list[float]] = {}
    times: dict[str, datetime] = {}
    for measured_at, fill in readings:
        key = measured_at.replace(minute=0, second=0, microsecond=0).isoformat()
        buckets.setdefault(key, []).append(fill)
        times[key] = measured_at
    ordered_keys = sorted(buckets)
    return [(times[k], sum(buckets[k]) / len(buckets[k])) for k in ordered_keys]


def _slope(series: list[tuple[datetime, float]]):
    """Least-squares slope of fill vs hours. Returns (slope, residual_std, mean_x, mean_y)."""
    n = len(series)
    t0 = series[0][0]
    xs = [(t - t0).total_seconds() / 3600.0 for t, _ in series]
    ys = [f for _, f in series]
    mx, my = sum(xs) / n, sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return 0.0, 0.0, mx, my
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    resid = [y - (my + slope * (x - mx)) for x, y in zip(xs, ys)]
    std = math.sqrt(sum(r * r for r in resid) / n) if n > 2 else 0.0
    return slope, std, mx, my


def forecast_bin(
    readings: list[tuple[datetime, float]],
    now: datetime,
    horizon_hours: int,
) -> dict:
    """Compute a forecast for one bin.

    readings: list of (measured_at, fill_percent) — any order, naive UTC.
    Returns a dict with status, points and metadata — never raises.
    """
    clean = sorted(
        [(t, float(f)) for t, f in readings if f is not None], key=lambda r: r[0]
    )
    if len(clean) < MIN_READINGS:
        return {
            "status": "insufficient_history",
            "method": METHOD,
            "model_version": MODEL_VERSION,
            "points": [],
            "warnings": [f"Only {len(clean)} reading(s) available; need >= {MIN_READINGS}."],
            "note": INSUFFICIENT_NOTE,
            "last_fill_percent": clean[-1][1] if clean else None,
            "last_measured_at": clean[-1][0] if clean else None,
        }

    span_h = (clean[-1][0] - clean[0][0]).total_seconds() / 3600.0
    if span_h < MIN_SPAN_HOURS:
        return {
            "status": "insufficient_history",
            "method": METHOD,
            "model_version": MODEL_VERSION,
            "points": [],
            "warnings": [f"History spans only {span_h:.1f}h; need >= {MIN_SPAN_HOURS}h."],
            "note": INSUFFICIENT_NOTE,
            "last_fill_percent": clean[-1][1],
            "last_measured_at": clean[-1][0],
        }

    hourly = _bucket_hourly(clean)
    window = hourly[-DEFAULT_WINDOW:]
    slope, std, mx, my = _slope(window)
    last_t, last_fill = hourly[-1]

    points = []
    warnings: list[str] = []
    for h in range(1, horizon_hours + 1):
        target = last_t.replace(minute=0, second=0, microsecond=0)
        from datetime import timedelta

        target = target + timedelta(hours=h)
        # anchor the projection to the actual last reading for accuracy
        anchor_hours = (last_t - window[0][0]).total_seconds() / 3600.0
        pred = my + slope * (anchor_hours + h - mx)
        band = 1.96 * std * math.sqrt(1.0 + h / max(1.0, len(window)))
        points.append(
            {
                "target_at": target,
                "predicted_fill_percent": round(max(0.0, min(100.0, pred)), 2),
                "lower_bound": round(max(0.0, min(100.0, pred - band)), 2),
                "upper_bound": round(max(0.0, min(100.0, pred + band)), 2),
            }
        )

    if slope < 0:
        warnings.append("Estimated fill rate is negative — bins may have been collected recently.")
    if std > 8:
        warnings.append(f"High variability in recent readings (σ={std:.1f}) — treat band as wide.")

    return {
        "status": "ok",
        "method": METHOD,
        "model_version": MODEL_VERSION,
        "points": points,
        "warnings": warnings,
        "note": "Predicted values are model estimates, not sensor measurements.",
        "fill_rate_percent_per_hour": round(slope, 3),
        "residual_std": round(std, 2),
        "history_points": len(hourly),
        "last_fill_percent": last_fill,
        "last_measured_at": last_t,
    }
