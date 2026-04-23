from typing import Literal

from pydantic import BaseModel, Field, field_validator

IntentName = Literal[
    "device_control",
    "weather_query",
    "traffic_query",
    "sensor_query",
    "general_chat",
]
ResponseSource = Literal[
    "ollama",
    "fallback",
    "placeholder",
    "device_control",
    "sensor",
    "weather_api",
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
