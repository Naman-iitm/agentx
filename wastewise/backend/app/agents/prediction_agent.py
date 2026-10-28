"""Prediction Agent — forecasts future fill levels from history.

Thin coordinator around forecasting.forecast_bin so the workflow node stays
small and the math stays independently testable.
"""
from app.core.utils import safe_percent
from app.forecasting.forecast import forecast_bin

AGENT_NAME = "prediction_agent"


def forecast_for_bin(history: list[tuple], now, horizon_hours: int) -> dict:
    return forecast_bin(history, now, horizon_hours)


def predicted_overflow(
    forecast: dict, critical_threshold: float
) -> tuple[bool, float | None]:
    """Will the bin cross the critical threshold within the horizon?

    Returns (will_overflow, first_predicted_value_above_threshold).
    Only uses valid forecasts — never fabricates a value.
    """
    if forecast.get("status") != "ok" or not forecast.get("points"):
        return False, None
    for p in forecast["points"]:
        if p["predicted_fill_percent"] >= critical_threshold:
            return True, p["predicted_fill_percent"]
    return False, None


def predicted_fill_at_horizon(forecast: dict) -> float | None:
    """Fill level predicted at the end of the horizon (or None)."""
    if forecast.get("status") != "ok" or not forecast.get("points"):
        return None
    return safe_percent(forecast["points"][-1]["predicted_fill_percent"])
