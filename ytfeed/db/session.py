"""Engine/session factory and schema creation."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ytfeed.config import Config
from ytfeed.db.models import Base

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine(config: Config) -> Engine:
    global _engine
    if _engine is None:
        db_path = Path(config.paths.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{db_path}", echo=False, connect_args={"timeout": 30}
        )

        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _record):
            # WAL lets the web app read/write while a sync is committing.
            # busy_timeout first so the WAL switch waits out other writers;
            # WAL is persistent in the DB file, so failure here just means
            # another connection set it already or will.
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA busy_timeout=30000")
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
            except Exception:
                pass
            cursor.close()

    return _engine


def get_session_factory(config: Config) -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(config), expire_on_commit=False)
    return _session_factory


def init_db(config: Config) -> None:
    Base.metadata.create_all(get_engine(config))
