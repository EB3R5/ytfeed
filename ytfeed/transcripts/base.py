"""Shared types for the transcript pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VideoRef:
    """Minimal video info the providers need."""

    video_id: str
    title: str = ""
    channel_title: str = ""

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


@dataclass
class TranscriptResult:
    video_id: str
    success: bool
    text: str | None = None
    source: str | None = None  # "notebooklm" | "youtube_api"
    error: str | None = None
