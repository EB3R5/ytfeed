"""FastAPI app: Recents | Subscriptions | Playlists | Queue | Settings."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ytfeed.db.session import init_db
from ytfeed.web.dependencies import get_config
from ytfeed.web.routes import channel, playlist, queue, recents, settings, storage

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
app.include_router(storage.router)


RETRY_POLL_SECONDS = 60


def _retry_monitor() -> None:
    """Pick up deferred queue items (e.g. IP-block retries) once they're due."""
    import time

    from ytfeed.db.session import get_session_factory
    from ytfeed.transcripts.pipeline import has_due_pending, run_transcription_pipeline

    config = get_config()
    factory = get_session_factory(config)
    while True:
        time.sleep(RETRY_POLL_SECONDS)
        try:
            with factory() as session:
                if has_due_pending(session):
                    run_transcription_pipeline(session, config)
        except Exception:
            logging.getLogger(__name__).exception("retry monitor pass failed")


@app.on_event("startup")
def _startup() -> None:
    config = get_config()
    init_db(config)
    # a restart kills any in-flight pipeline run; un-stick its queue items
    from ytfeed.db.session import get_session_factory
    from ytfeed.transcripts.pipeline import recover_stale_processing

    with get_session_factory(config)() as session:
        recover_stale_processing(session)

    threading.Thread(target=_retry_monitor, daemon=True, name="retry-monitor").start()
