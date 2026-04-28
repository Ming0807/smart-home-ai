from typing import Literal

from pydantic import BaseModel, Field, field_validator

IntentName = Literal[
    "device_control",
    "line_send_request",
    "navigation_query",
    "news_detail_query",
    "news_query",
    "weather_query",
    "traffic_query",
    "sensor_query",
    "system_status",
    "general_chat",
]
ResponseSource = Literal[
    "cache",
    "ollama",
    "fallback",
    "line",
    "rule_based",
    "placeholder",
    "device_control",
    "motion_sensor",
    "navigation_api",
    "traffic_api",
    "currents_api",
    "sensor",
    "system_status",
    "weather_api",
    "voice_control",
]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        message = value.strip()
        if not message:
            raise ValueError("message must not be empty")
        return message


class ChatResponse(BaseModel):
    reply: str
    intent: IntentName
    source: ResponseSource
    audio_url: str | None = None
