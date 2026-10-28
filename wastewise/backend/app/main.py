"""WasteWise API — FastAPI application entry point."""
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.routes import health_bins_demo
from app.api.routes.ops import (
    alerts_router, dashboard_router, fleet_router, forecasts_router,
    optimization_router, recycling_router, settings_router,
)
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import SessionLocal, engine, Base
from app.seed.seed_data import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Test sessions manage their own schema/data (see tests/conftest.py).
    if get_settings().app_env != "test":
        # Prototype strategy: create_all + idempotent seed.
        # Production: Alembic migrations as a controlled release step
        # (deployment_guide.md).
        Base.metadata.create_all(bind=engine)
        db: Session = SessionLocal()
        try:
            seed(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="WasteWise API",
    description=(
        "AI-powered waste management platform — multi-agent collection planning. "
        "Demo data is simulated and labelled; agents are deterministic and versioned."
    ),
    version=get_settings().version,
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid4().hex[:12]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def _error(code: str, message: str, status_code: int, request: Request):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": getattr(request.state, "request_id", None)}},
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return _error(exc.code, exc.message, exc.status_code, request)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(p) for p in first.get("loc", []))
    msg = first.get("msg", "Invalid request.")
    return _error("VALIDATION_ERROR", f"{loc}: {msg}" if loc else msg, 422, request)


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    return _error("INTERNAL_ERROR", "An unexpected error occurred.", 500, request)


API = "/api/v1"
app.include_router(health_bins_demo.router, prefix=API)
app.include_router(optimization_router, prefix=API)
app.include_router(forecasts_router, prefix=API)
app.include_router(recycling_router, prefix=API)
app.include_router(alerts_router, prefix=API)
app.include_router(fleet_router, prefix=API)
app.include_router(settings_router, prefix=API)
app.include_router(dashboard_router, prefix=API)


@app.get("/", tags=["health"])
def root():
    return {
        "service": "wastewise-api",
        "docs": "/docs",
        "api": "/api/v1",
        "note": "Demo deployment — telemetry is simulated and labelled.",
    }
