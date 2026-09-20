"""Subscriptions list and per-channel drill-down pages."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ytfeed.db.models import Channel, ChannelCategory, ChannelUpload, Video
from ytfeed.web.dependencies import get_config, get_db, templates
from ytfeed.web.routes.channel_category import _grouped

router = APIRouter()


@router.get("/subscriptions", response_class=HTMLResponse)
def subscriptions(request: Request, db: Session = Depends(get_db)):
    rows = db.execute(
        select(Channel, func.count(ChannelUpload.id), ChannelCategory)
        .outerjoin(ChannelUpload, ChannelUpload.channel_id == Channel.channel_id)
        .outerjoin(ChannelCategory, ChannelCategory.id == Channel.category_id)
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
        "category_groups": _grouped(db),
    }
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/video_list.html", context)
    return templates.TemplateResponse(request, "channel.html", context)


def _category_context(db: Session, channel: Channel, request: Request) -> dict:
    return {
        "request": request,
        "channel": channel,
        "category_groups": _grouped(db),
    }


@router.post("/channels/{channel_id}/category")
def set_channel_category(
    channel_id: str,
    request: Request,
    category_id: str = Form(""),
    db: Session = Depends(get_db),
):
    channel = db.scalar(select(Channel).where(Channel.channel_id == channel_id))
    if channel is None:
        raise HTTPException(404, "Channel not found")
    cid = int(category_id) if category_id.strip() else None
    if cid is not None and db.get(ChannelCategory, cid) is None:
        raise HTTPException(404, "Category not found")
    channel.category_id = cid
    db.commit()
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request, "partials/channel_category.html", _category_context(db, channel, request)
        )
    return RedirectResponse(f"/channels/{channel_id}", status_code=303)


@router.post("/channels/{channel_id}/notes")
def set_channel_notes(
    channel_id: str,
    request: Request,
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    channel = db.scalar(select(Channel).where(Channel.channel_id == channel_id))
    if channel is None:
        raise HTTPException(404, "Channel not found")
    channel.notes = notes
    db.commit()
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request, "partials/channel_notes.html", {"request": request, "channel": channel}
        )
    return RedirectResponse(f"/channels/{channel_id}", status_code=303)


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
