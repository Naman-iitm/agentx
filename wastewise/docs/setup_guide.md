# WasteWise Setup Guide

These instructions target macOS/Linux and a Windows terminal with equivalent commands. Use separate terminals for backend and frontend.

## Prerequisites

- Git
- Python 3.11 or 3.12
- Node.js LTS and npm
- Optional: Docker Desktop for PostgreSQL/PostGIS
- Editor: VS Code, Cursor, or equivalent

Check versions:
```bash
git --version
python3 --version
node --version
npm --version
```

## 1. Create repository

```bash
mkdir wastewise
cd wastewise
git init
mkdir -p backend/app/{api/routes,agents,core,db,schemas,services,optimization,forecasting,vision,seed}
mkdir -p backend/tests
npm create vite@latest frontend -- --template react-ts
```

Copy the project documents into the repository root. The backend may use `pyproject.toml`; do not create conflicting dependency files without a reason.

## 2. Backend environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

For Windows PowerShell activate with `.venv\\Scripts\\Activate.ps1`.

Install dependencies from the generated `pyproject.toml` or use a temporary minimal list:
```bash
pip install fastapi "uvicorn[standard]" pydantic-settings sqlalchemy alembic psycopg[binary] httpx pytest
pip install langgraph ortools pandas scikit-learn
```

Install optional dependencies separately, only when implementing vision:
```bash
pip install opencv-python ultralytics
```

Save exact resolved versions in the project's lock/dependency process after the first successful run. Avoid unpinned production deployments.

Run API:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000/docs` and `http://127.0.0.1:8000/api/v1/health`.

## 3. Frontend environment

In a second terminal:
```bash
cd wastewise/frontend
npm install
npm install axios react-router-dom leaflet react-leaflet
npm install recharts lucide-react
npm run dev
```

If using Leaflet, import its CSS in the frontend entry point and ensure the map container has a defined height. Keep the API base URL in `VITE_API_BASE_URL`.

## 4. Environment variables

Create `.env` from `.env.example`. Do not commit `.env`.

For local development, SQLite can be used first. For the full database, start PostgreSQL/PostGIS through Docker Compose and set `DATABASE_URL`. Example format:
`postgresql+psycopg://wastewise:wastewise_dev_only@localhost:5432/wastewise`

Never use the example credentials in production.

## 5. Database setup

After SQLAlchemy models and Alembic configuration exist:
```bash
alembic upgrade head
python -m app.seed.seed_demo
```
If the seed module is implemented as a script, use its documented invocation. Seed must be safe to run more than once.

## 6. Verify integration

```bash
# Backend tests
pytest -q

# Frontend tests
cd ../frontend
npm run test
npm run build
```

Manual checks:
- Dashboard loads.
- Bin list has demo data.
- A new reading changes the displayed fill state.
- Run Optimization returns an explicit status and route.
- Fuel calculation matches the documented formula.
- Agent failure appears as a warning, not fake success.
- Refreshing the browser does not erase persisted data.

## 7. Troubleshooting

- `ModuleNotFoundError: app`: run Uvicorn from `backend/` with `.venv` active.
- Frontend cannot reach API: check `VITE_API_BASE_URL`, backend port, CORS configuration, and browser console.
- PostgreSQL connection refused: check Docker container health and `DATABASE_URL`.
- Leaflet map blank: verify tile/network access, CSS import, map height, and valid coordinates.
- OR-Tools returns no solution: inspect capacity constraints and candidate demand; return `INFEASIBLE` or `PARTIAL` with a reason.
- Forecast has too little history: return baseline or `insufficient_history`; do not fabricate accuracy.
