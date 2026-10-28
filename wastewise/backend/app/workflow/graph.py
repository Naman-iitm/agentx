"""LangGraph multi-agent workflow.

Graph (architecture.md §4):
    load_snapshot → bin_agent → prediction_agent → route_agent
                  → fuel_agent → recycling_agent → persist_result

Every node wraps a deterministic Python agent, records timing + status, and
isolates failures per agents_config.md §6:
- prediction fails  → route on current readings + warning
- recycling fails   → optimization still succeeds
- routing infeasible→ persist the failure and explain unserved bins
- persistence fails → surface a server error, never claim a saved run

State is the typed dict from architecture.md §4 plus runtime-only keys
(`db`, `ops`) holding non-serializable dependencies — stripped from results.
"""
import time
from datetime import datetime
from typing import Any, TypedDict

from sqlalchemy.orm import Session

from app.agents import bin_agent as bin_agent_mod
from app.agents import fuel_agent as fuel_agent_mod
from app.agents import prediction_agent as prediction_agent_mod
from app.agents import recycling_agent as recycling_agent_mod
from app.agents import route_agent as route_agent_mod
from app.core.utils import utcnow
from app.db.models import AgentRun, Bin, BinReading, OptimizationRun, RouteStop, WasteClassification


class OptimizationState(TypedDict, total=False):
    # contract fields (architecture.md §4)
    run_id: str
    requested_by: str
    bin_snapshots: list[dict]
    collection_candidates: list[dict]
    forecast_results: dict
    route_plan: dict
    fuel_estimate: dict
    recycling_insights: list[dict]
    warnings: list[str]
    status: str

    # runtime-only (never persisted / returned)
    db: Any
    ops: dict
    agent_results: list[dict]
    started_at: datetime


def _agent(state: "OptimizationState", name: str, status: str, summary: str,
           reasons: list[str], warnings: list[str], duration_ms: int) -> list[dict]:
    """Return the updated agent_results list (LangGraph merges the dict we return)."""
    results = list(state.get("agent_results") or [])
    results.append(
        {
            "agent_name": name,
            "status": status,
            "summary": summary,
            "reasons": reasons,
            "warnings": warnings,
            "duration_ms": duration_ms,
        }
    )
    return results


def _with_warnings(state: "OptimizationState", new: list[str]) -> list[str]:
    return list(state.get("warnings") or []) + new


# ------------------------------------------------------------------- nodes --

def load_snapshot_node(state: OptimizationState) -> dict:
    db: Session = state["db"]
    t0 = time.perf_counter()
    bins = db.query(Bin).filter(Bin.is_active.is_(True)).order_by(Bin.id).all()
    snapshots = []
    for b in bins:
        latest = (
            db.query(BinReading)
            .filter(BinReading.bin_id == b.id)
            .order_by(BinReading.measured_at.desc())
            .first()
        )
        snapshots.append(
            {
                "bin_id": b.id,
                "name": b.name,
                "zone": b.zone,
                "latitude": b.latitude,
                "longitude": b.longitude,
                "bin_type": b.bin_type,
                "capacity_litres": b.capacity_litres,
                "fill_percent": latest.fill_percent if latest else None,
                "measured_at": latest.measured_at if latest else None,
                "battery_percent": latest.battery_percent if latest else None,
                "reading_source": latest.source if latest else None,
            }
        )
    duration = int((time.perf_counter() - t0) * 1000)
    with_data = sum(1 for s in snapshots if s["fill_percent"] is not None)
    return {
        "bin_snapshots": snapshots,
        "agent_results": _agent(
            state, "load_snapshot", "success",
            f"Loaded {len(snapshots)} active bins ({with_data} with telemetry).",
            [], [], duration,
        ),
    }


