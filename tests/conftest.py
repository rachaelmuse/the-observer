from __future__ import annotations

import pytest

from observer.db import init_db, reset_engine
from observer.registry import seed_registry


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSERVER_ARCHIVE_DIR", str(tmp_path / "archive"))
    monkeypatch.setenv("OBSERVER_RATE_LIMIT_SECONDS", "0")
    monkeypatch.setenv("OBSERVER_MAX_FETCH_BYTES", "5242880")
    monkeypatch.setenv("OLLAMA_MODEL", "")
    dbfile = tmp_path / "observer.db"
    reset_engine(f"sqlite:///{dbfile.as_posix()}")
    init_db()
    seed_registry()
    return tmp_path
