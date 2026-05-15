from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from server.models.chat import IntentName, ResponseSource
from server.models.voice import MicAction


VoiceNodeState = Literal[
    "BOOT",
    "WIFI_CONNECTING",
    "REGISTERING",
    "WAKE_LISTENING",
    "WAKE_DETECTED",
    "BEEPING",
    "RECORDING_COMMAND",
    "UPLOADING_AUDIO",
    "WAITING_SERVER_REPLY",
    "PLAYING_REPLY",
    "COOLDOWN",
    "ERROR",
]


class VoiceNodeHeartbeatRequest(BaseModel):
    device_id: str = Field(default="voice-node-01", min_length=1, max_length=64)
    firmware_version: str | None = Field(default=None, max_length=40)
    state: VoiceNodeState = "WAKE_LISTENING"
    ip_address: str | None = Field(default=None, max_length=64)

    @field_validator("device_id")
    @classmethod
    def strip_device_id(cls, value: str) -> str:
        device_id = value.strip()
        if not device_id:
            raise ValueError("device_id must not be empty")
        return device_id


class VoiceNodeHeartbeatResponse(BaseModel):
    status: Literal["ok"] = "ok"
    server_time: datetime


class VoiceNodeConfigResponse(BaseModel):
    device_id: str
    enabled: bool
    wake_word: str
    record_seconds: int
    sample_rate: int
    reply_sample_rate: int
    audio_format: str
    reply_audio_format: str
    mic_record_gain: int
    vad_enabled: bool
    vad_threshold: int
    vad_min_record_ms: int
    vad_silence_stop_ms: int
    heartbeat_endpoint: str
    audio_endpoint: str
    status_endpoint: str


class VoiceNodeConfigUpdateRequest(BaseModel):
    enabled: bool | None = None
    record_seconds: int | None = Field(default=None, ge=1, le=10)
    mic_record_gain: int | None = Field(default=None, ge=1, le=128)
    vad_enabled: bool | None = None
    vad_threshold: int | None = Field(default=None, ge=1, le=5000)
    vad_min_record_ms: int | None = Field(default=None, ge=300, le=5000)
    vad_silence_stop_ms: int | None = Field(default=None, ge=200, le=3000)


class VoiceNodeStatusResponse(BaseModel):
    device_id: str
    online: bool
    enabled: bool
    state: VoiceNodeState | None = None
    firmware_version: str | None = None
    ip_address: str | None = None
    last_seen_at: datetime | None = None
    seconds_since_heartbeat: int | None = None
    pending_command_count: int = 0


class VoiceNodeAudioStatusResponse(BaseModel):
    device_id: str
    has_result: bool
    received_at: datetime | None = None
    seconds_since_received: int | None = None
    stt_ok: bool | None = None
    stt_error: str | None = None
    stt_raw_text: str | None = None
    expected_text: str | None = None
    stt_similarity: float | None = None
    heard_text: str = ""
    reply: str = ""
    intent: IntentName | None = None
    source: ResponseSource | None = None
    action: MicAction = "none"
    keep_mic_open: bool = False
    reply_audio_url: str | None = None
    reply_audio_format: str | None = None
    uploaded_audio_url: str | None = None
    uploaded_audio_content_type: str | None = None
    uploaded_audio_size_bytes: int | None = None
    uploaded_audio_duration_ms: int | None = None
    uploaded_audio_sample_rate_hz: int | None = None
    uploaded_audio_peak_ratio: float | None = None
    uploaded_audio_rms_ratio: float | None = None
    uploaded_audio_clipping_ratio: float | None = None
    uploaded_audio_silence_ratio: float | None = None
    uploaded_audio_quality: str | None = None
    uploaded_audio_quality_notes: list[str] = Field(default_factory=list)
    playback_reported_at: datetime | None = None
    playback_stage: str | None = None
    playback_ok: bool | None = None
    playback_error: str | None = None
    playback_audio_url: str | None = None
    playback_audio_size_bytes: int | None = None


class VoiceNodeAudioHistoryItem(BaseModel):
    received_at: datetime
    seconds_since_received: int
    stt_ok: bool
    stt_error: str | None = None
    stt_raw_text: str | None = None
    expected_text: str | None = None
    stt_similarity: float | None = None
    heard_text: str = ""
    reply: str = ""
    intent: IntentName | None = None
    source: ResponseSource | None = None
    action: MicAction = "none"
    keep_mic_open: bool = False
    uploaded_audio_size_bytes: int | None = None
    uploaded_audio_duration_ms: int | None = None
    uploaded_audio_peak_ratio: float | None = None
    uploaded_audio_rms_ratio: float | None = None
    uploaded_audio_clipping_ratio: float | None = None
    uploaded_audio_quality: str | None = None
    uploaded_audio_quality_notes: list[str] = Field(default_factory=list)
    playback_stage: str | None = None
    playback_ok: bool | None = None
    playback_error: str | None = None
    playback_audio_size_bytes: int | None = None


class VoiceNodeAudioHistoryResponse(BaseModel):
    device_id: str
    items: list[VoiceNodeAudioHistoryItem]


class VoiceNodeAudioReportResponse(BaseModel):
    device_id: str
    generated_at: datetime
    total_items: int
    stt_success_count: int
    stt_success_rate: float
    scored_count: int
    average_similarity: float | None = None
    high_score_count: int
    low_score_count: int
    playback_success_count: int
    playback_success_rate: float
    average_uploaded_duration_ms: int | None = None
    average_peak_ratio: float | None = None
    average_rms_ratio: float | None = None
    audio_quality_ok_count: int
    audio_quality_ok_rate: float
    quiet_warning_count: int
    clipping_warning_count: int
    latest_received_at: datetime | None = None
    ready_for_demo: bool
    notes: list[str]


class VoiceNodeAudioHistoryClearResponse(BaseModel):
    status: Literal["ok"] = "ok"
    device_id: str
    cleared: bool
    cleared_pending_command_count: int = 0


class VoiceNodePlaybackStatusRequest(BaseModel):
    device_id: str = Field(default="voice-node-01", min_length=1, max_length=64)
    stage: str = Field(min_length=1, max_length=32)
    ok: bool
    error: str | None = Field(default=None, max_length=160)
    audio_url: str | None = Field(default=None, max_length=240)
    audio_size_bytes: int | None = Field(default=None, ge=0)

    @field_validator("device_id")
    @classmethod
    def strip_playback_device_id(cls, value: str) -> str:
        device_id = value.strip()
        if not device_id:
            raise ValueError("device_id must not be empty")
        return device_id


class VoiceNodePlaybackStatusResponse(BaseModel):
    status: Literal["ok"] = "ok"


class AssistantAudioData(BaseModel):
    heard_text: str
    reply: str
    intent: IntentName
    source: ResponseSource
    action: MicAction = "none"
    keep_mic_open: bool = False
    reply_audio_url: str | None = None
    reply_audio_format: str


class AssistantAudioResponse(BaseModel):
    status: Literal["success"] = "success"
    data: AssistantAudioData


VoiceNodeCommandType = Literal[
    "speaker_test",
    "record_once",
    "play_audio",
    "conversation_start",
    "conversation_stop",
]


class VoiceNodeCommandData(BaseModel):
    command_id: str
    type: VoiceNodeCommandType
    created_at: datetime
    audio_url: str | None = None
    expected_text: str | None = None


class VoiceNodeCommandPollResponse(BaseModel):
    command: VoiceNodeCommandData | None = None


class VoiceNodeCommandQueueResponse(BaseModel):
    status: Literal["queued"] = "queued"
    device_id: str
    command: VoiceNodeCommandData
    pending_command_count: int
