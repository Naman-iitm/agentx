# WasteWise API Contract

Base prefix: `/api/v1`

All timestamps use ISO 8601 UTC, e.g. `2026-10-27T10:30:00Z`. JSON errors should use FastAPI's validation detail where appropriate or this consistent application shape:

```json
{
  "error": {
    "code": "BIN_NOT_FOUND",
    "message": "The requested bin does not exist.",
    "request_id": "req_..."
  }
}
```

## Health

### `GET /health`
Response:
```json
{"status": "ok", "service": "wastewise-api", "version": "0.1.0"}
```

## Bins

### `GET /bins`
Query parameters: `zone`, `status`, `limit` (default 50, max 200), `offset` (default 0).  
Response:
```json
{"items":[{"id":"BIN-001","name":"Market Road Bin 1","zone":"Central","latitude":28.6139,"longitude":77.2090,"fill_percent":92.0,"status":"CRITICAL","measured_at":"2026-10-27T10:30:00Z"}],"total":1,"limit":50,"offset":0}
```

### `GET /bins/{bin_id}`
Returns bin metadata and latest reading. Return 404 for unknown IDs.

### `POST /bins/{bin_id}/readings`
Request:
```json
{"fill_percent":82.5,"measured_at":"2026-10-27T10:30:00Z","source":"simulator","battery_percent":88}
```
Validate fill/battery percentages in 0–100. The backend calculates status; clients must not choose status.

### `GET /bins/{bin_id}/readings?limit=100`
Returns readings newest first with pagination.

### `POST /demo/simulate`
Updates seeded demo telemetry. Only enabled when `DEMO_MODE=true`; must not be exposed as an unrestricted production endpoint.

## Optimization

### `POST /optimization/runs`
Request:
```json
{
  "depot_id": "DEPOT-001",
  "truck_id": "TRUCK-001",
  "planning_horizon_hours": 12,
  "include_predicted_overflow": true
}
```
Response should include `run_id`, status, selected bins, route stops, distance, estimated fuel/cost, warnings, and per-agent statuses. If processing becomes long-running, return `202 Accepted` with a run ID and expose `GET /optimization/runs/{run_id}`.

### `GET /optimization/runs`
Paginated history.

### `GET /optimization/runs/{run_id}`
Returns full result and agent logs.

## Forecasts

### `GET /forecasts?bin_id=BIN-001&horizon_hours=24`
Returns forecast points with `predicted_fill_percent`, timestamp, method, model version, and warnings. If history is inadequate, return a valid response with `status: "insufficient_history"` rather than fabricating confidence.

## Recycling

### `POST /recycling/classifications`
For MVP category input:
```json
{"bin_id":"BIN-001","category":"PLASTIC","source":"operator"}
```
Image upload should use a separate multipart endpoint, size limits, and file-type checks. Do not store uploaded files permanently unless configured.

## Alerts

### `GET /alerts?status=OPEN&severity=HIGH&limit=50&offset=0`
### `POST /alerts/{alert_id}/acknowledge`
### `POST /alerts/{alert_id}/resolve`

Alerts include type, severity, bin ID, created time, status, and reason. State transitions must be validated.

## Settings

### `GET /settings`
Returns safe operational settings only; never return secrets.
### `PATCH /settings`
Requires operator/admin permission and validation. Record an audit event.

## API conventions

- Use response schemas for every endpoint.
- Return 201 for created resources, 202 for accepted asynchronous work, 204 only when no body is intended, 400 for invalid business operations, 404 for missing records, 409 for conflicting state, and 422 for schema validation errors.
- Use pagination on list endpoints.
- Keep database operations in service/repository functions, not route handlers.
- Version any breaking contract changes.
