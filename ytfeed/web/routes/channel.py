"""Subscriptions list and per-channel drill-down pages."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ytfeed.db.models import Channel, ChannelUpload, Video
from ytfeed.web.dependencies import get_config, get_db, templates

router = APIRouter()


@router.get("/subscriptions", response_class=HTMLResponse)
def subscriptions(request: Request, db: Session = Depends(get_db)):
    rows = db.execute(
        select(Channel, func.count(ChannelUpload.id))
        .outerjoin(ChannelUpload, ChannelUpload.channel_id == Channel.channel_id)
        .where(Channel.is_active.is_(True))
        .group_by(Channel.id)
        .order_by(Channel.title)
    ).all()
    return templates.TemplateResponse(
        request,
        "subscriptions.html",
        {
            "request": request,
            "active_page": "subscriptions",
            "channel_rows": rows,
        },
    )


@router.get("/channels/{channel_id}", response_class=HTMLResponse)
def channel_page(
    channel_id: str,
    request: Request,
    db: Session = Depends(get_db),
    q: str | None = None,
):
    channel = db.scalar(select(Channel).where(Channel.channel_id == channel_id))
    if channel is None:
        raise HTTPException(404, "Channel not found")
    stmt = (
        select(Video)
        .join(ChannelUpload, ChannelUpload.video_id == Video.video_id)
        .where(ChannelUpload.channel_id == channel_id)
        .order_by(Video.published_at.desc().nullslast())
    )
    if q:
        stmt = stmt.where(Video.title.ilike(f"%{q}%"))
    videos = list(db.scalars(stmt))
    context = {
        "request": request,
        "active_page": "subscriptions",
        "channel": channel,
        "videos": videos,
        "q": q or "",
    }
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/video_list.html", context)
    return templates.TemplateResponse(request, "channel.html", context)


def _run_channel_sync(channel_id: str, force_full: bool) -> None:
    from ytfeed.db.session import get_session_factory
    from ytfeed.youtube.client import build_source
    from ytfeed.youtube.sync import run_partial_sync

    config = get_config()
    source = build_source(config)
    factory = get_session_factory(config)
    with factory() as session:
        # audited SyncRun: progress + log show up on the settings page
        run_partial_sync(
            session,
            source,
            "channel",
            channel_id=channel_id,
            force_full=force_full,
            initial_backfill=config.sync.initial_backfill,
        )


@router.post("/channels/{channel_id}/refresh")
def refresh_channel(
    channel_id: str, request: Request, background_tasks: BackgroundTasks
):
    background_tasks.add_task(_run_channel_sync, channel_id, False)
    return RedirectResponse(f"/channels/{channel_id}", status_code=303)


@router.post("/channels/{channel_id}/backfill")
def backfill_channel(
    channel_id: str, request: Request, background_tasks: BackgroundTasks
):
    background_tasks.add_task(_run_channel_sync, channel_id, True)
    return RedirectResponse(f"/channels/{channel_id}", status_code=303)
