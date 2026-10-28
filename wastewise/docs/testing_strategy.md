# WasteWise Testing Strategy

## Testing layers

### Unit tests
Test domain functions without a database or network:
- fill status and priority
- stale sensor detection
- fuel calculation
- route capacity validation
- distance calculations
- forecast baseline and clamping
- waste-category handling recommendations

### API integration tests
Use FastAPI TestClient/HTTPX and an isolated test database:
- health endpoint
- list/detail bins
- create readings and validate ranges
- unknown bin returns 404
- optimization request returns a documented state
- alerts can be acknowledged/resolved only through valid transitions
- pagination limits are enforced

### Workflow tests
Mock external adapters and verify:
- all agent nodes execute on success
- prediction failure allows current-reading route planning with warning
- infeasible route is not shown as a successful route
- optional recycling failure does not erase valid route output
- database persistence failure is surfaced as failure

### Frontend tests
- dashboard loading/error/empty states
- filters and navigation
- API error rendering
- optimization button disables while running
- route stops match API response
- accessibility labels and keyboard interaction

## Important numerical cases

Fuel:
- distance 0 -> fuel 0
- distance 10 km, consumption 20 L/100 km -> 2 L
- missing baseline -> savings is null
- negative distance or consumption -> validation error

Fill:
- 0 and 100 are valid
- -1 and 101 are invalid
- threshold boundaries are tested exactly
- stale readings are visibly stale

Routing:
- no candidate bins
- one candidate
- truck capacity exactly equals total demand
- total demand exceeds capacity
- missing coordinates
- disconnected/unavailable distance provider
- all bins served vs some unserved

Forecast:
- empty history
- one observation
- missing timestamps
- irregular sample frequency
- predicted values bounded to 0–100
- chronological train/test split for trained models

## Demo acceptance checklist

- [ ] Fresh install follows documentation.
- [ ] Dashboard loads from API-backed seeded data.
- [ ] Manual/simulated reading updates a bin.
- [ ] Bin status and reason are visible.
- [ ] Optimization creates a persisted run.
- [ ] Route feasibility and unserved bins are shown honestly.
- [ ] Fuel estimate displays assumptions.
- [ ] Forecast is labelled predicted.
- [ ] Recycling output includes source and review status.
- [ ] Agent Activity shows actual workflow node outcomes.
- [ ] Errors are visible and actionable.
- [ ] No secret or real personal data is committed.
