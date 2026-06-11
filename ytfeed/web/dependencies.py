"""Shared FastAPI dependencies: config, DB session, templates."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ytfeed.config import Config, load_config
from ytfeed.db.session import get_session_factory

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def asset_v(filename: str) -> int:
    """File mtime as a cache-busting version for static asset URLs."""
    try:
        return int((STATIC_DIR / filename).stat().st_mtime)
    except OSError:
        return 0


templates.env.globals["asset_v"] = asset_v


@lru_cache(maxsize=1)
def get_config() -> Config:
    return load_config()


def get_db() -> Iterator[Session]:
    factory = get_session_factory(get_config())
    session = factory()
    try:
        yield session
    finally:
        session.close()