def bin_agent_node(state: OptimizationState) -> dict:
    t0 = time.perf_counter()
    ops = state["ops"]
    results, candidates = [], []
    for snap in state["bin_snapshots"]:
        if snap["fill_percent"] is None:
            continue
        r = bin_agent_mod.evaluate_bin(
            snap,
            warning_threshold=ops["warning_threshold"],
            critical_threshold=ops["critical_threshold"],
            collection_threshold=ops["collection_threshold"],
            stale_after_hours=ops["stale_after_hours"],
            now=state["started_at"],
        )
        results.append(r)
        if r["should_collect"]:
            cand = dict(r)
            cand["bin_type"] = snap.get("bin_type", "general")
            cand["capacity_litres"] = snap.get("capacity_litres", 600)
            cand["demand_litres"] = round(
                snap["fill_percent"] / 100.0 * (snap["capacity_litres"] or 600), 2
            )
            candidates.append(cand)

    warnings = sorted({w for r in results for w in r["warnings"]})
    duration = int((time.perf_counter() - t0) * 1000)
    return {
        "collection_candidates": candidates,
        "warnings": _with_warnings(state, warnings),
        "agent_results": _agent(
            state, "bin_agent", "success",
            f"Evaluated {len(results)} bins; {len(candidates)} collection candidates.",
            [f"{c['bin_id']}: {'; '.join(c['reasons'])}" for c in candidates],
            warnings, duration,
        ),
    }


def prediction_agent_node(state: OptimizationState) -> dict:
    db: Session = state["db"]
    ops = state["ops"]
    t0 = time.perf_counter()
    warnings: list[str] = []
    forecast_results: dict = {}

    def history_for(bin_id: str):
        rows = (
            db.query(BinReading)
            .filter(BinReading.bin_id == bin_id)
            .order_by(BinReading.measured_at.asc())
            .all()
        )
        return [(r.measured_at, r.fill_percent) for r in rows]

    try:
        candidates = [dict(c) for c in state["collection_candidates"]]
        candidate_ids = {c["bin_id"] for c in candidates}

        if ops["include_predicted_overflow"]:
            for snap in state["bin_snapshots"]:
                if snap["fill_percent"] is None or snap["bin_id"] in candidate_ids:
                    continue
                fc = prediction_agent_mod.forecast_for_bin(
                    history_for(snap["bin_id"]), state["started_at"],
                    ops["planning_horizon_hours"],
                )
                forecast_results[snap["bin_id"]] = {
                    "status": fc["status"],
                    "predicted_fill_at_horizon": prediction_agent_mod.predicted_fill_at_horizon(fc),
                }
                will, value = prediction_agent_mod.predicted_overflow(fc, ops["critical_threshold"])
                if will:
                    extra = dict(snap)
                    extra.update(
                        {
                            "status": "WARNING",
                            "flags": ["PREDICTED_OVERFLOW"],
                            "is_stale": False,
                            "priority": round(value or snap["fill_percent"], 2),
                            "should_collect": True,
                            "reasons": [
                                f"Predicted to reach {value:.0f}% within "
                                f"{ops['planning_horizon_hours']}h horizon."
                            ],
                            "warnings": [],
                            "demand_litres": round(
                                (value or snap["fill_percent"]) / 100.0
                                * (snap["capacity_litres"] or 600),
                                2,
                            ),
                            "predicted_fill_at_horizon": value,
                        }
                    )
                    candidates.append(extra)
                    candidate_ids.add(snap["bin_id"])

        for c in candidates:
            bid = c["bin_id"]
            if bid not in forecast_results:
                fc = prediction_agent_mod.forecast_for_bin(
                    history_for(bid), state["started_at"], ops["planning_horizon_hours"]
                )
                forecast_results[bid] = {
                    "status": fc["status"],
                    "predicted_fill_at_horizon": prediction_agent_mod.predicted_fill_at_horizon(fc),
                }
                if fc["status"] != "ok":
                    warnings.append(f"{bid}: {fc.get('note', 'insufficient history')}")
            c["predicted_fill_at_horizon"] = forecast_results[bid]["predicted_fill_at_horizon"]

        added = sum(1 for c in candidates if "PREDICTED_OVERFLOW" in c.get("flags", []))
        duration = int((time.perf_counter() - t0) * 1000)
        return {
            "collection_candidates": candidates,
            "forecast_results": forecast_results,
            "warnings": _with_warnings(state, warnings),
            "agent_results": _agent(
                state, "prediction_agent", "success" if not warnings else "partial",
                f"Forecasts for {len(forecast_results)} bins; {added} added for predicted overflow.",
                [], warnings, duration,
            ),
        }
    except Exception as exc:  # noqa: BLE001 — degrade, keep optimizing on live data
        warnings.append(f"Prediction agent failed ({exc}); routing on current readings only.")
        return {
            "warnings": _with_warnings(state, warnings),
            "agent_results": _agent(state, "prediction_agent", "failed", f"Failed: {exc}",
                                    [], warnings, int((time.perf_counter() - t0) * 1000)),
        }


