from functools import lru_cache
from os import environ, getenv
from pathlib import Path

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
    default_esp32_device_id: str = Field(default="esp32-01")
    sensor_freshness_seconds: int = Field(default=300)
    openweather_api_key: str = Field(default="")
    default_weather_location: str = Field(default="Yala,TH")
    weather_timeout_seconds: float = Field(default=5.0)
    weather_cache_ttl_seconds: int = Field(default=600)


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


def _load_dotenv() -> None:
    """Load project-root .env values without overriding real environment variables."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#") or "=" not in stripped_line:
            continue
        key, value = stripped_line.split("=", 1)
        key = key.strip()
        if not key or key in environ:
            continue
        environ[key] = _strip_env_quotes(value.strip())


def _strip_env_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    _load_dotenv()
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
        default_esp32_device_id=getenv("DEFAULT_ESP32_DEVICE_ID", "esp32-01"),
        sensor_freshness_seconds=_get_int_env("SENSOR_FRESHNESS_SECONDS", 300),
        openweather_api_key=getenv("OPENWEATHER_API_KEY", ""),
        default_weather_location=getenv("DEFAULT_WEATHER_LOCATION", "Yala,TH"),
        weather_timeout_seconds=_get_float_env("WEATHER_TIMEOUT_SECONDS", 5.0),
        weather_cache_ttl_seconds=_get_int_env("WEATHER_CACHE_TTL_SECONDS", 600),
    )
