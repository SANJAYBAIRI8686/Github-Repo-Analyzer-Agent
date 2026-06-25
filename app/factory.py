from __future__ import annotations

import logging
from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.intelligence import router as intelligence_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.repositories import router as repositories_router
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.db.session import init_db


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    init_db(settings)

    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.state.settings = settings

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logging.exception("Unhandled application error")
        return JSONResponse(status_code=500, content={"error": "internal_error", "detail": str(exc)})

    app.include_router(health_router)
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(repositories_router, prefix="/repositories", tags=["repositories"])
    app.include_router(intelligence_router)
    app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])

    return app
