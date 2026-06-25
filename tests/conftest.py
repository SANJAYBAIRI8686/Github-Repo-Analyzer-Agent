from __future__ import annotations

import pytest

from app.core.config import get_settings
from app import db as app_db
from app.db import session as db_session


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-test-secret-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", "/tmp/chroma-test")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("CELERY_BROKER_URL", "memory://")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "rpc://")
    if getattr(db_session, "_engine", None) is not None:
        db_session._engine.dispose()
    db_session._engine = None
    db_session._SessionLocal = None
    get_settings.cache_clear()
    yield
    if getattr(db_session, "_engine", None) is not None:
        db_session._engine.dispose()
    db_session._engine = None
    db_session._SessionLocal = None
    get_settings.cache_clear()