def route_agent_node(state: OptimizationState) -> dict:
    t0 = time.perf_counter()
    ops = state["ops"]
    try:
        plan = route_agent_mod.build_route(
            state["collection_candidates"],
            depot=ops["depot"],
            truck=ops["truck"],
            road_factor=ops["road_distance_factor"],
        )
        duration = int((time.perf_counter() - t0) * 1000)
        return {
            "route_plan": plan,
            "status": plan["status"],
            "warnings": _with_warnings(state, plan["warnings"]),
            "agent_results": _agent(
                state, "route_agent",
                "success" if plan["status"] == "FEASIBLE" else "partial",
                f"Route {plan['status'].lower()}: {len(plan['stops'])} stops, "
                f"{plan['total_distance_km']} km via {plan['solver'].split(' (')[0]}.",
                [f"Stop {s['sequence']}: {s['bin_id']} (+{s['distance_from_previous_km']} km)"
                 for s in plan["stops"][:8]],
                plan["warnings"], duration,
            ),
        }
    except Exception as exc:  # noqa: BLE001
        msg = f"Route agent failed: {exc}"
        return {
            "status": "FAILED",
            "warnings": _with_warnings(state, [msg]),
            "agent_results": _agent(state, "route_agent", "failed", msg, [], [msg],
                                    int((time.perf_counter() - t0) * 1000)),
        }


def fuel_agent_node(state: OptimizationState) -> dict:
    t0 = time.perf_counter()
    plan = state.get("route_plan") or {}
    ops = state["ops"]
    if not plan:
        msg = "Skipped — no route plan available."
        return {
            "warnings": _with_warnings(state, [msg]),
            "agent_results": _agent(state, "fuel_agent", "skipped", msg, [], [msg],
                                    int((time.perf_counter() - t0) * 1000)),
        }
    est = fuel_agent_mod.estimate_fuel(
        distance_km=plan["total_distance_km"],
        consumption_l_per_100km=ops["truck"]["consumption_l_per_100km"],
        fuel_price_per_litre=ops["fuel_price_per_litre"],
        baseline_distance_km=plan.get("baseline_distance_km"),
    )
    duration = int((time.perf_counter() - t0) * 1000)
    savings = est["savings_percent"]
    return {
        "fuel_estimate": est,
        "agent_results": _agent(
            state, "fuel_agent", "success",
            f"~{est['estimated_fuel_litres']} L (₹{est['estimated_fuel_cost']}) for "
            f"{est['distance_km']} km"
            + (f"; {savings}% cheaper than baseline." if savings is not None else "."),
            [], [est["note"]], duration,
        ),
    }


def recycling_agent_node(state: OptimizationState) -> dict:
    db: Session = state["db"]
    t0 = time.perf_counter()
    try:
        latest: dict[str, str] = {}
        for c in state["collection_candidates"]:
            row = (
                db.query(WasteClassification)
                .filter(WasteClassification.bin_id == c["bin_id"])
                .order_by(WasteClassification.created_at.desc())
                .first()
            )
            if row:
                latest[c["bin_id"]] = row.category
        insights = recycling_agent_mod.run_insights(state["collection_candidates"], latest)
        duration = int((time.perf_counter() - t0) * 1000)
        return {
            "recycling_insights": insights,
            "agent_results": _agent(
                state, "recycling_agent", "success",
                "Category mix: "
                + ", ".join(f"{k}×{v}" for k, v in sorted(insights["distribution"].items())) + ".",
                [r["recommendation"] for r in insights["recommendations"]],
                [insights["note"]], duration,
            ),
        }
    except Exception as exc:  # noqa: BLE001
        msg = f"Recycling agent failed ({exc}) — run result unaffected."
        return {
            "warnings": _with_warnings(state, [msg]),
            "agent_results": _agent(state, "recycling_agent", "failed", msg, [], [msg],
                                    int((time.perf_counter() - t0) * 1000)),
        }


