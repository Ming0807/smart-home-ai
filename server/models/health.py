from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = Field(default="ok")
    service: str
    environment: str
    version: str


class ReadyResponse(BaseModel):
    status: Literal["ready", "degraded"] = Field(default="ready")
    service: str
    checks: dict[str, Literal["ok", "degraded"]]


class LLMHealthResponse(BaseModel):
    status: Literal["ok", "degraded"] = Field(default="ok")
    available: bool
    model_present: bool
    warmed_up: bool
    checked_at: datetime | None = None
    source: Literal["live", "cache"]
    model: str
    last_error: str | None = None
    latency_ms: float | None = None
    keep_awake_enabled: bool = False
    keep_awake_paused: bool = False
