"""FastAPI app: Recents | Subscriptions | Playlists | Queue | Settings."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ytfeed.db.session import init_db
from ytfeed.web.dependencies import get_config
from ytfeed.web.routes import channel, playlist, queue, recents, settings

app = FastAPI(title="ytfeed")

app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
    name="static",
)

app.include_router(recents.router)
app.include_router(channel.router)
app.include_router(playlist.router)
app.include_router(queue.router)
app.include_router(settings.router)


@app.on_event("startup")
def _startup() -> None:
    init_db(get_config())
