from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ActivityLogItem(BaseModel):
    id: int
    event_type: str
    device_id: str | None = None
    message: str
    payload: dict[str, Any] | None = None
    created_at: datetime


class ActivityLogResponse(BaseModel):
    items: list[ActivityLogItem]
