"""3-tier transcription orchestration: NotebookLM -> youtube-transcript-api -> placeholder.

Work is processed in batches of config.notebooklm.batch_size (50 = one
notebook on the free tier). Each batch runs all three tiers and is committed
to the DB before the next batch starts, so the queue page shows progress in
waves instead of going dark for the whole run.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ytfeed.config import Config
from ytfeed.db.models import TranscriptionQueueItem, Video, utcnow
from ytfeed.transcripts import placeholder, youtube_api_provider
from ytfeed.transcripts.base import TranscriptResult, VideoRef
from ytfeed.transcripts.markdown_writer import write_transcript_file

logger = logging.getLogger(__name__)


def _now():
    return utcnow().replace(tzinfo=None)


def _select_queue_items(
    session: Session, video_ids: list[str] | None, limit: int | None
) -> list[TranscriptionQueueItem]:
    stmt = (
        select(TranscriptionQueueItem)
        .where(TranscriptionQueueItem.status == "pending")
        .order_by(TranscriptionQueueItem.requested_at)
    )
    if video_ids:
        stmt = stmt.where(TranscriptionQueueItem.video_id.in_(video_ids))
    if limit:
        stmt = stmt.limit(limit)
    return list(session.scalars(stmt))


def _published_str(video: Video) -> str | None:
    return video.published_at.strftime("%Y-%m-%dT%H:%M:%SZ") if video.published_at else None


def recover_stale_processing(session: Session) -> int:
    """Reset items stuck in 'processing' (e.g. after a server restart killed a run)."""
    stale = list(
        session.scalars(
            select(TranscriptionQueueItem).where(
                TranscriptionQueueItem.status == "processing"
            )
        )
    )
    for item in stale:
        item.status = "pending"
        video = session.scalar(select(Video).where(Video.video_id == item.video_id))
        if video is not None and video.transcript_status == "in_progress":
            video.transcript_status = "queued"
    if stale:
        session.commit()
        logger.info("recovered %d stale processing queue items", len(stale))
    return len(stale)


def _finalize_item(
    session: Session,
    config: Config,
    item: TranscriptionQueueItem,
    video: Video,
    result: TranscriptResult | None,
) -> None:
    """Write the transcript/placeholder file and update DB rows for one video."""
    rag_dir = Path(config.paths.rag_output_dir)

    if result and result.success:
        # enrich the DB description from yt-dlp when sync only had a stub;
        # the vault file stays transcript-only
        if not video.description:
            from ytfeed.metadata import ytdlp_client

            meta = ytdlp_client.fetch_video_metadata(video.video_id)
            if meta:
                video.description = meta.get("description") or ""
                if meta.get("duration") and not video.duration_seconds:
                    video.duration_seconds = int(meta["duration"])

        path = write_transcript_file(
            rag_dir,
            video_id=video.video_id,
            title=video.title,
            channel=video.channel_title,
            published=_published_str(video),
            transcript=result.text or "",
            source=result.source or "unknown",
        )
        video.transcript_status = "done"
        video.transcript_source = result.source
        video.transcript_path = str(path)
        item.status = "done"
        item.error_message = None
    else:
        error = result.error if result else "no result"
        path = placeholder.write_placeholder_file(
            rag_dir,
            video_id=video.video_id,
            title=video.title,
            channel=video.channel_title,
            published=_published_str(video),
            error=error,
        )
        video.transcript_status = "placeholder"
        video.transcript_source = "placeholder"
        video.transcript_path = str(path)
        item.status = "done"
        item.error_message = error

    if config.download.download_audio:
        from ytfeed.metadata import ytdlp_client

        audio_path = ytdlp_client.download_audio(
            video.video_id, Path(config.paths.audio_output_dir)
        )
        if audio_path:
            video.audio_status = "done"
            video.audio_path = str(audio_path)
        else:
            video.audio_status = "failed"

    item.completed_at = _now()
    session.commit()


def _process_batch(
    session: Session,
    config: Config,
    batch_items: list[TranscriptionQueueItem],
    videos: dict[str, Video],
) -> dict[str, TranscriptResult]:
    """Run all three tiers for one batch of queue items and commit results."""
    # mark just this batch as processing so the queue page reflects reality
    for item in batch_items:
        item.status = "processing"
        item.started_at = _now()
        item.attempt_count += 1
        videos[item.video_id].transcript_status = "in_progress"
    session.commit()

    refs = [
        VideoRef(
            video_id=item.video_id,
            title=videos[item.video_id].title,
            channel_title=videos[item.video_id].channel_title,
        )
        for item in batch_items
    ]
    results: dict[str, TranscriptResult] = {}

    # tier 1: NotebookLM (one throwaway notebook for this batch)
    if config.notebooklm.enabled and refs:
        from ytfeed.transcripts import notebooklm_provider

        try:
            results = asyncio.run(
                notebooklm_provider.transcribe_batch(
                    refs,
                    batch_size=config.notebooklm.batch_size,
                    profile=config.notebooklm.profile,
                    delete_after=config.notebooklm.delete_notebook_after_extract,
                )
            )
        except Exception as exc:
            logger.warning("NotebookLM tier failed wholesale: %s — falling to tier 2", exc)
            results = {}

    # tier 2: youtube-transcript-api for anything still missing
    for ref in refs:
        prior = results.get(ref.video_id)
        if prior is not None and prior.success:
            continue
        tier1_error = prior.error if prior else None
        result = youtube_api_provider.fetch(ref.video_id)
        if not result.success and tier1_error:
            result.error = f"notebooklm: {tier1_error}; youtube_api: {result.error}"
        results[ref.video_id] = result

    # tier 3 fallback + file writing + DB updates, committed per video
    for item in batch_items:
        _finalize_item(session, config, item, videos[item.video_id], results.get(item.video_id))

    return results


def run_transcription_pipeline(
    session: Session,
    config: Config,
    *,
    video_ids: list[str] | None = None,
    limit: int | None = None,
) -> dict[str, TranscriptResult]:
    """Process pending queue items in batches. Returns per-video results."""
    items = _select_queue_items(session, video_ids, limit)
    if not items:
        return {}

    videos: dict[str, Video] = {}
    workable: list[TranscriptionQueueItem] = []
    for item in items:
        video = session.scalar(select(Video).where(Video.video_id == item.video_id))
        if video is None:
            item.status = "failed"
            item.error_message = "video not in DB"
            continue
        videos[item.video_id] = video
        workable.append(item)
    session.commit()

    batch_size = max(1, config.notebooklm.batch_size)
    results: dict[str, TranscriptResult] = {}
    total_batches = (len(workable) + batch_size - 1) // batch_size
    for i in range(0, len(workable), batch_size):
        batch = workable[i : i + batch_size]
        logger.info(
            "transcription batch %d/%d (%d videos)",
            i // batch_size + 1,
            total_batches,
            len(batch),
        )
        results.update(_process_batch(session, config, batch, videos))

    return results
