# WasteWise: AI-Powered Waste Management

**A complete, working, exhibition-ready demo** — smart dustbin fill monitoring, intelligent collection scheduling, fuel-efficient truck routing, recycling insights and waste-generation forecasting, powered by a five-agent workflow.

> 🟢 **Status: end-to-end working.** Backend: 54/54 tests passing. Frontend: production build clean. Everything runs locally with **zero API keys and zero hardware** (seeded, clearly-labelled demo data).

---

## 🚀 Quick start (2 terminals)

**Prerequisites:** Python 3.12+, Node.js 20+.

```bash
# Terminal 1 — backend (FastAPI + SQLite + agents)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# → API docs: http://localhost:8000/docs

# Terminal 2 — frontend (React control tower)
cd frontend
npm install
npm run dev
# → Dashboard: http://localhost:5173
```

The database is created and seeded automatically on first start (12 demo bins across Jaipur, 3 trucks, 1 depot, 48h of simulated history, alerts, classifications).

**Run the tests:**

```bash
cd backend && python -m pytest tests/ -q   # 54 tests
cd frontend && npm run build               # type-check + production build
```

## 🤖 The one-click demo (exhibition script)

1. **Overview** — KPIs, distribution, open alerts (all live from the API)
2. Hit **⚡ Simulate tick** — bins fill up, new alerts appear
3. Open **Collection Planner** → **▶ Run Optimization** — watch the LangGraph pipeline: `load_snapshot → bin_agent → prediction_agent → route_agent → fuel_agent → recycling_agent → persist`
4. Show the result: selected bins **with reasons**, OR-Tools route on the map, fuel cost + savings vs baseline, recycling mix
5. **Forecasts** — pick a bin, show history vs prediction with uncertainty band
6. **Agent Activity** — full traceability of the last run
7. **Settings** — change thresholds live (validated + audited), regenerate demo data

## 🧠 The five agents

| Agent | What it does | How (deterministic, versioned) |
| --- | --- | --- |
| **Bin Agent** | Status + collection priority from telemetry | Thresholds (70/90 default), stale detection, priority = fill (v1, documented simplification) |
| **Route Agent** | Feasible collection route | **Google OR-Tools CVRP** with capacity constraints + drop penalties; nearest-neighbour + 2-opt fallback (labelled heuristic) |
| **Fuel Agent** | Litres, cost, savings | `litres = km × L/100km ÷ 100`, compared to a *documented* baseline (priority-order tour) |
| **Recycling Agent** | Categories + handling recommendations | Rules-based (`rules-v1`), hazardous → mandatory human review |
| **Prediction Agent** | Fill-level forecasts | Transparent rolling-slope baseline with uncertainty bands; `insufficient_history` instead of fabricated confidence |

Orchestration is a **LangGraph** `StateGraph` with typed state, per-node timing and failure isolation (prediction fails → route on live readings; recycling fails → run still succeeds; infeasible → persisted honestly with unserved bins). **No LLM is used for any numerical decision** — by design (see `docs/agents_config.md`).

## 🏗️ Architecture

```
React + Vite + TS + Tailwind (control tower, 10 pages)
        │  /api/v1 (REST, versioned, validated, paginated)
FastAPI ── services ── LangGraph workflow ── agents (deterministic)
   │                        │
 SQLAlchemy            OR-Tools VRP + forecast baseline
   │
 SQLite (prototype) → PostgreSQL + PostGIS (docker-compose target)
```

**Repo layout:**

```
wastewise/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # thin HTTP handlers
│   │   ├── services/        # use-cases (no HTTP logic)
│   │   ├── agents/          # the 5 agents (pure, testable)
│   │   ├── workflow/        # LangGraph graph
│   │   ├── optimization/    # OR-Tools VRP + heuristic fallback
│   │   ├── forecasting/     # rolling-slope baseline
│   │   ├── schemas/         # Pydantic contracts
│   │   ├── db/              # SQLAlchemy models
│   │   ├── seed/            # idempotent demo seed (Jaipur)
│   │   └── core/            # config, errors, utils
│   └── tests/               # 54 tests (agents, solver, API e2e)
├── frontend/
│   └── src/
│       ├── pages/           # 10 dashboard pages
│       ├── components/      # UI kit, SVG charts, SVG city map
│       ├── api.ts / types.ts
│       └── styles.css       # Tailwind v4 theme
├── docs/                    # the full blueprint pack (specs of record)
├── docker-compose.yml       # postgres + api + frontend target
└── .env.example
```

## 📊 Dashboard pages

Overview (KPIs) · Live Bin Map (SVG schematic, offline-safe) · Bins & Sensors (table + reading drill-down + demo ingest) · **Collection Planner** (run the workflow, explainable results) · Fleet & Fuel · Recycling Insights · Waste Forecasts · Agent Activity (traceability) · Alerts (validated transitions) · Settings (audited).

The map is an **offline SVG schematic** plotted from real coordinates (Leaflet/OSM swap-in is documented in `docs/architecture.md` §7 — tiles require internet, the schematic never does, which is what you want at an exhibition).

## ⚙️ API (v1, prefix `/api/v1`)

`GET /health` · `GET /bins` (+filters) · `GET/POST /bins/{id}/readings` · `POST /demo/simulate` · `POST /demo/reset` · `POST /optimization/runs` · `GET /optimization/runs[/{id}|/latest]` · `GET /forecasts` · `GET/POST /recycling/classifications` · `GET /recycling/summary` · `GET /alerts` (+acknowledge/resolve) · `GET /fleet/trucks|depots` · `GET/PATCH /settings` · `GET /dashboard/summary`

Full contracts with examples: `docs/api_contract.md`. Interactive: `http://localhost:8000/docs`.

## 🔍 Honest engineering (what's real vs simulated)

- ✅ **Real:** the entire pipeline — validation, agent logic, OR-Tools optimization, capacity constraints, fuel math, forecast math, alert state machine, persistence, tests.
- 🟡 **Simulated & labelled everywhere:** bin telemetry (seeded Jaipur dataset + simulator), fuel price/consumption assumptions, distances (haversine × 1.30 road factor, no traffic API).
- ⬜ **Phase 10 extensions (documented, not blockers):** IoT ingestion, traffic-aware routing API, YOLO waste classification from images, auth, scheduled forecast refresh. See `docs/tasks.md`.

**Documented deviations from the blueprint** (all allowed by it): SQLite instead of Postgres for the local prototype; `create_all()` + idempotent seed instead of Alembic (production step kept in the guide); SVG map instead of Leaflet tiles (offline requirement); scikit-learn model deferred in favour of the transparent baseline the agents config prescribes for MVP.

## 📚 Documentation

The original blueprint pack (specs of record) lives in [`docs/`](docs/): architecture, agent configs, API contract, data model, setup guide, tasks & phases, prompt templates, testing strategy, deployment guide, security & ethics.

## 📄 License / provenance

Built as a student exhibition project. Demo data is synthetic. Google, Meta and other names never appear as endorsements. Fuel savings and forecast accuracy are labelled estimates — not measured performance.
