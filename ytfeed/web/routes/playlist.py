"""Playlists list and per-playlist video pages."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ytfeed.db.models import Playlist, PlaylistItem, Video
from ytfeed.web.dependencies import get_db, templates

router = APIRouter()


@router.get("/playlists", response_class=HTMLResponse)
def playlists(request: Request, db: Session = Depends(get_db)):
    rows = list(db.scalars(select(Playlist).order_by(Playlist.title)))
    return templates.TemplateResponse(
        request,
        "playlists.html",
        {"request": request, "active_page": "playlists", "playlists": rows},
    )


@router.get("/playlists/{playlist_id}", response_class=HTMLResponse)
def playlist_page(
    playlist_id: str,
    request: Request,
    db: Session = Depends(get_db),
    q: str | None = None,
):
    playlist = db.scalar(select(Playlist).where(Playlist.playlist_id == playlist_id))
    if playlist is None:
        raise HTTPException(404, "Playlist not found")
    stmt = (
        select(Video)
        .join(PlaylistItem, PlaylistItem.video_id == Video.video_id)
        .where(PlaylistItem.playlist_id == playlist_id)
        .order_by(PlaylistItem.position)
    )
    if q:
        stmt = stmt.where(Video.title.ilike(f"%{q}%"))
    videos = list(db.scalars(stmt))
    context = {
        "request": request,
        "active_page": "playlists",
        "playlist": playlist,
        "videos": videos,
        "q": q or "",
    }
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/video_list.html", context)
    return templates.TemplateResponse(request, "playlist.html", context)
