"""Vehicle routing with capacity constraints.

Primary solver: Google OR-Tools (CVRP with drop penalties).
Fallback: deterministic nearest-neighbour + 2-opt, explicitly labelled as a
heuristic — per agents_config.md ("a nearest-neighbour fallback is acceptable
but must be labelled heuristic, not globally optimal").

Distances are haversine great-circle estimates multiplied by a road-distance
factor (default 1.30). This is a documented approximation, not road network
data — the UI labels it accordingly.
"""
from dataclasses import dataclass, field

from app.core.utils import haversine_km

SOLVER_ORTOOLS = "OR-Tools CVRP (PATH_CHEAPEST_ARC + GUIDED_LOCAL_SEARCH)"
SOLVER_HEURISTIC = "Heuristic (nearest-neighbour + 2-opt) — not globally optimal"
ALGORITHM_VERSION = "vrp-v1"


@dataclass
class VRPInput:
    depot_lat: float
    depot_lng: float
    bins: list[dict]  # [{bin_id, latitude, longitude, demand_litres}]
    capacity_litres: float
    road_factor: float = 1.30


@dataclass
class VRPOutput:
    status: str  # FEASIBLE | PARTIAL | INFEASIBLE
    solver: str
    ordered_bin_ids: list[str] = field(default_factory=list)
    leg_distances_km: dict[str, float] = field(default_factory=dict)  # bin_id -> dist from previous
    total_distance_km: float = 0.0
    return_leg_km: float = 0.0
    unserved_bin_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _matrix_meters(inp: VRPInput) -> list[list[int]]:
    """Distance matrix in whole metres: node 0 = depot, 1..n = bins."""
    coords = [(inp.depot_lat, inp.depot_lng)] + [
        (b["latitude"], b["longitude"]) for b in inp.bins
    ]
    n = len(coords)
    m = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            km = haversine_km(*coords[i], *coords[j]) * inp.road_factor
            m[i][j] = m[j][i] = int(round(km * 1000))
    return m


def solve_vrp(inp: VRPInput) -> VRPOutput:
    if not inp.bins:
        return VRPOutput(
            status="FEASIBLE",
            solver=SOLVER_HEURISTIC,
            warnings=["No collection candidates — empty route returned."],
        )
    if inp.capacity_litres <= 0:
        return VRPOutput(
            status="INFEASIBLE",
            solver=SOLVER_HEURISTIC,
            unserved_bin_ids=[b["bin_id"] for b in inp.bins],
            warnings=["Truck capacity must be positive."],
        )
    try:
        return _solve_ortools(inp)
    except Exception as exc:  # noqa: BLE001 — any solver failure degrades gracefully
        out = _solve_heuristic(inp)
        out.warnings.append(f"OR-Tools unavailable/fallback triggered: {exc}")
        out.solver = SOLVER_HEURISTIC
        return out


def _solve_ortools(inp: VRPInput) -> VRPOutput:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    matrix = _matrix_meters(inp)
    n_bins = len(inp.bins)
    demands = [0] + [int(round(b["demand_litres"])) for b in inp.bins]

    manager = pywrapcp.RoutingIndexManager(n_bins + 1, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_cb(from_index: int, to_index: int) -> int:
        return matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit = routing.RegisterTransitCallback(distance_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit)

    def demand_cb(from_index: int) -> int:
        return demands[manager.IndexToNode(from_index)]

    demand_index = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        demand_index,
        slack_max=0,
        vehicle_capacities=[int(inp.capacity_litres)],
        fix_start_cumul_to_zero=True,
        name="Capacity",
    )
    # Allow dropping a bin at a heavy penalty so capacity overflows surface
    # as "unserved" instead of a hard infeasibility.
    for node in range(1, n_bins + 1):
        routing.AddDisjunction([manager.NodeToIndex(node)], 10_000_000)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    params.time_limit.FromMilliseconds(1000)

    solution = routing.SolveWithParameters(params)
    if solution is None:
        raise RuntimeError("OR-Tools returned no solution")

    ordered: list[str] = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        if node != 0:
            ordered.append(inp.bins[node - 1]["bin_id"])
        index = solution.Value(routing.NextVar(index))

    unserved = [b["bin_id"] for b in inp.bins if b["bin_id"] not in ordered]
    out = _assemble(inp, ordered, unserved)
    out.solver = SOLVER_ORTOOLS
    if unserved:
        out.warnings.append(
            f"{len(unserved)} bin(s) dropped: total demand exceeds truck capacity."
        )
    return out


