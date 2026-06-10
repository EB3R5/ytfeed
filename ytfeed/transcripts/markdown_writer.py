"""Write transcript markdown files into the Obsidian RAG vault."""

from __future__ import annotations

import re
from pathlib import Path


def sanitize_filename(name: str) -> str:
    # forbid path separators and characters that break macOS/Obsidian filenames
    name = re.sub(r'[/\\:*?"<>|]', "_", name)
    name = re.sub(r"\s+", " ", name).strip().rstrip(".")
    return name[:180] or "untitled"


def build_filename(title: str, channel: str, *, placeholder: bool = False) -> str:
    base = sanitize_filename(f"{title} - {channel}")
    suffix = " (PLACEHOLDER)" if placeholder else ""
    return f"{base}{suffix}.md"


def _yaml_escape(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _frontmatter(
    *, video_id: str, channel: str, published: str | None, url: str, source: str
) -> str:
    lines = [
        "---",
        f"video_id: {video_id}",
        f"channel: {_yaml_escape(channel)}",
        f"published: {published or ''}",
        f"url: {url}",
        f"source: {source}",
        "tags: []",
        "---",
        "",
    ]
    return "\n".join(lines)


def write_transcript_file(
    output_dir: Path,
    *,
    video_id: str,
    title: str,
    channel: str,
    published: str | None,
    transcript: str,
    source: str,
    description: str | None = None,
) -> Path:
    url = f"https://www.youtube.com/watch?v={video_id}"
    path = Path(output_dir) / build_filename(title, channel)
    parts = [
        _frontmatter(
            video_id=video_id, channel=channel, published=published, url=url, source=source
        ),
        f"# {title}",
        "",
        f"**Channel**: {channel}",
        f"**Published**: {published or 'unknown'}",
        f"**Video ID**: {video_id}",
        "",
        f"**Video URL**: {url}",
        "",
    ]
    if description:
        parts += ["## Description", "", description.strip(), ""]
    parts += ["## Transcript", "", transcript.strip(), ""]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")

    # a successful transcript supersedes any earlier placeholder file
    placeholder_path = Path(output_dir) / build_filename(title, channel, placeholder=True)
    if placeholder_path.exists():
        placeholder_path.unlink()

    return path
