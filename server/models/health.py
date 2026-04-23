from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = Field(default="ok")
    service: str
    environment: str
    version: str


class ReadyResponse(BaseModel):
    status: Literal["ready"] = Field(default="ready")
    service: str
    checks: dict[str, Literal["ok"]]
