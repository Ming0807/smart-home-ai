from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from server.models.chat import IntentName, ResponseSource


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


class VoiceChatResponse(BaseModel):
    heard_text: str
    reply: str
    intent: IntentName
    source: ResponseSource
    audio_url: str | None = None
