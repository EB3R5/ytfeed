"""Derive a vault category for a video from its playlist memberships.

Playlist names are the user's own taxonomy, so they are the categorization
signal — no transcript reading needed. When a video sits in several playlists,
the most recently added membership wins: the latest filing decision reflects
current intent, and re-adding a video to a playlist deliberately re-files it.
Ties (or missing timestamps) fall back to the smallest playlist, which is the
most specific. Same-named playlists are merged.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ytfeed.db.models import Playlist, PlaylistItem
from ytfeed.transcripts.markdown_writer import sanitize_filename


def category_for_video(session: Session, video_id: str) -> str | None:
    memberships = session.execute(
        select(Playlist.title, PlaylistItem.added_at)
        .join(PlaylistItem, PlaylistItem.playlist_id == Playlist.playlist_id)
        .where(PlaylistItem.video_id == video_id)
    ).all()
    titles = [t.strip() for t, _ in memberships if t.strip()]
    if not titles:
        return None

    # live membership count per title (merged across same-named playlists;
    # the synced item_count column can be stale)
    sizes = dict(
        session.execute(
            select(Playlist.title, func.count(PlaylistItem.id))
            .join(PlaylistItem, PlaylistItem.playlist_id == Playlist.playlist_id)
            .where(Playlist.title.in_(titles))
            .group_by(Playlist.title)
        ).all()
    )

    def rank(row) -> tuple:
        title, added_at = row
        return (added_at is not None, added_at or datetime.min, -sizes.get(title.strip(), 0))

    valid = [m for m in memberships if m.title.strip()]
    best = max(rank(m) for m in valid)
    # alphabetical among equally-ranked memberships, for determinism
    title = min(m.title.strip() for m in valid if rank(m) == best)
    return sanitize_filename(title)
