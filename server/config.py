from functools import lru_cache
from os import getenv

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    app_name: str = Field(default="AI Smart Home Thai Assistant")
    app_version: str = Field(default="0.1.0")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="scb10x/llama3.1-typhoon2-8b-instruct:latest")
    ollama_timeout_seconds: float = Field(default=120.0)
    llm_max_tokens: int = Field(default=120)
    llm_temperature: float = Field(default=0.2)
    system_prompt_path: str = Field(default="prompts/system_prompt.txt")


def _get_bool_env(name: str, default: bool = False) -> bool:
    value = getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_float_env(name: str, default: float) -> float:
    value = getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_int_env(name: str, default: int) -> int:
    value = getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings(
        app_name=getenv("APP_NAME", "AI Smart Home Thai Assistant"),
        app_version=getenv("APP_VERSION", "0.1.0"),
        environment=getenv("APP_ENV", "development"),
        debug=_get_bool_env("APP_DEBUG", False),
        ollama_base_url=getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=getenv(
            "OLLAMA_MODEL",
            "scb10x/llama3.1-typhoon2-8b-instruct:latest",
        ),
        ollama_timeout_seconds=_get_float_env("OLLAMA_TIMEOUT_SECONDS", 120.0),
        llm_max_tokens=_get_int_env("LLM_MAX_TOKENS", 120),
        llm_temperature=_get_float_env("LLM_TEMPERATURE", 0.2),
        system_prompt_path=getenv("SYSTEM_PROMPT_PATH", "prompts/system_prompt.txt"),
    )