def _solve_heuristic(inp: VRPInput) -> VRPOutput:
    """Greedy nearest-neighbour with capacity check, then 2-opt improvement."""
    remaining = {b["bin_id"]: b for b in inp.bins}
    ordered: list[str] = []
    load = 0.0
    cur_lat, cur_lng = inp.depot_lat, inp.depot_lng

    # Keep visiting the nearest bin that still fits; stop when nothing fits.
    while remaining:
        fitting = [
            bid for bid, b in remaining.items() if load + b["demand_litres"] <= inp.capacity_litres
        ]
        if not fitting:
            break
        nearest = min(
            fitting,
            key=lambda bid: haversine_km(cur_lat, cur_lng, remaining[bid]["latitude"], remaining[bid]["longitude"]),
        )
        b = remaining.pop(nearest)
        ordered.append(nearest)
        load += b["demand_litres"]
        cur_lat, cur_lng = b["latitude"], b["longitude"]

    ordered = _two_opt(inp, ordered)
    unserved = [b["bin_id"] for b in inp.bins if b["bin_id"] not in ordered]
    out = _assemble(inp, ordered, unserved)
    out.solver = SOLVER_HEURISTIC
    if unserved:
        out.warnings.append(
            f"{len(unserved)} bin(s) unserved: demand exceeds remaining truck capacity."
        )
    return out


def _two_opt(inp: VRPInput, ordered: list[str]) -> list[str]:
    """Classic 2-opt on the depot-bins-depot tour (capacity unchanged)."""
    if len(ordered) < 3:
        return ordered
    by_id = {b["bin_id"]: b for b in inp.bins}
    coords = {
        "DEPOT": (inp.depot_lat, inp.depot_lng),
        **{bid: (by_id[bid]["latitude"], by_id[bid]["longitude"]) for bid in by_id},
    }

    def d(a: str, b: str) -> float:
        return haversine_km(*coords[a], *coords[b]) * inp.road_factor

    def tour_length(seq: list[str]) -> float:
        path = ["DEPOT", *seq, "DEPOT"]
        return sum(d(path[i], path[i + 1]) for i in range(len(path) - 1))

    best = list(ordered)
    best_len = tour_length(best)
    improved = True
    while improved:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                cand = best[: i + 1] + list(reversed(best[i + 1 : j + 1])) + best[j + 1 :]
                cand_len = tour_length(cand)
                if cand_len < best_len - 1e-9:
                    best, best_len, improved = cand, cand_len, True
    return best


def _assemble(inp: VRPInput, ordered: list[str], unserved: list[str]) -> VRPOutput:
    by_id = {b["bin_id"]: b for b in inp.bins}
    legs: dict[str, float] = {}
    total = 0.0
    cur = (inp.depot_lat, inp.depot_lng)
    for bid in ordered:
        b = by_id[bid]
        leg = haversine_km(cur[0], cur[1], b["latitude"], b["longitude"]) * inp.road_factor
        legs[bid] = round(leg, 3)
        total += leg
        cur = (b["latitude"], b["longitude"])
    return_leg = haversine_km(cur[0], cur[1], inp.depot_lat, inp.depot_lng) * inp.road_factor

    status = "FEASIBLE" if not unserved else ("PARTIAL" if ordered else "INFEASIBLE")
    return VRPOutput(
        status=status,
        solver=SOLVER_HEURISTIC,
        ordered_bin_ids=ordered,
        leg_distances_km=legs,
        total_distance_km=round(total + return_leg, 3),
        return_leg_km=round(return_leg, 3),
        unserved_bin_ids=unserved,
    )


def route_distance_for_order(
    depot_lat: float, depot_lng: float, bins: list[dict], road_factor: float
) -> float:
    """Distance of depot → bins(in given order) → depot. Used for the baseline."""
    total = 0.0
    cur = (depot_lat, depot_lng)
    for b in bins:
        total += haversine_km(cur[0], cur[1], b["latitude"], b["longitude"]) * road_factor
        cur = (b["latitude"], b["longitude"])
    total += haversine_km(cur[0], cur[1], depot_lat, depot_lng) * road_factor
    return round(total, 3)
