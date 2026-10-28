# WasteWise: AI-Powered Waste Management

**Project type:** Full-stack smart-city waste collection and optimization platform  
**Primary goal:** Monitor bin fill levels, prioritize collection, optimize truck routes, estimate fuel usage, identify recyclable waste, and forecast future waste generation.

## 1. Product vision

WasteWise is a decision-support platform for municipal waste operations. It combines IoT-style bin telemetry, five cooperating agents, geographic visualization, route optimization, recycling insights, and forecasting in one control-tower dashboard.

### Core agents
1. **Bin Agent** — validates sensor readings, calculates fill status, and prioritizes collection.
2. **Route Agent** — creates a feasible collection route using selected bins, truck capacity, depot location, and travel-distance data.
3. **Fuel Agent** — estimates fuel consumption, fuel cost, and baseline-versus-optimized savings.
4. **Recycling Agent** — classifies waste records or uploaded images into supported waste categories and recommends handling.
5. **Prediction Agent** — forecasts future fill levels / waste generation from timestamped historical data.

## 2. MVP scope

The first complete demo must work without physical hardware or paid API keys.

- Seeded demo bins, trucks, depots, and historical measurements.
- Live-simulation mode that updates fill levels on a timer or by a manual button.
- Dashboard KPIs, bin table, map, alerts, agent run page, routes, recycling analytics, forecast chart, and settings.
- One-click **Run Optimization** workflow:
  1. Read current bin telemetry.
  2. Select bins needing collection.
  3. Build a route using a deterministic optimizer.
  4. Estimate fuel and cost.
  5. Produce a run summary and persist it.
- Simulated telemetry is clearly labelled **Demo / Simulated**. Never imply that real sensors are connected when they are not.

## 3. Recommended stack

- Frontend: React, Vite, TypeScript, Tailwind CSS, a chart library, Leaflet / React Leaflet.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic.
- Persistence: PostgreSQL + PostGIS in the full deployment; SQLite may be used for the first local prototype if documented.
- Agent orchestration: LangGraph, with typed state and deterministic tools.
- Optimization: Google OR-Tools for vehicle routing; provide a deterministic fallback for small demos if OR-Tools is unavailable.
- Forecasting: pandas + scikit-learn baseline model; start with a transparent rolling-average baseline before a more complex model.
- Optional vision: OpenCV + Ultralytics YOLO. Image classification is an extension, not a blocker for the core MVP.
- Tests: Pytest, HTTPX, Vitest, React Testing Library.
- Local deployment: Docker Compose.

## 4. Repository structure

```text
wastewise/
├── README.md
├── architecture.md
├── agents_config.md
├── setup_guide.md
├── tasks.md
├── prompt_templates.md
├── api_contract.md
├── data_model.md
├── testing_strategy.md
├── deployment_guide.md
├── security_and_ethics.md
├── .env.example
├── docker-compose.yml
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/config.py
│   │   ├── db/session.py
│   │   ├── db/models.py
│   │   ├── schemas/
│   │   ├── api/routes/
│   │   ├── services/
│   │   ├── agents/
│   │   ├── optimization/
│   │   ├── forecasting/
│   │   ├── vision/
│   │   └── seed/
│   └── tests/
└── frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── app/
        ├── components/
        ├── features/
        ├── pages/
        ├── services/
        ├── hooks/
        ├── types/
        └── styles/
```

## 5. Quick-start order

Follow `docs/setup_guide.md` (or `setup_guide.md` at repository root), then execute phases in `tasks.md`. Feed the project documents to your coding assistant before asking it to generate code. Build backend foundations first, then deterministic agents and tests, then frontend pages, then optional AI/IoT integrations.

## 6. Non-negotiable engineering rules

- Keep business logic out of React components and FastAPI route handlers.
- Validate every incoming request with Pydantic.
- Use typed interfaces between agents; agents must not pass free-form text as machine-readable state.
- Never let an LLM invent sensor readings, coordinates, fuel prices, or route distances.
- Mark synthetic data and model-generated classifications as estimates.
- Route optimization must enforce truck capacity and visit only selected bins.
- Store timestamps in UTC; convert to local time only in the UI.
- Keep secrets in environment variables; never commit `.env`.
- Include tests for fill-priority rules, route feasibility, fuel math, and forecast fallback.
- If an external map/traffic API is unavailable, use documented straight-line or local-road-distance approximations and label them.
