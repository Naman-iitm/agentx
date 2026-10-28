"""Fuel Agent — litres, cost and baseline savings from actual route distance."""
from app.core.utils import round2

AGENT_NAME = "fuel_agent"

ESTIMATE_NOTE = (
    "Estimate only: excludes idling, road grade, congestion, payload variation "
    "and maintenance. Demo assumptions, clearly labelled."
)


def estimate_fuel(
    *,
    distance_km: float,
    consumption_l_per_100km: float,
    fuel_price_per_litre: float,
    baseline_distance_km: float | None,
) -> dict:
    """litres = km * L/100km / 100 ; cost = litres * price.

    Savings compare against the documented baseline tour (see route_agent);
    if the baseline is missing or zero the savings are returned as None —
    never a fabricated number.
    """
    litres = distance_km * consumption_l_per_100km / 100.0
    cost = litres * fuel_price_per_litre

    baseline: dict | None = None
    savings_percent: float | None = None
    if baseline_distance_km:
        b_litres = baseline_distance_km * consumption_l_per_100km / 100.0
        b_cost = b_litres * fuel_price_per_litre
        baseline = {
            "method": "priority-descending tour (no solver)",
            "distance_km": round2(baseline_distance_km),
            "fuel_litres": round2(b_litres),
            "fuel_cost": round2(b_cost),
        }
        if b_cost > 0:
            savings_percent = round2(100.0 * (b_cost - cost) / b_cost)

    return {
        "distance_km": round2(distance_km),
        "consumption_l_per_100km": consumption_l_per_100km,
        "fuel_price_per_litre": fuel_price_per_litre,
        "estimated_fuel_litres": round2(litres),
        "estimated_fuel_cost": round2(cost),
        "baseline": baseline,
        "savings_percent": savings_percent,
        "note": ESTIMATE_NOTE,
    }
