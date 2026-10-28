"""Optimization run orchestration — entry point for POST /optimization/runs."""
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.core.utils import utcnow
from app.db.models import AgentRun, AppSettings, Depot, OptimizationRun, RouteStop, Truck
from app.schemas.optimization import OptimizationRunIn
from app.services.settings_service import get_settings_row
from app.workflow import graph as wf


def _run_or_404(db: Session, run_id: str) -> OptimizationRun:
    run = db.get(OptimizationRun, run_id)
    if not run:
        raise not_found("optimization run", run_id)
    return run


def run_optimization(
    db: Session, req: OptimizationRunIn, requested_by: str | None
) -> dict:
    depot = db.get(Depot, req.depot_id)
    if not depot:
        raise not_found("depot", req.depot_id)
    truck = db.get(Truck, req.truck_id)
    if not truck:
        raise not_found("truck", req.truck_id)

    settings_row = get_settings_row(db)

    run = OptimizationRun(
        id=f"run_{uuid.uuid4().hex[:12]}",
        requested_by=requested_by,
        depot_id=depot.id,
        truck_id=truck.id,
        status="RUNNING",
        started_at=utcnow(),
    )
    db.add(run)
    db.commit()

    ops = {
        "depot": {"id": depot.id, "name": depot.name, "latitude": depot.latitude, "longitude": depot.longitude},
        "truck": {
            "id": truck.id,
            "name": truck.name,
            "capacity_litres": truck.capacity_litres,
            "consumption_l_per_100km": truck.consumption_l_per_100km,
        },
        "warning_threshold": settings_row.warning_threshold,
        "critical_threshold": settings_row.critical_threshold,
        "collection_threshold": settings_row.collection_threshold,
        "stale_after_hours": settings_row.stale_after_hours,
        "fuel_price_per_litre": settings_row.fuel_price_per_litre,
        "road_distance_factor": settings_row.road_distance_factor,
        "planning_horizon_hours": req.planning_horizon_hours,
        "include_predicted_overflow": req.include_predicted_overflow,
    }

    state: dict = {
        "run_id": run.id,
        "requested_by": requested_by,
        "warnings": [],
        "status": "RUNNING",
        "started_at": run.started_at,
        "db": db,
        "ops": ops,
        "agent_results": [],
    }

    if wf.workflow is not None:
        wf.workflow.invoke(state, config={"recursion_limit": 50})
    else:  # graceful degradation if langgraph is unavailable
        for node in (
            wf.load_snapshot_node, wf.bin_agent_node, wf.prediction_agent_node,
            wf.route_agent_node, wf.fuel_agent_node, wf.recycling_agent_node,
            wf.persist_result_node,
        ):
            state.update(node(state))

    return build_run_detail(db, run.id)


def build_run_detail(db: Session, run_id: str) -> dict:
    """Full run response — from the persisted snapshot + normalized tables."""
    run = _run_or_404(db, run_id)
    detail = dict(run.result_snapshot or {})
    detail.update(
        {
            "run_id": run.id,
            "status": run.status,
            "requested_by": run.requested_by,
            "depot_id": run.depot_id,
            "truck_id": run.truck_id,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
        }
    )
    return detail


def list_runs(db: Session, limit: int, offset: int) -> dict:
    q = db.query(OptimizationRun).order_by(OptimizationRun.started_at.desc())
    total = q.count()
    runs = q.offset(offset).limit(limit).all()
    items = []
    for r in runs:
        agents = (
            db.query(AgentRun)
            .filter(AgentRun.optimization_run_id == r.id)
            .order_by(AgentRun.id)
            .all()
        )
        items.append(
            {
                "run_id": r.id,
                "status": r.status,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "total_distance_km": r.total_distance_km,
                "estimated_fuel_litres": r.estimated_fuel_litres,
                "estimated_fuel_cost": r.estimated_fuel_cost,
                "savings_percent": r.savings_percent,
                "selected_count": len(r.selected_bin_ids or []),
                "solver": r.solver_name,
                "warnings": r.warnings or [],
                "agents": [
                    {
                        "agent_name": a.agent_name,
                        "status": a.status,
                        "duration_ms": a.duration_ms,
                        "warnings": a.warnings or [],
                    }
                    for a in agents
                ],
            }
        )
    return {"items": items, "total": total, "limit": limit, "offset": offset}
