"""Route Agent — feasible collection route over selected candidates."""
from app.core.utils import round2
from app.optimization.solver import (
    ALGORITHM_VERSION,
    VRPInput,
    route_distance_for_order,
    solve_vrp,
)

AGENT_NAME = "route_agent"


def build_route(
    candidates: list[dict],
    *,
    depot: dict,
    truck: dict,
    road_factor: float,
) -> dict:
    """Build a capacity-constrained route visiting only the given candidates.

    Returns the solver output plus a documented baseline tour (candidates in
    descending priority order) used by the Fuel Agent for savings comparison.
    """
    bins = [
        {
            "bin_id": c["bin_id"],
            "latitude": c["latitude"],
            "longitude": c["longitude"],
            "demand_litres": c["demand_litres"],
        }
        for c in candidates
    ]

    vrp = solve_vrp(
        VRPInput(
            depot_lat=depot["latitude"],
            depot_lng=depot["longitude"],
            bins=bins,
            capacity_litres=truck["capacity_litres"],
            road_factor=road_factor,
        )
    )

    by_id = {c["bin_id"]: c for c in candidates}
    stops = [
        {
            "sequence": i + 1,
            "bin_id": bid,
            "name": by_id[bid]["name"],
            "zone": by_id[bid]["zone"],
            "distance_from_previous_km": vrp.leg_distances_km.get(bid, 0.0),
            "demand_litres": round2(by_id[bid]["demand_litres"]),
        }
        for i, bid in enumerate(vrp.ordered_bin_ids)
    ]

    # Baseline (documented, not invented): same bins visited in descending
    # priority order — i.e. what an operator without a solver would do.
    baseline_order = sorted(candidates, key=lambda c: (-c.get("priority", 0), c["bin_id"]))
    baseline_km = (
        route_distance_for_order(
            depot["latitude"], depot["longitude"], baseline_order, road_factor
        )
        if baseline_order
        else 0.0
    )

    return {
        "status": vrp.status,
        "solver": vrp.solver,
        "algorithm_version": ALGORITHM_VERSION,
        "stops": stops,
        "ordered_bin_ids": vrp.ordered_bin_ids,
        "total_distance_km": vrp.total_distance_km,
        "return_leg_km": vrp.return_leg_km,
        "unserved_bin_ids": vrp.unserved_bin_ids,
        "baseline_distance_km": baseline_km,
        "baseline_method": "priority-descending tour (no solver)",
        "warnings": list(vrp.warnings),
    }
