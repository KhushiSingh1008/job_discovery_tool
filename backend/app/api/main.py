"""FastAPI application entry point: ``uvicorn app.api.main:app --reload``."""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.rate_limit import RateLimiter
from app.api.routers import applications, listings, match, meta, resume
from app.api.static import mount_frontend
from app.config import get_settings
from app.db import open_db
from app.scheduler import ScrapeScheduler
from app.services.errors import ConflictError, DomainError, InvalidTransitionError, NotFoundError

_ERROR_STATUS: dict[type[Exception], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    InvalidTransitionError: status.HTTP_409_CONFLICT,
}

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def _configure_logging() -> None:
    """Show the app's own INFO logs (scheduler, scrapes) next to uvicorn's in production."""
    app_logger = logging.getLogger("app")
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        app_logger.addHandler(handler)
        app_logger.setLevel(logging.INFO)
        app_logger.propagate = False


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _configure_logging()
    with open_db(settings.resolved_database_path()):
        pass  # creates or migrates the schema once at startup
    scheduler = ScrapeScheduler(settings) if settings.scrape_interval_hours > 0 else None
    if scheduler:
        scheduler.start()
    yield
    if scheduler:
        scheduler.stop()


async def _domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    code = _ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return JSONResponse(status_code=code, content={"detail": str(exc)})


async def _security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    for name, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="GradGuide Job Discovery API",
        version="0.1.0",
        description="Jobs for international students in the UK, from our own scraper.",
        lifespan=lifespan,
    )
    app.state.resume_limiter = RateLimiter(settings.resume_requests_per_hour, window_seconds=3600)
    app.middleware("http")(_security_headers)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(DomainError, _domain_error_handler)
    app.include_router(listings.router)
    app.include_router(applications.router)
    app.include_router(match.router)
    app.include_router(resume.router)
    app.include_router(meta.router)
    if settings.static_dir is not None:
        mount_frontend(app, settings.static_dir)  # last: it answers every other path
    return app


app = create_app()
