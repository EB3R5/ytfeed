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
    engine = get_engine(config)
    Base.metadata.create_all(engine)
    # create_all never alters existing tables; add columns introduced after a
    # table first shipped (poor man's migration — SQLite, additive only)
    added_columns = {
        "sync_runs": [
            ("phase", "VARCHAR(32)"),
            ("progress_current", "INTEGER NOT NULL DEFAULT 0"),
            ("progress_total", "INTEGER NOT NULL DEFAULT 0"),
            ("progress_detail", "VARCHAR(255)"),
            ("api_calls", "INTEGER NOT NULL DEFAULT 0"),
            ("log", "TEXT NOT NULL DEFAULT ''"),
            ("cancel_requested", "BOOLEAN NOT NULL DEFAULT 0"),
        ]
    }
    with engine.connect() as conn:
        for table, columns in added_columns.items():
            existing = {
                row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")
            }
            for name, ddl in columns:
                if name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
        conn.commit()
