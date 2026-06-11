"""Sync engine: subscriptions, playlists, and per-channel uploads with early-stop."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ytfeed.config import Config
from ytfeed.db.models import (
    Channel,
    ChannelUpload,
    Playlist,
    PlaylistItem,
    SyncRun,
    Video,
    utcnow,
)
from ytfeed.youtube import client as yt

logger = logging.getLogger(__name__)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # store naive UTC for SQLite comparability
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return None


def _best_thumbnail(snippet: dict) -> str | None:
    thumbs = snippet.get("thumbnails", {})
    for key in ("medium", "high", "default", "standard", "maxres"):
        if key in thumbs and thumbs[key].get("url"):
            return thumbs[key]["url"]
    return None


def _upsert_video_from_playlist_item(session: Session, item: dict) -> Video | None:
    """Upsert a videos row from a playlistItems resource. Returns the Video, or None if not a video."""
    content = item.get("contentDetails", {})
    snippet = item.get("snippet", {})
    video_id = content.get("videoId") or snippet.get("resourceId", {}).get("videoId")
    if not video_id:
        return None

    video = session.scalar(select(Video).where(Video.video_id == video_id))
    published = _parse_dt(content.get("videoPublishedAt") or snippet.get("publishedAt"))
    owner_channel_id = snippet.get("videoOwnerChannelId") or snippet.get("channelId")
    owner_channel_title = snippet.get("videoOwnerChannelTitle") or snippet.get("channelTitle", "")

    if video is None:
        video = Video(
            video_id=video_id,
            channel_id=owner_channel_id,
            channel_title=owner_channel_title or "",
            title=snippet.get("title", ""),
            description=snippet.get("description", ""),
            thumbnail_url=_best_thumbnail(snippet),
            published_at=published,
            source="sync",
        )
        session.add(video)
    else:
        # refresh metadata but never clobber transcript state
        video.title = snippet.get("title", video.title) or video.title
        if snippet.get("description"):
            video.description = snippet["description"]
        video.thumbnail_url = _best_thumbnail(snippet) or video.thumbnail_url
        if published and not video.published_at:
            video.published_at = published
        if owner_channel_id and not video.channel_id:
            video.channel_id = owner_channel_id
        if owner_channel_title and not video.channel_title:
            video.channel_title = owner_channel_title
    return video


def sync_subscriptions(session: Session, youtube) -> int:
    """Upsert channels from the user's subscriptions. Returns count synced."""
    count = 0
    seen_ids: list[str] = []
    # network first, writes second — keep the SQLite write lock short
    subscription_items = list(yt.fetch_subscriptions(youtube))
    for item in subscription_items:
        snippet = item.get("snippet", {})
        channel_id = snippet.get("resourceId", {}).get("channelId")
        if not channel_id:
            continue
        seen_ids.append(channel_id)
        channel = session.scalar(select(Channel).where(Channel.channel_id == channel_id))
        if channel is None:
            channel = Channel(channel_id=channel_id)
            session.add(channel)
        channel.title = snippet.get("title", channel.title or "")
        channel.description = snippet.get("description", channel.description or "")
        channel.thumbnail_url = _best_thumbnail(snippet) or channel.thumbnail_url
        channel.subscribed_at = _parse_dt(snippet.get("publishedAt")) or channel.subscribed_at
        channel.is_active = True
        count += 1

    # channels no longer in the subscription list: deactivate so they stop
    # consuming upload-sync quota (data is kept; resubscribing reactivates)
    stale = session.scalars(
        select(Channel).where(
            Channel.is_active.is_(True), Channel.channel_id.not_in(seen_ids)
        )
    )
    for channel in stale:
        channel.is_active = False
        logger.info("deactivated unsubscribed channel: %s", channel.title)
    session.commit()

    # resolve uploads playlist ids for channels missing them
    missing = list(
        session.scalars(
            select(Channel).where(
                Channel.uploads_playlist_id.is_(None), Channel.channel_id.in_(seen_ids)
            )
        )
    )
    if missing:
        mapping = yt.fetch_channels_content_details(
            youtube, [c.channel_id for c in missing]
        )
        for channel in missing:
            channel.uploads_playlist_id = mapping.get(channel.channel_id)
        session.commit()
    return count


