# WasteWise Agent Configuration and Contracts

## Design principle

Agents are **bounded software components** with explicit inputs and outputs. The term "agent" does not mean every component must call an LLM. The numerical core must be deterministic and unit-tested. If an LLM is added, use it only for optional natural-language summaries or ambiguous unstructured inputs, never as the source of truth for calculations.

## Shared contract

Each agent should expose a function or class method with:
- validated input data,
- typed output data,
- `status`,
- `warnings`,
- `method` or `version`,
- structured decision reasons.

Example shared response:

```python
from pydantic import BaseModel, Field
from typing import Literal

class AgentResult(BaseModel):
    agent_name: str
    status: Literal["success", "partial", "skipped", "failed"]
    summary: str
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    duration_ms: int | None = None
```

## 1. Bin Agent

**Purpose:** Convert current bin telemetry into understandable state and collection priority.

### Input
- `bin_id`
- `fill_percent` (0–100)
- `measured_at`
- optional `battery_percent`
- optional sensor confidence / quality flag
- configured thresholds and stale-reading duration

### Rules
- `fill_percent >= critical_threshold`: `CRITICAL`
- else if `fill_percent >= warning_threshold`: `WARNING`
- else: `NORMAL`
- if timestamp is older than configured stale limit: add `STALE` flag, do not pretend the measurement is live.
- Priority score can start as `fill_percent`, with deterministic bonuses for critical status, long time since collection, and predicted overflow. Document exact formula and version it.

Example priority formula:
`priority = min(100, 0.70 * fill_percent + 0.20 * overdue_score + 0.10 * predicted_overflow_score)`
Each component must be scaled to 0–100. Do not use this formula until all input terms are implemented; for the first version use `priority = fill_percent` and document that simplification.

### Output
- state / flags
- priority score
- `should_collect`
- human-readable reasons

## 2. Route Agent

**Purpose:** Build a route that visits selected collection candidates.

### Inputs
- selected bin IDs with latitude/longitude and demand estimate
- depot coordinates
- one or more trucks with capacity
- distance matrix or a distance-provider adapter
- optional time/cost constraints

### Required behaviour
- Validate all coordinates and demands.
- Never include a bin that is not a candidate.
- Respect vehicle capacity or return a clear infeasible/partial status.
- Use OR-Tools Vehicle Routing Problem (VRP) when available.
- For the first tiny demo, a nearest-neighbour fallback is acceptable but must be labelled heuristic, not globally optimal.
- Return ordered stops, per-leg distance, total distance, estimated duration if supported, unserved bins, solver name, and warnings.

### Output contract sketch
```json
{
  "status": "FEASIBLE",
  "solver": "OR-Tools",
  "route_id": "route_demo_001",
  "truck_id": "truck_01",
  "stops": [
    {"sequence": 1, "bin_id": "BIN-012", "distance_from_previous_km": 1.8}
  ],
  "total_distance_km": 12.4,
  "unserved_bin_ids": [],
  "warnings": []
}
```

## 3. Fuel Agent

**Purpose:** Estimate fuel use and cost from the actual route distance.

### Configuration
- `fuel_consumption_l_per_100km`, e.g. 18.0 for demo only.
- `fuel_price_per_litre`, e.g. a configurable demo assumption.
- optional idle-time / load factor, only if data is available.

### Formula
`litres = distance_km * consumption_l_per_100km / 100`
`fuel_cost = litres * fuel_price_per_litre`

Return rounded display values but preserve sufficient precision internally. State that the first version is an estimate and excludes idling, road grade, congestion, payload variation, and maintenance.

### Savings
Compare with a defined baseline route, not an invented number:
`savings_percent = 100 * (baseline_cost - optimized_cost) / baseline_cost`
If baseline cost is zero or missing, return `null` rather than divide by zero.

## 4. Recycling Agent

**Purpose:** Classify waste records and recommend handling.

### Initial supported labels
- `ORGANIC`
- `PAPER`
- `PLASTIC`
- `METAL`
- `GLASS`
- `E_WASTE`
- `HAZARDOUS`
- `MIXED`
- `UNKNOWN`

### Input modes
1. MVP: operator selects or imports a category.
2. Extension: upload an image; validate MIME type and size; run an image classifier.
3. Optional: detect multiple objects using a compatible vision model.

### Rules
- Return class, confidence if model-provided, model/version, and handling recommendation.
- Low confidence below a configurable threshold must yield `UNKNOWN` or `REVIEW_REQUIRED`.
- Never claim that an image classifier is a certified hazardous-waste detector. Hazardous items require human review.
- Avoid sending uploaded images to third-party APIs without explicit disclosure and consent.

## 5. Prediction Agent

**Purpose:** Forecast fill levels or generated waste for a configurable horizon.

### MVP baseline
- Aggregate historical measurements by bin and time bucket.
- Use a rolling average / last-observation baseline if history is sparse.
- Return `insufficient_history` when there is not enough valid history for a meaningful forecast.
- Clamp physical fill predictions to 0–100%.
- Never present a prediction as a measured sensor reading.

### Later model
- Features may include hour, weekday, holiday flag, zone, bin category, lagged fill values, and collection events.
- Use time-based train/test split, not random row split.
- Report MAE or another suitable error metric on held-out periods.
- Include model version and forecast generation timestamp.

## 6. Workflow and failure handling

Recommended graph:
`load_data -> bin_agent -> prediction_agent -> route_agent -> fuel_agent -> recycling_agent -> persist`

- If prediction fails, route using current readings and attach a warning.
- If recycling fails, optimization may still succeed.
- If routing is infeasible, do not fabricate a route; persist the failure and explain unserved bins.
- If database persistence fails, return a server error and log a run correlation ID; do not report a saved run.
- Each node should be idempotent where practical.
- Record agent start/end times and outputs for the Agent Activity page.

## 7. LLM usage policy

An LLM may:
- produce a plain-language explanation from already-computed structured results,
- answer questions about documented dashboard metrics,
- help map a user-uploaded textual waste description to candidate categories, with review.

An LLM must not:
- invent fill readings, GPS coordinates, road distances, fuel prices, or model accuracy,
- override truck capacity constraints,
- create a route without passing it through feasibility validation,
- make unreviewed hazardous-waste decisions.
