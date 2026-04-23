from fastapi import FastAPI

from server.config import get_settings
from server.routes.chat import router as chat_router
from server.routes.health import router as health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    app.include_router(chat_router)
    app.include_router(health_router)

    return app


app = create_app()
