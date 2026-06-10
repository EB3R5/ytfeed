"""Settings page: config summary, DB stats, manual sync."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ytfeed.db.models import Channel, Playlist, SyncRun, Video
from ytfeed.web.dependencies import get_config, get_db, templates

router = APIRouter()


def _mask(path: object) -> str:
    s = str(path)
    return "…/" + "/".join(s.split("/")[-2:]) if "/" in s else s


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    config = get_config()
    stats = {
        "channels": db.scalar(select(func.count(Channel.id))) or 0,
        "playlists": db.scalar(select(func.count(Playlist.id))) or 0,
        "videos": db.scalar(select(func.count(Video.id))) or 0,
        "transcribed": db.scalar(
            select(func.count(Video.id)).where(Video.transcript_status == "done")
        )
        or 0,
    }
    channels = list(db.scalars(select(Channel).order_by(Channel.last_synced_at.desc().nullslast())))
    last_run = db.scalar(select(SyncRun).order_by(SyncRun.started_at.desc()).limit(1))
    config_summary = {
        "db_path": _mask(config.paths.db_path),
        "client_secret_path": _mask(config.paths.client_secret_path),
        "token_path": _mask(config.paths.token_path),
        "rag_output_dir": str(config.paths.rag_output_dir),
        "initial_backfill": config.sync.initial_backfill,
        "notebooklm_enabled": config.notebooklm.enabled,
        "notebooklm_batch_size": config.notebooklm.batch_size,
        "download_audio": config.download.download_audio,
    }
    context = {
        "request": request,
        "active_page": "settings",
        "stats": stats,
        "channels": channels,
        "last_run": last_run,
        "config_summary": config_summary,
    }
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/sync_status.html", context)
    return templates.TemplateResponse(request, "settings.html", context)


def _run_sync_bg() -> None:
    from ytfeed.db.session import get_session_factory
    from ytfeed.youtube.auth import get_youtube_client
    from ytfeed.youtube.sync import sync_all

    config = get_config()
    youtube = get_youtube_client(config)
    factory = get_session_factory(config)
    with factory() as session:
        sync_all(session, youtube, config)


@router.post("/settings/sync")
def trigger_sync(request: Request, background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_sync_bg)
    return RedirectResponse("/settings", status_code=303)
