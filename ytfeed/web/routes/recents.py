"""Recents page: newest videos from monitored (or one-off picked) channels."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ytfeed.db.models import Channel, Video
from ytfeed.web.dependencies import get_db, templates

router = APIRouter()

PAGE_SIZE = 100


def _recent_videos(
    db: Session,
    channel_ids: list[str],
    q: str | None,
    transcript_status: str | None,
) -> list[Video]:
    if not channel_ids:
        return []
    stmt = (
        select(Video)
        .where(Video.channel_id.in_(channel_ids))
        .order_by(Video.published_at.desc().nullslast())
        .limit(PAGE_SIZE)
    )
    if q:
        stmt = stmt.where(Video.title.ilike(f"%{q}%"))
    if transcript_status:
        stmt = stmt.where(Video.transcript_status == transcript_status)
    return list(db.scalars(stmt))


def _selected_channel_ids(
    db: Session, picked: list[str] | None
) -> tuple[list[str], bool]:
    """Picked channels override; otherwise monitored channels. Returns (ids, used_picker)."""
    if picked:
        return picked, True
    monitored = list(
        db.scalars(select(Channel.channel_id).where(Channel.is_monitored.is_(True)))
    )
    return monitored, False


@router.get("/", response_class=HTMLResponse)
def recents(
    request: Request,
    db: Session = Depends(get_db),
    channel: list[str] | None = Query(default=None),
    q: str | None = None,
    transcript_status: str | None = None,
):
    channels = list(db.scalars(select(Channel).order_by(Channel.title)))
    channel_ids, used_picker = _selected_channel_ids(db, channel)
    videos = _recent_videos(db, channel_ids, q, transcript_status)
    context = {
        "request": request,
        "active_page": "recents",
        "channels": channels,
        "selected_channel_ids": set(channel_ids),
        "used_picker": used_picker,
        "videos": videos,
        "q": q or "",
        "transcript_status": transcript_status or "",
    }
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/video_list.html", context)
    return templates.TemplateResponse(request, "recents.html", context)


@router.post("/channels/{channel_id}/monitor")
def toggle_monitor(
    channel_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    ch = db.scalar(select(Channel).where(Channel.channel_id == channel_id))
    if ch is not None:
        ch.is_monitored = not ch.is_monitored
        db.commit()
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request, "partials/monitor_button.html", {"request": request, "channel": ch}
        )
    return RedirectResponse(request.headers.get("referer", "/"), status_code=303)
