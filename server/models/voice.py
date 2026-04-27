from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from server.models.chat import IntentName, ResponseSource

MicAction = Literal["none", "light_on", "light_off", "relay_on", "relay_off"]


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("text must not be empty")
        return text


class SpeakResponse(BaseModel):
    status: Literal["ok", "error"]
    text: str
    audio_url: str | None = None
    provider: str | None = None
    error: str | None = None


class VoiceStatusResponse(BaseModel):
    tts_enabled: bool
    provider: str
    output_file: str
    current_token: str | None = None
    audio_ready: bool = False
    file_size_bytes: int = 0
    last_generated_at: datetime | None = None
    last_error: str | None = None


class VoiceChatRequestMeta(BaseModel):
    message: str | None = Field(default=None, max_length=2000)
    pir_state: int = Field(default=0, ge=0, le=1)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class VoiceChatData(BaseModel):
    heard_text: str
    reply: str
    intent: IntentName
    source: ResponseSource
    action: MicAction = "none"
    keep_mic_open: bool = False
    audio_url: str | None = None


class VoiceChatResponse(BaseModel):
    status: Literal["success"] = "success"
    data: VoiceChatData
