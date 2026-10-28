"""Shared schema plumbing: UTC-serialized datetimes + base response models."""
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, PlainSerializer

# Serialize every datetime as ISO 8601 UTC with a trailing "Z"
# (api_contract.md: "All timestamps use ISO 8601 UTC").
UTCDatetime = Annotated[
    datetime,
    PlainSerializer(
        lambda dt: (dt.replace(microsecond=0).isoformat()) + "Z",
        return_type=str,
        when_used="always",
    ),
]

AgentStatus = Literal["success", "partial", "skipped", "failed"]
RunStatus = Literal["PENDING", "RUNNING", "FEASIBLE", "PARTIAL", "INFEASIBLE", "FAILED"]
FillStatus = Literal["NORMAL", "WARNING", "CRITICAL"]
ReadingSource = Literal["sensor", "simulator", "manual", "import"]


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorBody(APIModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorEnvelope(APIModel):
    error: ErrorBody


class AgentResultOut(APIModel):
    agent_name: str
    status: AgentStatus
    summary: str
    reasons: list[str] = []
    warnings: list[str] = []
    duration_ms: int = 0
