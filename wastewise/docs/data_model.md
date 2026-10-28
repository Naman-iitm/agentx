# WasteWise Data Model

## Entities

### `bins`
- `id` UUID or stable string primary key
- `external_code` unique human-readable identifier
- `name`
- `zone`
- `latitude`, `longitude`
- `bin_type` (general, organic, recycling, etc.)
- `capacity_litres` nullable
- `is_active`
- `created_at`, `updated_at`

### `bin_readings`
- `id`
- `bin_id` foreign key
- `fill_percent` numeric 0–100
- `measured_at` timestamp UTC
- `source` (`sensor`, `simulator`, `manual`, `import`)
- `battery_percent` nullable
- `quality_flag` (`GOOD`, `SUSPECT`, `STALE`)
- `created_at`

Index `(bin_id, measured_at DESC)`.

### `trucks`
- `id`, `name`, `registration_label`
- `capacity_litres` or a clearly documented demand unit
- `fuel_type`
- `consumption_l_per_100km`
- `is_active`
- `created_at`, `updated_at`

### `depots`
- `id`, `name`, `latitude`, `longitude`, `is_active`

### `optimization_runs`
- `id`
- `requested_by` nullable for demo
- `depot_id`, `truck_id`
- `status` (`PENDING`, `RUNNING`, `FEASIBLE`, `PARTIAL`, `INFEASIBLE`, `FAILED`)
- `solver_name`, `algorithm_version`
- `total_distance_km`, `estimated_fuel_litres`, `estimated_fuel_cost`
- `baseline_distance_km` nullable
- `warnings` JSON
- `started_at`, `completed_at`
- `created_at`

### `route_stops`
- `id`, `run_id`, `sequence_number`, `bin_id`
- `distance_from_previous_km`
- `demand_estimate`
- `collected` boolean default false
- unique `(run_id, sequence_number)`

### `agent_runs`
- `id`, `optimization_run_id`
- `agent_name`, `status`
- `input_summary` JSON (avoid sensitive data)
- `output_summary` JSON
- `duration_ms`
- `warnings` JSON
- `started_at`, `completed_at`

### `waste_classifications`
- `id`, `bin_id` nullable, `image_reference` nullable
- `category`, `confidence` nullable
- `source` (`operator`, `model`, `import`)
- `model_version` nullable
- `review_status`
- `created_at`

### `forecasts`
- `id`, `bin_id`
- `target_at`, `predicted_fill_percent`
- `method`, `model_version` nullable
- `generated_at`
- `lower_bound`, `upper_bound` nullable
- `evaluation_metadata` JSON nullable

### `alerts`
- `id`, `bin_id` nullable
- `type`, `severity`, `status`
- `title`, `message`
- `created_at`, `acknowledged_at`, `resolved_at`
- `acknowledged_by`, `resolved_by`

### `audit_events`
- `id`, `actor_id` nullable
- `action`, `resource_type`, `resource_id`
- `details` JSON
- `created_at`

## Relationships

- One bin has many readings, forecasts, classifications, alerts, and route-stop records.
- One optimization run has many route stops and agent-run records.
- One truck and one depot can be referenced by many optimization runs.

## Geographic storage

With PostgreSQL/PostGIS, store coordinates as geography/geometry points and add a spatial index when spatial queries are required. Keep latitude and longitude validation even when PostGIS is enabled. For the first prototype, separate float columns are acceptable.

## Migration rules

- Use Alembic migrations for schema changes.
- Never rely on `create_all()` as the production migration strategy.
- Seed demo data through an idempotent script; rerunning it must not duplicate rows.
- Use foreign keys and delete policies deliberately. Prefer soft deactivation for bins/trucks referenced by historical runs.
