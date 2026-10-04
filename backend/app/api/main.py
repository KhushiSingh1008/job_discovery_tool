"""FastAPI application entry point: ``uvicorn app.api.main:app --reload``."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import applications, listings, match, meta, resume
from app.config import get_settings
from app.db import open_db
from app.services.errors import ConflictError, DomainError, InvalidTransitionError, NotFoundError

_ERROR_STATUS: dict[type[Exception], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    InvalidTransitionError: status.HTTP_409_CONFLICT,
}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    with open_db(get_settings().resolved_database_path()):
        pass  # creates the schema once at startup
    yield


async def _domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    code = _ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return JSONResponse(status_code=code, content={"detail": str(exc)})


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="GradGuide Job Discovery API",
        version="0.1.0",
        description="Jobs for international students in the UK, from our own scraper.",
        lifespan=lifespan,
    )
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
    return app


app = create_app()
