# WasteWise Implementation Tasks and Acceptance Criteria

Build in the order below. Do not start the optional computer-vision model before the end-to-end core works.

## Phase 0 — Repository and agreements
- [ ] Create repo and copy all blueprint documents.
- [ ] Create `.env.example`, `.gitignore`, dependency configuration.
- [ ] Agree API contracts and domain enums before parallel code generation.
- [ ] Create a README with run commands and demo limitations.

**Exit criteria:** Clean repository structure and one agreed set of schemas.

## Phase 1 — Backend foundation
- [ ] FastAPI app, `/api/v1/health`, CORS from environment.
- [ ] Settings with Pydantic Settings.
- [ ] SQLAlchemy session and database models.
- [ ] Alembic migration and idempotent demo seed.
- [ ] Error response format, structured logging, request ID.
- [ ] CRUD/list endpoints for bins and readings.

**Exit criteria:** App starts; migrations and seed run; API docs load; tests pass.

## Phase 2 — Bin Agent and alerts
- [ ] Fill thresholds configurable.
- [ ] Stale reading detection.
- [ ] Priority result with explanation.
- [ ] Alert creation and state transitions.
- [ ] Unit tests for threshold boundaries and invalid values.

**Exit criteria:** 69%, 70%, 89%, and 90% test cases behave according to configuration.

## Phase 3 — Route and Fuel Agents
- [ ] Distance provider interface.
- [ ] OR-Tools VRP solver with capacity constraints.
- [ ] Small-data heuristic fallback, explicitly labelled.
- [ ] Route feasibility validator.
- [ ] Fuel litres and cost estimator.
- [ ] Baseline comparison only when baseline exists.

**Exit criteria:** Every returned route visits only candidates; capacity is respected or infeasibility is explicit.

## Phase 4 — Prediction and Recycling Agents
- [ ] History aggregation and rolling baseline.
- [ ] Insufficient-history response.
- [ ] Forecast API and evaluation tests.
- [ ] Operator-entered recycling categories.
- [ ] Handling recommendations and low-confidence review path.

**Exit criteria:** Prediction is distinguishable from measurement; unknown categories are handled safely.

## Phase 5 — Multi-agent workflow
- [ ] Typed workflow state.
- [ ] Nodes for all agents and optimization.
- [ ] Persist optimization run and agent execution records.
- [ ] Failure isolation and warnings.
- [ ] Integration tests for success, partial, and failure paths.

**Exit criteria:** One API call runs the complete workflow and persists a traceable result.

## Phase 6 — Frontend shell and dashboard
- [ ] Responsive app shell, navigation, loading/error/empty states.
- [ ] KPI cards and charts.
- [ ] Bin table and filters.
- [ ] API client and shared TypeScript types.

**Exit criteria:** No fake hardcoded KPIs when API data is available; demo data is labelled.

## Phase 7 — Map and planning UI
- [ ] Leaflet map with status markers.
- [ ] Bin detail drawer.
- [ ] Truck/depot selection.
- [ ] Run Optimization action and progress state.
- [ ] Ordered stops, route metrics, unserved bins, warnings.

**Exit criteria:** UI output matches API response and can explain why bins were selected.

## Phase 8 — Remaining pages
- [ ] Fleet & Fuel.
- [ ] Recycling Insights.
- [ ] Waste Forecasts.
- [ ] Agent Activity.
- [ ] Alerts.
- [ ] Settings and demo simulator controls.

**Exit criteria:** All navigation routes work; all pages handle empty/error/loading states.

## Phase 9 — Hardening
- [ ] Unit, API integration, and frontend tests.
- [ ] Input validation and file upload limits if vision is enabled.
- [ ] Authentication/role controls if deployed beyond a closed demo.
- [ ] Accessibility, responsive checks, performance checks.
- [ ] Database backup and deployment instructions.
- [ ] Document known limitations and data provenance.

**Exit criteria:** `pytest`, frontend tests, and production build pass; fresh-clone setup works from docs.

## Phase 10 — Optional integrations
- [ ] Real IoT device ingestion.
- [ ] Traffic-aware routing API adapter.
- [ ] YOLO-based waste classification.
- [ ] Real authentication provider.
- [ ] Scheduled forecast refresh and notifications.

Each optional integration requires a documented secret, fallback, timeout, rate limit, and test strategy.
