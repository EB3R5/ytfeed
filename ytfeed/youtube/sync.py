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
from ytfeed.youtube.client import YouTubeSource
from ytfeed.youtube.sync_run import (
    NULL_REPORTER,
    Reporter,
    SyncCancelled,
    _is_quota_error,
    audited_run,
)

logger = logging.getLogger(__name__)

# re-exported for callers that import these from the sync module
__all__ = ["SyncCancelled", "sync_all", "run_partial_sync", "sync_channel_uploads"]


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


def sync_subscriptions(
    session: Session, source: YouTubeSource, reporter: Reporter = NULL_REPORTER
) -> int:
    """Upsert channels from the user's subscriptions. Returns count synced."""
    count = 0
    seen_ids: list[str] = []
    # network first, writes second — keep the SQLite write lock short
    reporter.progress("subscriptions", 0, 0, "fetching subscriptions from YouTube")
    subscription_items: list[dict] = []
    for item in source.fetch_subscriptions():
        subscription_items.append(item)
        if len(subscription_items) % 50 == 0:
            reporter.progress(
                "subscriptions", 0, 0,
                f"fetched {len(subscription_items)} subscriptions so far",
            )
    reporter.progress(
        "subscriptions", 0, len(subscription_items),
        f"updating {len(subscription_items)} channels",
    )
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
    reporter.progress(
        "subscriptions", count, len(subscription_items),
        f"saved {count} channels",
    )

    # resolve uploads playlist ids for channels missing them
    missing = list(
        session.scalars(
            select(Channel).where(
                Channel.uploads_playlist_id.is_(None), Channel.channel_id.in_(seen_ids)
            )
        )
    )
    if missing:
        reporter.progress(
            "subscriptions", count, len(subscription_items),
            f"resolving uploads playlists for {len(missing)} new channels",
        )
        mapping = source.fetch_channels_content_details(
            [c.channel_id for c in missing]
        )
        for channel in missing:
            channel.uploads_playlist_id = mapping.get(channel.channel_id)
        session.commit()
    return count


