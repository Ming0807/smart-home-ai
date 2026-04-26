from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RelayAction = Literal["on", "off"]


class StatusResponse(BaseModel):
    status: Literal["ok"] = "ok"


class HeartbeatRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)


class SensorRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    temperature: float
    humidity: float
    timestamp: datetime


class MotionRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    motion: bool
    timestamp: datetime


class RelayCommand(BaseModel):
    type: Literal["relay"] = "relay"
    channel: int = Field(default=1, ge=1, le=1)
    action: RelayAction


class CommandResponse(BaseModel):
    command: RelayCommand | None


class DeviceHeartbeat(BaseModel):
    device_id: str
    last_seen_at: datetime


class DeviceStatusResponse(BaseModel):
    device_id: str
    online: bool
    last_seen_at: datetime | None = None
    seconds_since_heartbeat: int | None = None
    pending_command_count: int = 0
    latest_command: RelayCommand | None = None


class SensorReading(BaseModel):
    device_id: str
    temperature: float
    humidity: float
    timestamp: datetime
    received_at: datetime


class MotionEvent(BaseModel):
    device_id: str
    motion: bool
    timestamp: datetime
    received_at: datetime