def _progress(session: Session, run: SyncRun | None, phase: str, current: int, total: int, detail: str) -> None:
    if run is None:
        return
    run.phase = phase
    run.progress_current = current
    run.progress_total = total
    run.progress_detail = detail[:255]
    run.api_calls = yt.get_api_calls() - getattr(run, "_api_calls_at_start", 0)
    session.commit()


def sync_my_playlists(
    session: Session, youtube, run: SyncRun | None = None
) -> tuple[int, int]:
    """Upsert playlists + playlist_items + videos. Returns (playlists, videos_upserted).

    Quota saver: a playlist's item walk is skipped when YouTube's itemCount
    matches the raw count from our last walk — only changed/new playlists
    cost API pages.
    """
    playlists_synced = 0
    videos_upserted = 0
    # ALL network I/O happens before any DB write in each iteration: a dirty
    # ORM object + any SELECT autoflushes and takes the SQLite write lock, so
    # fetching pages mid-transaction would hold that lock for the whole
    # playlist and starve the web app.
    playlist_payloads = list(yt.fetch_my_playlists(youtube))
    total = len(playlist_payloads)
    for idx, item in enumerate(playlist_payloads, 1):
        playlist_id = item["id"]
        snippet = item.get("snippet", {})
        title = snippet.get("title", "")
        yt_item_count = item.get("contentDetails", {}).get("itemCount", 0)
        _progress(session, run, "playlists", idx, total, title)

        try:
            playlist = session.scalar(
                select(Playlist).where(Playlist.playlist_id == playlist_id)
            )
            needs_walk = (
                playlist is None or playlist.synced_item_count != yt_item_count
            )
            items = (
                list(yt.fetch_playlist_items(youtube, playlist_id))
                if needs_walk
                else []
            )

            if playlist is None:
                playlist = Playlist(playlist_id=playlist_id)
                session.add(playlist)
            playlist.title = title or playlist.title or ""
            playlist.description = snippet.get("description", playlist.description or "")
            playlist.thumbnail_url = _best_thumbnail(snippet) or playlist.thumbnail_url
            playlist.item_count = yt_item_count
            playlist.last_synced_at = utcnow().replace(tzinfo=None)
            playlists_synced += 1

            if not needs_walk:
                session.commit()
                continue

            existing = {
                pi.video_id: pi
                for pi in session.scalars(
                    select(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id)
                )
            }
            seen_ids: set[str] = set()
            for pi_item in items:
                video = _upsert_video_from_playlist_item(session, pi_item)
                if video is None:
                    continue
                videos_upserted += 1
                seen_ids.add(video.video_id)
                snippet_pi = pi_item.get("snippet", {})
                pi = existing.get(video.video_id)
                if pi is None:
                    # YouTube playlists can contain the same video twice; keep one row
                    pi = PlaylistItem(playlist_id=playlist_id, video_id=video.video_id)
                    session.add(pi)
                    existing[video.video_id] = pi
                pi.position = snippet_pi.get("position", 0)
                pi.added_at = _parse_dt(snippet_pi.get("publishedAt"))
            # drop rows for videos removed from the playlist
            for vid, pi in existing.items():
                if vid not in seen_ids:
                    session.delete(pi)
            playlist.synced_item_count = len(items)
            session.commit()
        except Exception as exc:  # one bad playlist must not kill the run
            session.rollback()
            logger.warning("playlist sync failed for %s: %s", title, exc)
            if _is_quota_error(exc):
                raise
    return playlists_synced, videos_upserted


def _is_quota_error(exc: Exception) -> bool:
    return "quotaExceeded" in str(exc)


