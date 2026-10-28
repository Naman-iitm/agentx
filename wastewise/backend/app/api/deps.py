"""FastAPI dependencies shared across routers."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import AppSettings
from app.db.session import get_db
from app.services.settings_service import get_settings_row


def db_session() -> Session:
    return Depends(get_db)


def settings_row(db: Session = Depends(get_db)) -> AppSettings:
    return get_settings_row(db)


def require_demo_mode():
    """Guard for simulation-only endpoints — never exposed in production."""
    if not get_settings().demo_mode:
        raise AppError(
            code="DEMO_MODE_DISABLED",
            message="Simulation endpoints are disabled (DEMO_MODE=false).",
            status_code=403,
        )
