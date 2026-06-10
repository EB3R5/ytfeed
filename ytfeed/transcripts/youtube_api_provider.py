"""Tier 2: caption transcripts via youtube-transcript-api (v1.x API)."""

from __future__ import annotations

import logging

from youtube_transcript_api import (
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)

from ytfeed.transcripts.base import TranscriptResult

logger = logging.getLogger(__name__)


def fetch(video_id: str) -> TranscriptResult:
    try:
        fetched = YouTubeTranscriptApi().fetch(video_id)
        text = "\n".join(snippet.text for snippet in fetched if snippet.text)
        if not text.strip():
            return TranscriptResult(video_id, False, error="Empty transcript returned")
        return TranscriptResult(video_id, True, text=text, source="youtube_api")
    except (IpBlocked, RequestBlocked) as exc:
        # transient: YouTube rate-limited this IP — caller should retry later
        logger.warning("YouTube blocked transcript request for %s (rate limit)", video_id)
        return TranscriptResult(
            video_id, False, error=type(exc).__name__, retryable=True
        )
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as exc:
        return TranscriptResult(video_id, False, error=type(exc).__name__)
    except Exception as exc:  # network or parsing failures shouldn't kill the batch
        logger.warning("youtube_api transcript failed for %s: %s", video_id, exc)
        return TranscriptResult(video_id, False, error=f"{type(exc).__name__}: {exc}")
