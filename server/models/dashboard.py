from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from server.models.esp32 import RelayCommand


class SensorSnapshot(BaseModel):
    device_id: str
    temperature: float | None = None
    humidity: float | None = None
    timestamp: datetime | None = None
    received_at: datetime | None = None
    is_fresh: bool = False


class DeviceSnapshot(BaseModel):
    device_id: str
    online: bool = False
    last_seen_at: datetime | None = None
    seconds_since_heartbeat: int | None = None
    pending_command_count: int = 0
    latest_command: RelayCommand | None = None


class MotionSnapshot(BaseModel):
    device_id: str
    motion_detected: bool = False
    last_motion_at: datetime | None = None
    last_event_at: datetime | None = None
    greeting_message: str | None = None


class VoiceSnapshot(BaseModel):
    tts_enabled: bool
    demo_voice_mode: bool
    provider: str
    default_voice: str
    output_file: str


class LLMSnapshot(BaseModel):
    status: Literal["ok", "degraded"]
    available: bool
    model_present: bool
    warmed_up: bool
    model: str
    source: Literal["live", "cache"]
    checked_at: datetime | None = None
    last_error: str | None = None
    latency_ms: float | None = None
    keep_awake_enabled: bool = False
    keep_awake_paused: bool = False


class AppSnapshot(BaseModel):
    demo_mode: bool
    debug_logs: bool
    max_chat_history_items: int


class DashboardStatusResponse(BaseModel):
    sensor: SensorSnapshot
    device: DeviceSnapshot
    motion: MotionSnapshot
    voice: VoiceSnapshot
    llm: LLMSnapshot
    app: AppSnapshot
