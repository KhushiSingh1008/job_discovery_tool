"""FastAPI application entry point: ``uvicorn app.api.main:app --reload``."""

import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_db
from app.config import get_settings
from app.db import open_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    with open_db(get_settings().resolved_database_path()):
        pass  # creates the schema once at startup
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="GradGuide Job Discovery API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["meta"])
    def health(db: Annotated[sqlite3.Connection, Depends(get_db)]) -> dict[str, object]:
        listings = db.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
        return {"status": "ok", "listings": listings}

    return app


app = create_app()
