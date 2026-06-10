"""yt-dlp helpers: metadata enrichment and optional audio download."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

logger = logging.getLogger(__name__)


def fetch_video_metadata(video_id: str) -> dict[str, Any] | None:
    url = f"https://www.youtube.com/watch?v={video_id}"
    opts = {"quiet": True, "skip_download": True, "no_warnings": True}
    try:
        with YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)
    except DownloadError as exc:
        logger.warning("yt-dlp metadata failed for %s: %s", video_id, exc)
        return None


def download_audio(video_id: str, output_dir: Path) -> Path | None:
    """Download audio as mp3 (requires ffmpeg). Returns the file path or None."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
    except DownloadError as exc:
        logger.warning("yt-dlp audio download failed for %s: %s", video_id, exc)
        return None
    path = output_dir / f"{video_id}.mp3"
    return path if path.exists() else None