def sync_channel_uploads(
    session: Session,
    youtube,
    channel: Channel,
    *,
    force_full: bool = False,
    initial_backfill: int = 50,
) -> int:
    """Sync a channel's uploads playlist newest-first with early-stop.

    Stops (unless force_full) when hitting a video already recorded for this
    channel or older than channel.last_video_published_at. First-ever sync is
    capped at initial_backfill videos.
    """
    if not channel.uploads_playlist_id:
        logger.warning("channel %s has no uploads_playlist_id; skipping", channel.channel_id)
        return 0

    known_ids = {
        cu.video_id
        for cu in session.scalars(
            select(ChannelUpload).where(ChannelUpload.channel_id == channel.channel_id)
        )
    }
    is_first_sync = not known_ids
    new_count = 0
    newest_published: datetime | None = channel.last_video_published_at
    stop = False

    for page in yt.fetch_playlist_items_paged(youtube, channel.uploads_playlist_id):
        for item in page:
            content = item.get("contentDetails", {})
            video_id = content.get("videoId")
            if not video_id:
                continue
            published = _parse_dt(
                content.get("videoPublishedAt")
                or item.get("snippet", {}).get("publishedAt")
            )

            if not force_full:
                if video_id in known_ids:
                    stop = True
                    break
                if (
                    channel.last_video_published_at
                    and published
                    and published <= channel.last_video_published_at
                ):
                    stop = True
                    break
                if is_first_sync and new_count >= initial_backfill:
                    stop = True
                    break

            if video_id not in known_ids:
                video = _upsert_video_from_playlist_item(session, item)
                if video is None:
                    continue
                if not video.channel_id:
                    video.channel_id = channel.channel_id
                if not video.channel_title:
                    video.channel_title = channel.title
                session.add(
                    ChannelUpload(
                        channel_id=channel.channel_id,
                        video_id=video_id,
                        published_at=published,
                    )
                )
                known_ids.add(video_id)
                new_count += 1
            if published and (newest_published is None or published > newest_published):
                newest_published = published
        # commit per page so the write lock is released before the next
        # network fetch
        session.commit()
        if stop:
            break

    channel.last_synced_at = utcnow().replace(tzinfo=None)
    channel.last_video_published_at = newest_published
    session.commit()
    return new_count


def sync_all(
    session: Session,
    youtube,
    config: Config,
    *,
    force_full: bool = False,
    progress_cb=None,
) -> SyncRun:
    """Run subscriptions -> playlists -> per-channel uploads, audit in sync_runs."""

    def report(msg: str) -> None:
        logger.info(msg)
        if progress_cb:
            progress_cb(msg)

    run = SyncRun(kind="full" if not force_full else "full-force")
    run._api_calls_at_start = yt.get_api_calls()  # type: ignore[attr-defined]
    session.add(run)
    session.commit()

    try:
        report("Syncing subscriptions…")
        _progress(session, run, "subscriptions", 0, 0, "fetching subscriptions")
        channels_synced = sync_subscriptions(session, youtube)
        run.channels_synced = channels_synced

        report("Syncing playlists…")
        _, videos_from_playlists = sync_my_playlists(session, youtube, run)
        run.videos_upserted += videos_from_playlists

        # never-synced channels first: quota-limited runs make forward
        # progress instead of re-walking the same head every time
        channels = list(
            session.scalars(
                select(Channel)
                .where(Channel.is_active.is_(True))
                .order_by(Channel.last_synced_at.asc().nullsfirst())
            )
        )
        failed_channels = 0
        for i, channel in enumerate(channels, 1):
            report(f"Syncing uploads {i}/{len(channels)}: {channel.title}")
            _progress(session, run, "channels", i, len(channels), channel.title)
            try:
                run.videos_upserted += sync_channel_uploads(
                    session,
                    youtube,
                    channel,
                    force_full=force_full,
                    initial_backfill=config.sync.initial_backfill,
                )
            except Exception as exc:  # one bad channel must not kill the run
                session.rollback()
                failed_channels += 1
                logger.warning("uploads sync failed for %s: %s", channel.title, exc)
                if _is_quota_error(exc):
                    raise
        if failed_channels:
            run.error_message = f"{failed_channels} channel(s) failed; see logs"
        run.phase = "done"
        run.api_calls = yt.get_api_calls() - getattr(run, "_api_calls_at_start", 0)
        run.finished_at = utcnow().replace(tzinfo=None)
        session.commit()
        report(
            f"Sync complete: {run.channels_synced} channels, {run.videos_upserted} videos upserted."
        )
    except Exception as exc:  # record failure in the audit row, then re-raise
        session.rollback()
        run.error_message = (
            "YouTube API daily quota exceeded — resets at midnight Pacific. "
            "Progress is saved; run sync again tomorrow."
            if _is_quota_error(exc)
            else str(exc)
        )
        run.api_calls = yt.get_api_calls() - getattr(run, "_api_calls_at_start", 0)
        run.finished_at = utcnow().replace(tzinfo=None)
        session.commit()
        raise
    return run
