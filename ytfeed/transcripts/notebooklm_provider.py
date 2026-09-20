"""Tier 1: batch transcript extraction via NotebookLM.

Creates throwaway ytfeed-batch-* notebooks (50 sources each on free tier),
pulls each source's fulltext (the YouTube caption transcript), then deletes
the notebook so the free-tier notebook quota is never accumulated against.
Never touches the user's pre-existing notebooks.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from notebooklm import (
    NotebookLimitError,
    NotebookLMClient,
    RateLimitError,
    SourceAddError,
    SourceNotFoundError,
    SourceTimeoutError,
)

from ytfeed.transcripts.base import TranscriptResult, VideoRef

logger = logging.getLogger(__name__)

PER_VIDEO_ERRORS = (
    SourceAddError,
    SourceTimeoutError,
    RateLimitError,
    SourceNotFoundError,
)


async def _process_chunk(
    client: NotebookLMClient,
    chunk: list[VideoRef],
    *,
    delete_after: bool,
) -> dict[str, TranscriptResult]:
    results: dict[str, TranscriptResult] = {}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    try:
        notebook = await client.notebooks.create(title=f"ytfeed-batch-{stamp}")
    except (NotebookLimitError, RateLimitError) as exc:
        for video in chunk:
            results[video.video_id] = TranscriptResult(
                video.video_id, False, error=f"{type(exc).__name__}: {exc}"
            )
        return results

    source_map: dict[str, str] = {}  # source_id -> video_id
    try:
        for video in chunk:
            try:
                source = await client.sources.add_url(notebook.id, video.url, wait=False)
                source_map[source.id] = video.video_id
            except PER_VIDEO_ERRORS as exc:
                results[video.video_id] = TranscriptResult(
                    video.video_id, False, error=f"{type(exc).__name__}: {exc}"
                )

        if source_map:
            try:
                await client.sources.wait_for_sources(notebook.id, list(source_map))
            except PER_VIDEO_ERRORS as exc:
                logger.warning("wait_for_sources failed for batch: %s", exc)

        for source_id, video_id in source_map.items():
            try:
                fulltext = await client.sources.get_fulltext(
                    notebook.id, source_id, output_format="text"
                )
                text = (fulltext.content or "").strip()
                if text:
                    results[video_id] = TranscriptResult(
                        video_id, True, text=text, source="notebooklm"
                    )
                else:
                    results[video_id] = TranscriptResult(
                        video_id, False, error="NotebookLM returned empty fulltext"
                    )
            except PER_VIDEO_ERRORS as exc:
                results[video_id] = TranscriptResult(
                    video_id, False, error=f"{type(exc).__name__}: {exc}"
                )
    finally:
        # delete even on partial failure — failed videos fall to tier 2 anyway
        if delete_after:
            try:
                await client.notebooks.delete(notebook.id)
            except Exception as exc:
                logger.warning("could not delete notebook %s: %s", notebook.id, exc)

    return results


async def transcribe_batch(
    videos: list[VideoRef],
    *,
    batch_size: int = 50,
    profile: str = "default",
    delete_after: bool = True,
) -> dict[str, TranscriptResult]:
    """Transcribe videos in chunks of batch_size, one throwaway notebook per chunk."""
    results: dict[str, TranscriptResult] = {}
    if not videos:
        return results

    async with NotebookLMClient.from_storage(profile=profile) as client:
        for i in range(0, len(videos), batch_size):
            chunk = videos[i : i + batch_size]
            logger.info(
                "NotebookLM batch %d-%d of %d", i + 1, i + len(chunk), len(videos)
            )
            results.update(
                await _process_chunk(client, chunk, delete_after=delete_after)
            )
    return results
