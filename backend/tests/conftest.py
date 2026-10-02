import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import connect, init_db


@pytest.fixture
def db() -> Iterator[sqlite3.Connection]:
    """An initialised in-memory database."""
    conn = connect(":memory:")
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point the app settings at a fresh on-disk database for this test."""
    path = tmp_path / "test.db"
    monkeypatch.setenv("GG_DATABASE_PATH", str(path))
    get_settings.cache_clear()
    yield path
    get_settings.cache_clear()


@pytest.fixture
def client(db_path: Path) -> Iterator[TestClient]:
    from app.api.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
