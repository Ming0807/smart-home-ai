from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RelayAction = Literal["on", "off"]
CommandResultStatus = Literal["applied", "failed"]


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


class Esp32CapabilitiesRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    board_type: str = Field(default="esp32-s3", min_length=1, max_length=80)
    firmware_version: str | None = Field(default=None, max_length=80)
    capabilities: list[str] = Field(default_factory=list, max_length=30)
    relay_pins: list[int] = Field(default_factory=list, max_length=64)
    sensor_pins: list[int] = Field(default_factory=list, max_length=64)
    reserved_pins: list[int] = Field(default_factory=list, max_length=64)
    i2s_pins: list[int] = Field(default_factory=list, max_length=16)
    available_pins: list[int] = Field(default_factory=list, max_length=64)
    timestamp: datetime


class RelayCommand(BaseModel):
    type: Literal["relay"] = "relay"
    command_id: str | None = None
    target_device_id: str | None = None
    channel: int = Field(default=1, ge=1, le=1)
    gpio_pin: int | None = Field(default=None, ge=0, le=48)
    action: RelayAction


class CommandResponse(BaseModel):
    command: RelayCommand | None


class CommandResultRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    command_id: str = Field(min_length=1, max_length=120)
    status: CommandResultStatus
    state: RelayAction | None = None
    error: str | None = Field(default=None, max_length=500)
    timestamp: datetime


class CommandResult(BaseModel):
    device_id: str
    command_id: str
    status: CommandResultStatus
    state: RelayAction | None = None
    error: str | None = None
    timestamp: datetime
    received_at: datetime


class Esp32Capabilities(BaseModel):
    device_id: str
    board_type: str
    firmware_version: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    relay_pins: list[int] = Field(default_factory=list)
    sensor_pins: list[int] = Field(default_factory=list)
    reserved_pins: list[int] = Field(default_factory=list)
    i2s_pins: list[int] = Field(default_factory=list)
    available_pins: list[int] = Field(default_factory=list)
    timestamp: datetime
    received_at: datetime


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
    latest_command_result: CommandResult | None = None
    capabilities: Esp32Capabilities | None = None


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
