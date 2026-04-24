from server.config import Settings, get_settings
from server.models.health import HealthResponse, LLMHealthResponse, ReadyResponse
from server.services.llm_manager import LLMManager, get_llm_manager


class HealthService:
    """Provides application liveness and readiness status."""

    def __init__(self, settings: Settings, llm_manager: LLMManager) -> None:
        self._settings = settings
        self._llm_manager = llm_manager

    def get_health(self) -> HealthResponse:
        return HealthResponse(
            service=self._settings.app_name,
            environment=self._settings.environment,
            version=self._settings.app_version,
        )

    def get_ready(self) -> ReadyResponse:
        llm_health = self._llm_manager.get_health_status()
        llm_check = "ok" if llm_health.available else "degraded"
        status = "ready" if llm_health.available else "degraded"
        return ReadyResponse(
            service=self._settings.app_name,
            status=status,
            checks={"config": "ok", "llm": llm_check},
        )

    def get_llm_health(self) -> LLMHealthResponse:
        llm_health = self._llm_manager.get_health_status()
        return LLMHealthResponse(
            status="ok" if llm_health.available else "degraded",
            available=llm_health.available,
            model_present=llm_health.model_present,
            warmed_up=llm_health.warmed_up,
            checked_at=llm_health.checked_at,
            source=llm_health.source,
            model=self._settings.ollama_model,
            last_error=llm_health.last_error,
            latency_ms=llm_health.last_latency_ms,
        )


def get_health_service() -> HealthService:
    return HealthService(
        settings=get_settings(),
        llm_manager=get_llm_manager(),
    )
