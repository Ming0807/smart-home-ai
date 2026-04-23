from server.config import Settings, get_settings
from server.models.health import HealthResponse, ReadyResponse


class HealthService:
    """Provides application liveness and readiness status."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_health(self) -> HealthResponse:
        return HealthResponse(
            service=self._settings.app_name,
            environment=self._settings.environment,
            version=self._settings.app_version,
        )

    def get_ready(self) -> ReadyResponse:
        return ReadyResponse(
            service=self._settings.app_name,
            checks={"config": "ok"},
        )


def get_health_service() -> HealthService:
    return HealthService(settings=get_settings())
