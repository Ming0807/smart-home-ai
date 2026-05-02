import logging
from threading import Thread
from time import sleep

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from server.config import get_settings, resolve_project_path
from server.routes.chat import router as chat_router
from server.routes.dashboard import router as dashboard_router
from server.routes.devices import router as devices_router
from server.routes.esp32 import router as esp32_router
from server.routes.health import router as health_router
from server.routes.voice import router as voice_router
from server.services.llm_manager import get_llm_manager
from server.services.stt_service import get_stt_service
from server.utils.observability import configure_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    static_dir = resolve_project_path(settings.tts_output_dir)
    webui_dir = resolve_project_path("webui")
    static_dir.mkdir(parents=True, exist_ok=True)
    webui_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.mount("/webui", StaticFiles(directory=webui_dir), name="webui")
    app.include_router(dashboard_router)
    app.include_router(chat_router)
    app.include_router(devices_router)
    app.include_router(esp32_router)
    app.include_router(health_router)
    app.include_router(voice_router)
    _register_handlers(app)
    _register_startup_tasks(app)

    return app


def _register_startup_tasks(app: FastAPI) -> None:
    @app.on_event("startup")
    async def startup() -> None:
        settings = get_settings()

        if settings.llm_warmup_on_start:
            def _warmup_llm() -> None:
                logger.info("Starting LLM warmup in background")
                get_llm_manager().warmup()

            Thread(target=_warmup_llm, daemon=True).start()

        if settings.demo_mode and settings.llm_keep_awake_in_demo:
            def _keep_llm_awake() -> None:
                interval_seconds = max(60, settings.llm_keep_awake_interval_seconds)
                logger.info(
                    "Starting LLM keep-awake loop every %s seconds",
                    interval_seconds,
                )
                while True:
                    sleep(interval_seconds)
                    try:
                        get_llm_manager().keep_awake_once()
                    except Exception:
                        logger.exception("LLM keep-awake tick failed")

            Thread(target=_keep_llm_awake, daemon=True).start()

        if settings.stt_warmup_on_start:
            def _warmup_stt() -> None:
                logger.info("Starting STT warmup in background")
                get_stt_service().warmup()

            Thread(target=_warmup_stt, daemon=True).start()


def _register_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "request validation failed",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled application error at %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "internal server error"},
        )


app = create_app()
