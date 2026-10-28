"""Small shared utilities: UTC time handling and pagination."""
import math
from datetime import datetime, timezone
from typing import Any

from fastapi import Query


def utcnow() -> datetime:
    """Naive UTC datetime — the canonical internal timestamp format.

    Stored naive (SQLite-friendly), serialized with a trailing 'Z' by the
    API layer. Never store local time.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc(dt: datetime) -> datetime:
    """Coerce an aware datetime to naive UTC; pass naive values through."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def hours_between(a: datetime, b: datetime) -> float:
    return (a - b).total_seconds() / 3600.0


class Pagination:
    """Shared limit/offset query params with sane caps."""

    def __init__(
        self,
        limit: int = Query(50, ge=1, le=200, description="Page size (max 200)"),
        offset: int = Query(0, ge=0, description="Number of items to skip"),
    ):
        self.limit = limit
        self.offset = offset

    def window(self, items: list[Any]) -> list[Any]:
        return items[self.offset : self.offset + self.limit]


def paginate(items: list[Any], limit: int, offset: int) -> dict[str, Any]:
    return {
        "items": items[offset : offset + limit],
        "total": len(items),
        "limit": limit,
        "offset": offset,
    }


def round2(value: float) -> float:
    return round(value + 0.0, 2)


def safe_percent(p: float) -> float:
    return max(0.0, min(100.0, p))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres (deterministic, no external API)."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))
