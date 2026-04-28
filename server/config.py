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
    debug_logs: bool = Field(default=False)
    demo_mode: bool = Field(default=True)
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="scb10x/llama3.1-typhoon2-8b-instruct:latest")
    ollama_timeout_seconds: float = Field(default=120.0)
    chat_timeout_seconds: float = Field(default=30.0)
    llm_warmup_on_start: bool = Field(default=True)
    llm_max_tokens: int = Field(default=120)
    llm_temperature: float = Field(default=0.2)
    llm_health_cache_ttl_seconds: int = Field(default=30)
    llm_response_cache_ttl_seconds: int = Field(default=120)
    system_prompt_path: str = Field(default="prompts/system_prompt.txt")
    default_esp32_device_id: str = Field(default="esp32-01")
    esp32_offline_timeout_seconds: int = Field(default=60)
    sensor_freshness_seconds: int = Field(default=300)
    openweather_api_key: str = Field(default="")
    default_weather_location: str = Field(default="Yala,TH")
    weather_timeout_seconds: float = Field(default=5.0)
    weather_cache_ttl_seconds: int = Field(default=600)
    currents_api_key: str = Field(default="")
    news_provider: str = Field(default="currents")
    news_default_language: str = Field(default="th")
    news_default_country: str = Field(default="TH")
    news_cache_ttl_seconds: int = Field(default=600)
    news_timeout_seconds: float = Field(default=5.0)
    news_max_items: int = Field(default=5)
    line_enabled: bool = Field(default=False)
    line_channel_id: str = Field(default="")
    line_channel_secret: str = Field(default="")
    line_channel_access_token: str = Field(default="")
    line_target_id: str = Field(default="")
    line_timeout_seconds: float = Field(default=5.0)
    nav_provider: str = Field(default="openrouteservice")
    openrouteservice_api_key: str = Field(default="")
    nav_default_origin: str = Field(default="Yala")
    nav_timeout_seconds: float = Field(default=5.0)
    nav_cache_ttl_seconds: int = Field(default=600)
    nav_default_language: str = Field(default="th")
    traffic_provider: str = Field(default="tomtom")
    tomtom_api_key: str = Field(default="")
    traffic_timeout_seconds: float = Field(default=5.0)
    traffic_cache_ttl_seconds: int = Field(default=300)
    traffic_default_location: str = Field(default="Yala")
    traffic_flow_zoom: int = Field(default=10)
    tts_enabled: bool = Field(default=True)
    demo_voice_mode: bool = Field(default=True)
    tts_provider: str = Field(default="edge_tts")
    tts_overwrite_output: bool = Field(default=True)
    tts_output_file: str = Field(default="current_reply.mp3")
    tts_default_voice: str = Field(default="th-TH-PremwadeeNeural")
    tts_output_dir: str = Field(default="static")
    stt_provider: str = Field(default="faster_whisper")
    stt_model: str = Field(default="small")
    stt_language: str = Field(default="th")
    stt_timeout_seconds: float = Field(default=30.0)
    stt_warmup_on_start: bool = Field(default=True)
    max_chat_history_items: int = Field(default=50)


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


def resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[1] / path


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    _load_dotenv()
    return Settings(
        app_name=getenv("APP_NAME", "AI Smart Home Thai Assistant"),
        app_version=getenv("APP_VERSION", "0.1.0"),
        environment=getenv("APP_ENV", "development"),
        debug=_get_bool_env("APP_DEBUG", False),
        debug_logs=_get_bool_env("DEBUG_LOGS", False),
        demo_mode=_get_bool_env("DEMO_MODE", True),
        ollama_base_url=getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=getenv(
            "OLLAMA_MODEL",
            "scb10x/llama3.1-typhoon2-8b-instruct:latest",
        ),
        ollama_timeout_seconds=_get_float_env("OLLAMA_TIMEOUT_SECONDS", 120.0),
        chat_timeout_seconds=_get_float_env("CHAT_TIMEOUT_SECONDS", 30.0),
        llm_warmup_on_start=_get_bool_env("LLM_WARMUP_ON_START", True),
        llm_max_tokens=_get_int_env("LLM_MAX_TOKENS", 120),
        llm_temperature=_get_float_env("LLM_TEMPERATURE", 0.2),
        llm_health_cache_ttl_seconds=_get_int_env("LLM_HEALTH_CACHE_TTL_SECONDS", 30),
        llm_response_cache_ttl_seconds=_get_int_env("LLM_RESPONSE_CACHE_TTL_SECONDS", 120),
        system_prompt_path=getenv("SYSTEM_PROMPT_PATH", "prompts/system_prompt.txt"),
        default_esp32_device_id=getenv("DEFAULT_ESP32_DEVICE_ID", "esp32-01"),
        esp32_offline_timeout_seconds=_get_int_env("ESP32_OFFLINE_TIMEOUT_SECONDS", 60),
        sensor_freshness_seconds=_get_int_env("SENSOR_FRESHNESS_SECONDS", 300),
        openweather_api_key=getenv("OPENWEATHER_API_KEY", ""),
        default_weather_location=getenv("DEFAULT_WEATHER_LOCATION", "Yala,TH"),
        weather_timeout_seconds=_get_float_env("WEATHER_TIMEOUT_SECONDS", 5.0),
        weather_cache_ttl_seconds=_get_int_env("WEATHER_CACHE_TTL_SECONDS", 600),
        currents_api_key=getenv("CURRENTS_API_KEY", ""),
        news_provider=getenv("NEWS_PROVIDER", "currents"),
        news_default_language=getenv("NEWS_DEFAULT_LANGUAGE", "th"),
        news_default_country=getenv("NEWS_DEFAULT_COUNTRY", "TH"),
        news_cache_ttl_seconds=_get_int_env("NEWS_CACHE_TTL_SECONDS", 600),
        news_timeout_seconds=_get_float_env("NEWS_TIMEOUT_SECONDS", 5.0),
        news_max_items=_get_int_env("NEWS_MAX_ITEMS", 5),
        line_enabled=_get_bool_env("LINE_ENABLED", False),
        line_channel_id=getenv("LINE_CHANNEL_ID", ""),
        line_channel_secret=getenv("LINE_CHANNEL_SECRET", ""),
        line_channel_access_token=getenv("LINE_CHANNEL_ACCESS_TOKEN", ""),
        line_target_id=getenv("LINE_TARGET_ID", ""),
        line_timeout_seconds=_get_float_env("LINE_TIMEOUT_SECONDS", 5.0),
        nav_provider=getenv("NAV_PROVIDER", "openrouteservice"),
        openrouteservice_api_key=getenv("OPENROUTESERVICE_API_KEY", ""),
        nav_default_origin=getenv("NAV_DEFAULT_ORIGIN", "Yala"),
        nav_timeout_seconds=_get_float_env("NAV_TIMEOUT_SECONDS", 5.0),
        nav_cache_ttl_seconds=_get_int_env("NAV_CACHE_TTL_SECONDS", 600),
        nav_default_language=getenv("NAV_DEFAULT_LANGUAGE", "th"),
        traffic_provider=getenv("TRAFFIC_PROVIDER", "tomtom"),
        tomtom_api_key=getenv("TOMTOM_API_KEY", ""),
        traffic_timeout_seconds=_get_float_env("TRAFFIC_TIMEOUT_SECONDS", 5.0),
        traffic_cache_ttl_seconds=_get_int_env("TRAFFIC_CACHE_TTL_SECONDS", 300),
        traffic_default_location=getenv("TRAFFIC_DEFAULT_LOCATION", "Yala"),
        traffic_flow_zoom=_get_int_env("TRAFFIC_FLOW_ZOOM", 10),
        tts_enabled=_get_bool_env("TTS_ENABLED", True),
        demo_voice_mode=_get_bool_env("DEMO_VOICE_MODE", True),
        tts_provider=getenv("TTS_PROVIDER", "edge_tts"),
        tts_overwrite_output=_get_bool_env("TTS_OVERWRITE_OUTPUT", True),
        tts_output_file=getenv("TTS_OUTPUT_FILE", "current_reply.mp3"),
        tts_default_voice=getenv("TTS_DEFAULT_VOICE", "th-TH-PremwadeeNeural"),
        tts_output_dir=getenv("TTS_OUTPUT_DIR", "static"),
        stt_provider=getenv("STT_PROVIDER", "faster_whisper"),
        stt_model=getenv("STT_MODEL", "small"),
        stt_language=getenv("STT_LANGUAGE", "th"),
        stt_timeout_seconds=_get_float_env("STT_TIMEOUT_SECONDS", 30.0),
        stt_warmup_on_start=_get_bool_env("STT_WARMUP_ON_START", True),
        max_chat_history_items=_get_int_env("MAX_CHAT_HISTORY_ITEMS", 50),
    )