def sync_my_playlists(
    session: Session, source: YouTubeSource, reporter: Reporter = NULL_REPORTER
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
    reporter.progress("playlists", 0, 0, "fetching playlist list from YouTube")
    playlist_payloads = list(source.fetch_my_playlists())
    total = len(playlist_payloads)
    for idx, item in enumerate(playlist_payloads, 1):
        title = item.get("snippet", {}).get("title", "")
        reporter.progress("playlists", idx, total, title)
        try:
            videos_upserted += _sync_playlist_payload(
                session, source, item, reporter=reporter, progress_pos=(idx, total)
            )
            playlists_synced += 1
        except SyncCancelled:
            raise
        except Exception as exc:  # one bad playlist must not kill the run
            session.rollback()
            logger.warning("playlist sync failed for %s: %s", title, exc)
            if _is_quota_error(exc):
                raise
    return playlists_synced, videos_upserted


def _sync_playlist_payload(
    session: Session,
    source: YouTubeSource,
    item: dict,
    *,
    force: bool = False,
    reporter: Reporter = NULL_REPORTER,
    progress_pos: tuple[int, int] = (0, 0),
) -> int:
    """Upsert one playlist (+ items if changed or force) from a playlists().list payload."""
    playlist_id = item["id"]
    snippet = item.get("snippet", {})
    title = snippet.get("title", "")
    yt_item_count = item.get("contentDetails", {}).get("itemCount", 0)

    playlist = session.scalar(
        select(Playlist).where(Playlist.playlist_id == playlist_id)
    )
    needs_walk = force or playlist is None or playlist.synced_item_count != yt_item_count
    # network before any DB write — see sync_my_playlists
    items: list[dict] = []
    if needs_walk:
        for page in source.fetch_playlist_items_paged(playlist_id):
            items.extend(page)
            if len(items) < yt_item_count:  # big playlist: show walk progress
                reporter.progress(
                    "playlists", *progress_pos,
                    f"{title} — fetched {len(items)}/{yt_item_count} items",
                )

    if playlist is None:
        playlist = Playlist(playlist_id=playlist_id)
        session.add(playlist)
    playlist.title = title or playlist.title or ""
    playlist.description = snippet.get("description", playlist.description or "")
    playlist.thumbnail_url = _best_thumbnail(snippet) or playlist.thumbnail_url
    playlist.item_count = yt_item_count
    playlist.last_synced_at = utcnow().replace(tzinfo=None)

    if not needs_walk:
        session.commit()
        return 0

    videos_upserted = 0
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
    # store YouTube's claimed count, not len(items): playlists with deleted
    # videos return fewer items than itemCount forever, and a raw-count
    # mismatch would force a full re-walk on every sync
    playlist.synced_item_count = yt_item_count
    session.commit()
    return videos_upserted


def sync_channel_uploads(
    session: Session,
    source: YouTubeSource,
    channel: Channel,
    *,
    force_full: bool = False,
    initial_backfill: int = 50,
    reporter: Reporter = NULL_REPORTER,
    progress_pos: tuple[int, int] = (0, 0),
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

    page_num = 0
    for page in source.fetch_playlist_items_paged(channel.uploads_playlist_id):
        page_num += 1
        if page_num > 1:  # first page is covered by the caller's per-channel update
            reporter.progress(
                "channels", *progress_pos,
                f"{channel.title} — page {page_num}, {new_count} new videos so far",
            )
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


def run_partial_sync(
    session: Session,
    source: YouTubeSource,
    kind: str,
    *,
    playlist_id: str | None = None,
    channel_id: str | None = None,
    force_full: bool = False,
    initial_backfill: int = 50,
) -> SyncRun:
    """Audited scoped sync: kind = 'subscriptions' | 'playlists' | 'playlist' | 'channel'."""
    with audited_run(session, kind, source) as reporter:
        run = reporter.run
        if kind == "subscriptions":
            run.channels_synced = sync_subscriptions(session, source, reporter)
        elif kind == "playlists":
            _, run.videos_upserted = sync_my_playlists(session, source, reporter)
        elif kind == "playlist":
            if not playlist_id:
                raise ValueError("playlist_id required for kind='playlist'")
            payloads = source.fetch_playlists_by_ids([playlist_id])
            if not payloads:
                raise ValueError(f"playlist {playlist_id} not found on YouTube")
            title = payloads[0].get("snippet", {}).get("title", playlist_id)
            reporter.progress("playlist", 1, 1, title)
            # explicit priority sync: force the item walk even if unchanged
            run.videos_upserted = _sync_playlist_payload(
                session, source, payloads[0], force=True, reporter=reporter, progress_pos=(1, 1)
            )
        elif kind == "channel":
            if not channel_id:
                raise ValueError("channel_id required for kind='channel'")
            channel = session.scalar(
                select(Channel).where(Channel.channel_id == channel_id)
            )
            if channel is None:
                raise ValueError(f"channel {channel_id} not in database")
            reporter.progress("channels", 1, 1, channel.title)
            run.channels_synced = 1
            run.videos_upserted = sync_channel_uploads(
                session,
                source,
                channel,
                force_full=force_full,
                initial_backfill=initial_backfill,
                reporter=reporter,
                progress_pos=(1, 1),
            )
        else:
            raise ValueError(f"unknown sync kind: {kind}")
    return reporter.run


def sync_all(
    session: Session,
    source: YouTubeSource,
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

    with audited_run(session, "full" if not force_full else "full-force", source) as reporter:
        run = reporter.run
        report("Syncing subscriptions…")
        run.channels_synced = sync_subscriptions(session, source, reporter)

        report("Syncing playlists…")
        _, videos_from_playlists = sync_my_playlists(session, source, reporter)
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
            reporter.progress("channels", i, len(channels), channel.title)
            try:
                run.videos_upserted += sync_channel_uploads(
                    session,
                    source,
                    channel,
                    force_full=force_full,
                    initial_backfill=config.sync.initial_backfill,
                    reporter=reporter,
                    progress_pos=(i, len(channels)),
                )
            except SyncCancelled:
                raise
            except Exception as exc:  # one bad channel must not kill the run
                session.rollback()
                failed_channels += 1
                logger.warning("uploads sync failed for %s: %s", channel.title, exc)
                reporter.log(f"[channels {i}/{len(channels)}] {channel.title} FAILED: {exc}")
                if _is_quota_error(exc):
                    raise
        if failed_channels:
            run.error_message = f"{failed_channels} channel(s) failed; see logs"

    run = reporter.run
    if run.phase == "cancelled":
        report("Sync stopped by user.")
    else:
        report(
            f"Sync complete: {run.channels_synced} channels, {run.videos_upserted} videos upserted."
        )
    return run
