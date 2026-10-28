# Coding Assistant Prompt Pack — WasteWise

## How to use these prompts

1. Give the assistant `README.md`, `architecture.md`, `agents_config.md`, `api_contract.md`, `data_model.md`, `tasks.md`, and `security_and_ethics.md`.
2. Ask it to inspect the existing repository before writing anything.
3. Implement only one phase at a time.
4. Require complete files, tests, commands, and a summary of changed paths.
5. Run the code and tests locally before proceeding. Never accept a claim that tests passed unless the tool actually ran them.

## Master instruction (paste first)

```text
You are the senior engineer implementing WasteWise: AI-Powered Waste Management.
Treat the supplied project documents as the source of truth. Read them before coding.
Do not silently change API contracts, enum names, domain rules, or folder structure.
Build a working, testable MVP before optional integrations. Use deterministic logic for
fill priority, routing feasibility, and fuel calculations. LangGraph coordinates typed
agent steps; an LLM is not required for numerical decisions. Never fabricate sensor data,
coordinates, route distance, fuel savings, or model accuracy. Label demo/simulated values.
Before editing, inspect the repository and report what exists. Then implement only the
requested phase, run relevant tests/build commands, fix failures, and report exact files
changed, commands executed, results, known limitations, and the next phase. Do not claim
tests passed unless you actually ran them.
```

## Prompt 1 — Audit and plan

```text
Read all WasteWise project documents. Inspect the current repository without overwriting
existing work. Compare actual files against the architecture and tasks checklist. Return:
(1) current state, (2) missing files, (3) dependency conflicts, (4) exact Phase 1 plan.
Do not implement yet.
```

## Prompt 2 — Backend foundation

```text
Implement Phase 1 from tasks.md only. Create the FastAPI app, configuration, SQLAlchemy
session/models, Alembic setup, health endpoint, bin/readings schemas and CRUD endpoints,
idempotent demo seed, and tests. Follow api_contract.md and data_model.md exactly.
Keep route handlers thin. Provide complete changed files and run pytest.
```

## Prompt 3 — Bin Agent and alerts

```text
Implement Phase 2 only. Build the Bin Agent as a deterministic, typed service; add stale
reading logic and alert lifecycle. Keep thresholds configurable. Add tests for every
threshold boundary, invalid percentage, stale reading, and alert state transition.
Do not add LLM calls.
```

## Prompt 4 — Routing and fuel

```text
Implement Phase 3 only. Build a distance-provider interface, OR-Tools vehicle-routing
solver with truck capacity, feasibility validation, and an explicitly labelled heuristic
fallback for small demos. Implement Fuel Agent using the documented formula. Add tests
for zero distance, missing baseline, capacity overflow, empty candidates, and infeasible
routes. Never label a heuristic as globally optimal.
```

## Prompt 5 — Prediction and recycling

```text
Implement Phase 4 only. Add a rolling-baseline forecast, history sufficiency checks,
forecast schemas/endpoints, category-based recycling service, and safe handling guidance.
Separate predicted values from measured readings. Add tests for sparse history, bounded
predictions, unknown category, and low-confidence review.
```

## Prompt 6 — Multi-agent workflow

```text
Implement Phase 5 using LangGraph and the typed state in agents_config.md. Connect the
existing services rather than duplicating their business logic. Persist optimization runs,
route stops, and agent execution summaries. Handle optional agent failure without fake
success. Add end-to-end tests for success, partial, and failure paths.
```

## Prompt 7 — Frontend shell

```text
Implement Phase 6 in the existing React + Vite + TypeScript frontend. Create a professional
municipal control-tower layout: light theme, white/slate/navy palette, accessible contrast,
responsive sidebar, compact KPI cards, clear typography, loading/error/empty states.
Use the API client and shared TypeScript types. Do not use cyberpunk styling or fabricate
live metrics. Run lint/tests/build and fix errors.
```

## Prompt 8 — Map and collection planner

```text
Implement Phase 7. Add the Leaflet bin map, filters, bin detail panel, depot/truck selectors,
Run Optimization action, progress/error states, ordered route stops, distance/fuel metrics,
unserved bins, and agent warnings. The UI must display API-returned values, not independently
recalculate them. Label estimated distances and simulated data.
```

## Prompt 9 — Remaining dashboard pages

```text
Implement Phase 8 page-by-page: Fleet & Fuel, Recycling Insights, Waste Forecasts, Agent
Activity, Alerts, Settings. Connect every page to the documented API. Add accessible charts,
filters, empty states, error states, and responsive behaviour. Do not leave dead navigation
items or buttons without actions.
```

## Prompt 10 — QA and release

```text
Run the complete test suite, type checks, frontend production build, migration check, and
fresh-start setup. Fix actual failures. Review security_and_ethics.md and deployment_guide.md.
Return a release checklist, test results, demo script, known limitations, and exact local
run commands. Do not claim production readiness if authentication, secrets, migrations,
monitoring, or deployment security remain incomplete.
```

## Parallel coding rules

Safe to parallelize after contracts are agreed:
- Frontend shell and backend agent implementation can proceed independently.
- Documentation and test writing can proceed in parallel.
- Do not let two agents edit the same shared schema, router, package manifest, or main app entry point simultaneously.
- Assign file ownership and integrate changes through reviewed commits.
- The integration owner must run the complete test/build suite after every merge.


## Prompt 11 — Fix a bug without regressions

```text
Reproduce the bug first. Identify the failing test or exact observed behaviour. Make the
smallest correct change, add a regression test, run the targeted test and then the relevant
full suite. Do not refactor unrelated modules or change API contracts. Report root cause,
files changed, commands and test output.
```

## Prompt 12 — Review generated code

```text
Perform a senior-engineer review against the WasteWise documents. Look for fabricated
metrics, route feasibility bugs, stale-reading errors, missing validation, secret exposure,
unhandled API failures, duplicate business logic, untested boundaries, accessibility issues,
and misleading claims about AI. Report findings by severity with file/line references.
Do not modify files until I approve the review.
```