def persist_result_node(state: OptimizationState) -> dict:
    db: Session = state["db"]
    ops = state["ops"]
    plan = state.get("route_plan") or {}
    fuel = state.get("fuel_estimate") or {}
    recycling = state.get("recycling_insights")
    completed = utcnow()
    started: datetime = state["started_at"]
    duration_ms = int((completed - started).total_seconds() * 1000)

    def _sel(c: dict) -> dict:
        return {
            "bin_id": c["bin_id"],
            "name": c.get("name", ""),
            "zone": c.get("zone", ""),
            "fill_percent": c.get("fill_percent", 0.0),
            "status": c.get("status", ""),
            "priority": c.get("priority", 0.0),
            "demand_litres": c.get("demand_litres", 0.0),
            "predicted_fill_at_horizon": c.get("predicted_fill_at_horizon"),
            "reasons": c.get("reasons", []),
        }

    snapshot = {
        "solver": plan.get("solver", ""),
        "algorithm_version": plan.get("algorithm_version", ""),
        "planning_horizon_hours": ops["planning_horizon_hours"],
        "bins_evaluated": sum(1 for s in state.get("bin_snapshots", []) if s["fill_percent"] is not None),
        "selected_bins": [_sel(c) for c in state.get("collection_candidates", [])],
        "stops": plan.get("stops", []),
        "unserved_bin_ids": plan.get("unserved_bin_ids", []),
        "total_distance_km": plan.get("total_distance_km", 0.0),
        "return_leg_km": plan.get("return_leg_km", 0.0),
        "estimated_fuel_litres": fuel.get("estimated_fuel_litres", 0.0),
        "estimated_fuel_cost": fuel.get("estimated_fuel_cost", 0.0),
        "baseline": fuel.get("baseline"),
        "savings_percent": fuel.get("savings_percent"),
        "warnings": state.get("warnings", []),
        "agents": state.get("agent_results", []),
        "recycling_summary": recycling,
        "duration_ms": duration_ms,
    }

    try:
        run = db.get(OptimizationRun, state["run_id"])
        run.status = state.get("status", "FAILED")
        run.solver_name = plan.get("solver", "")
        run.algorithm_version = plan.get("algorithm_version", "")
        run.total_distance_km = plan.get("total_distance_km", 0.0)
        run.baseline_distance_km = plan.get("baseline_distance_km")
        run.estimated_fuel_litres = fuel.get("estimated_fuel_litres", 0.0)
        run.estimated_fuel_cost = fuel.get("estimated_fuel_cost", 0.0)
        run.savings_percent = fuel.get("savings_percent")
        run.warnings = state.get("warnings", [])
        run.selected_bin_ids = [c["bin_id"] for c in state.get("collection_candidates", [])]
        run.result_snapshot = snapshot
        run.completed_at = completed

        for stop in plan.get("stops", []):
            db.add(
                RouteStop(
                    run_id=run.id,
                    sequence_number=stop["sequence"],
                    bin_id=stop["bin_id"],
                    distance_from_previous_km=stop["distance_from_previous_km"],
                    demand_estimate=stop["demand_litres"],
                )
            )
        for ar in state.get("agent_results", []):
            db.add(
                AgentRun(
                    optimization_run_id=run.id,
                    agent_name=ar["agent_name"],
                    status=ar["status"],
                    input_summary={},
                    output_summary={"summary": ar["summary"], "reasons": ar["reasons"]},
                    duration_ms=ar["duration_ms"],
                    warnings=ar["warnings"],
                    started_at=started,
                    completed_at=completed,
                )
            )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise RuntimeError(f"Run persistence failed: {exc}") from exc

    return {"status": state.get("status", "FAILED")}


# ------------------------------------------------------------------- graph --

def build_graph():
    """Compile the LangGraph workflow (sequential for easy debugging)."""
    from langgraph.graph import END, START, StateGraph

    g = StateGraph(OptimizationState)
    g.add_node("load_snapshot", load_snapshot_node)
    g.add_node("bin_agent", bin_agent_node)
    g.add_node("prediction_agent", prediction_agent_node)
    g.add_node("route_agent", route_agent_node)
    g.add_node("fuel_agent", fuel_agent_node)
    g.add_node("recycling_agent", recycling_agent_node)
    g.add_node("persist_result", persist_result_node)

    g.add_edge(START, "load_snapshot")
    g.add_edge("load_snapshot", "bin_agent")
    g.add_edge("bin_agent", "prediction_agent")
    g.add_edge("prediction_agent", "route_agent")
    g.add_edge("route_agent", "fuel_agent")
    g.add_edge("fuel_agent", "recycling_agent")
    g.add_edge("recycling_agent", "persist_result")
    g.add_edge("persist_result", END)
    return g.compile()


# Compiled once at import — the graph is stateless and safe to reuse.
try:
    workflow = build_graph()
except Exception:  # noqa: BLE001 — import still works without langgraph
    workflow = None
