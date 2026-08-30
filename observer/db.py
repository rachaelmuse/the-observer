from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from observer.models import Base
from observer.settings import load_settings, resolve_path

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _sqlite_url(url: str) -> str:
    if url.startswith("sqlite:///./"):
        db_path = resolve_path(url.replace("sqlite:///./", "./"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path.as_posix()}"
    return url


def make_engine(url: str | None = None) -> Engine:
    settings = load_settings()
    db_url = _sqlite_url(url or settings.observer_database_url)
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    engine = create_engine(db_url, future=True, connect_args=connect_args)
    if db_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _fk(dbapi_conn, _rec):  # type: ignore[no-untyped-def]
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = make_engine()
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def reset_engine(url: str | None = None) -> Engine:
    """Test helper: replace the process engine."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = make_engine(url)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def init_db(engine: Engine | None = None) -> None:
    target = engine or get_engine()
    Base.metadata.create_all(target)
    archive = resolve_path(load_settings().observer_archive_dir)
    archive.mkdir(parents=True, exist_ok=True)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
