"""Unit tests: solver feasibility + fuel math + forecast fallback."""
import math
from datetime import timedelta

from app.agents.fuel_agent import estimate_fuel
from app.forecasting.forecast import forecast_bin
from app.optimization.solver import VRPInput, route_distance_for_order, solve_vrp

DEPOT = {"lat": 26.9050, "lng": 75.7870}


def bin_dict(bid, lat, lng, demand):
    return {"bin_id": bid, "latitude": lat, "longitude": lng, "demand_litres": demand}


BINS = [
    bin_dict("BIN-A", 26.9138, 75.8070, 500),
    bin_dict("BIN-B", 26.9207, 75.8230, 600),
    bin_dict("BIN-C", 26.8560, 75.8130, 550),
    bin_dict("BIN-D", 26.9450, 75.7900, 700),
]


class TestSolver:
    def test_visits_only_candidates(self):
        out = solve_vrp(VRPInput(DEPOT["lat"], DEPOT["lng"], BINS, capacity_litres=5000))
        assert set(out.ordered_bin_ids) <= {b["bin_id"] for b in BINS}
        assert len(out.ordered_bin_ids) == len(set(out.ordered_bin_ids))  # no duplicates

    def test_capacity_respected_or_unserved(self):
        out = solve_vrp(VRPInput(DEPOT["lat"], DEPOT["lng"], BINS, capacity_litres=1000))
        by_id = {b["bin_id"]: b for b in BINS}
        served_load = sum(by_id[b]["demand_litres"] for b in out.ordered_bin_ids)
        assert served_load <= 1000 + 1e-6
        assert out.status in {"PARTIAL", "INFEASIBLE"}
        assert out.unserved_bin_ids  # overflow surfaced explicitly

    def test_feasible_when_capacity_sufficient(self):
        out = solve_vrp(VRPInput(DEPOT["lat"], DEPOT["lng"], BINS, capacity_litres=5000))
        assert out.status == "FEASIBLE"
        assert not out.unserved_bin_ids

    def test_total_distance_covers_return_leg(self):
        out = solve_vrp(VRPInput(DEPOT["lat"], DEPOT["lng"], BINS, capacity_litres=5000))
        assert out.total_distance_km > out.return_leg_km > 0

    def test_empty_candidates(self):
        out = solve_vrp(VRPInput(DEPOT["lat"], DEPOT["lng"], [], capacity_litres=5000))
        assert out.status == "FEASIBLE" and out.ordered_bin_ids == []

    def test_baseline_order_distance_positive(self):
        km = route_distance_for_order(DEPOT["lat"], DEPOT["lng"], BINS, 1.3)
        assert km > 0

    def test_optimized_not_worse_than_worst_order(self):
        """2-opt/OR-Tools result must beat visiting bins in the given (scattered) order."""
        optimized = solve_vrp(VRPInput(DEPOT["lat"], DEPOT["lng"], BINS, capacity_litres=5000))
        baseline = route_distance_for_order(DEPOT["lat"], DEPOT["lng"], BINS, 1.3)
        assert optimized.total_distance_km <= baseline + 0.001


class TestFuelAgent:
    def test_litres_and_cost_math(self):
        est = estimate_fuel(
            distance_km=100.0,
            consumption_l_per_100km=18.0,
            fuel_price_per_litre=94.5,
            baseline_distance_km=150.0,
        )
        assert math.isclose(est["estimated_fuel_litres"], 18.0, abs_tol=0.01)
        assert math.isclose(est["estimated_fuel_cost"], 18.0 * 94.5, abs_tol=0.1)
        assert est["savings_percent"] == 33.33  # (150-100)/150

    def test_no_baseline_no_savings(self):
        est = estimate_fuel(
            distance_km=50, consumption_l_per_100km=20, fuel_price_per_litre=90,
            baseline_distance_km=None,
        )
        assert est["savings_percent"] is None
        assert est["baseline"] is None

    def test_zero_baseline_no_division_by_zero(self):
        est = estimate_fuel(
            distance_km=50, consumption_l_per_100km=20, fuel_price_per_litre=90,
            baseline_distance_km=0.0,
        )
        assert est["savings_percent"] is None


class TestForecast:
    def test_insufficient_history(self):
        from app.core.utils import utcnow

        now = utcnow()
        pts = [(now - timedelta(hours=i), 50.0) for i in range(3)]
        fc = forecast_bin(pts, now, 24)
        assert fc["status"] == "insufficient_history"
        assert fc["points"] == []

    def test_short_span_insufficient(self):
        from app.core.utils import utcnow

        now = utcnow()
        # 8 readings only 15 minutes apart → ~1.75h span (< MIN_SPAN_HOURS)
        pts = [(now - timedelta(minutes=15 * i), 50.0 + i) for i in range(8)]
        fc = forecast_bin(pts, now, 24)
        assert fc["status"] == "insufficient_history"

    def test_valid_forecast_clamped_and_shaped(self):
        from app.core.utils import utcnow

        now = utcnow()
        # ~1.5%/hour growth over 48h
        pts = [(now - timedelta(hours=48 - i), 10 + 1.5 * i) for i in range(48)]
        fc = forecast_bin(pts, now, 12)
        assert fc["status"] == "ok"
        assert len(fc["points"]) == 12
        for p in fc["points"]:
            assert 0 <= p["predicted_fill_percent"] <= 100
            assert p["lower_bound"] <= p["predicted_fill_percent"] <= p["upper_bound"]
        # upward trend should project above the last reading
        assert fc["points"][-1]["predicted_fill_percent"] > pts[-1][1]

    def test_predictions_are_labelled(self):
        from app.core.utils import utcnow

        now = utcnow()
        pts = [(now - timedelta(hours=48 - i), 10 + 1.5 * i) for i in range(48)]
        fc = forecast_bin(pts, now, 6)
        assert "not sensor measurements" in fc["note"]
