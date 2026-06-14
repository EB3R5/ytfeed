"""Tier 3: placeholder stub files matching the existing RAG/raw convention."""

from __future__ import annotations

from pathlib import Path

from ytfeed.transcripts.markdown_writer import _frontmatter, build_filename


def write_placeholder_file(
    output_dir: Path,
    *,
    video_id: str,
    title: str,
    channel: str,
    published: str | None,
    error: str | None = None,
    category: str | None = None,
    description: str | None = None,
) -> Path:
    url = f"https://www.youtube.com/watch?v={video_id}"
    path = Path(output_dir) / build_filename(title, channel, placeholder=True)
    parts = [
        _frontmatter(
            video_id=video_id,
            channel=channel,
            published=published,
            url=url,
            source="placeholder",
            category=category,
        ),
        f"# {title} (TRANSCRIPTION UNAVAILABLE)",
        "",
    ]
    if description and description.strip():
        parts += ["## Description", "", description.strip(), ""]
    parts += [
        "## Transcription Status",
        "",
        "Automatic transcription failed for this video.",
        "",
        f"- **Error**: {error or 'unknown'}",
        "- NotebookLM and the YouTube caption API both came up empty.",
        "",
        "To fill this in manually: open the video URL above, add it to a NotebookLM",
        "notebook (or download audio and transcribe), then replace this file with the",
        "transcript, dropping the (PLACEHOLDER) filename suffix.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")
    return path
