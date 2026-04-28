from fastapi import APIRouter, Depends, status

from server.models.health import HealthResponse, LLMHealthResponse, ReadyResponse
from server.services.health import HealthService, get_health_service

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
async def health(
    health_service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    return health_service.get_health()


@router.get(
    "/ready",
    response_model=ReadyResponse,
    status_code=status.HTTP_200_OK,
)
async def ready(
    health_service: HealthService = Depends(get_health_service),
) -> ReadyResponse:
    return health_service.get_ready()


@router.get(
    "/health/llm",
    response_model=LLMHealthResponse,
    status_code=status.HTTP_200_OK,
)
async def health_llm(
    health_service: HealthService = Depends(get_health_service),
) -> LLMHealthResponse:
    return health_service.get_llm_health()


@router.post(
    "/health/llm/warmup",
    response_model=LLMHealthResponse,
    status_code=status.HTTP_200_OK,
)
async def warmup_llm(
    health_service: HealthService = Depends(get_health_service),
) -> LLMHealthResponse:
    return health_service.warmup_llm()


@router.post(
    "/health/llm/sleep",
    response_model=LLMHealthResponse,
    status_code=status.HTTP_200_OK,
)
async def sleep_llm(
    health_service: HealthService = Depends(get_health_service),
) -> LLMHealthResponse:
    return health_service.sleep_llm()
