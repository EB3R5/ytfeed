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
    *,
    video_id: str,
    channel: str,
    published: str | None,
    url: str,
    source: str,
    category: str | None = None,
) -> str:
    lines = [
        "---",
        f"video_id: {video_id}",
        f"channel: {_yaml_escape(channel)}",
        f"published: {published or ''}",
        f"url: {url}",
        f"source: {source}",
    ]
    if category:
        lines.append(f"category: {_yaml_escape(category)}")
    lines += ["tags: []", "---", ""]
    return "\n".join(lines)


def ensure_description_section(path: Path, description: str | None) -> bool:
    """Insert a ## Description section after the title of an existing vault
    file that predates description writing. When the rest of the body is bare
    transcript text it also gains a ## Transcript heading; bodies that already
    start with their own section (placeholder stubs) are left as-is below the
    description. Returns True if the file changed."""
    if not description or not description.strip():
        return False
    text = path.read_text(encoding="utf-8")
    if "\n## Description\n" in text:
        return False
    title_match = re.search(r"^# .+$", text, re.MULTILINE)
    if title_match is None:
        return False
    head = text[: title_match.end()]
    body = text[title_match.end() :].lstrip("\n")
    section = f"\n\n## Description\n\n{description.strip()}\n\n"
    if not body.startswith("## "):
        section += "## Transcript\n\n"
    path.write_text(head + section + body, encoding="utf-8")
    return True


def write_transcript_file(
    output_dir: Path,
    *,
    video_id: str,
    title: str,
    channel: str,
    published: str | None,
    transcript: str,
    source: str,
    category: str | None = None,
    description: str | None = None,
) -> Path:
    """Vault file: frontmatter identifies the video, the body is the
    description (recipes, links, chapter notes often live there) and the
    transcript. Sync/status metadata lives in the ytfeed DB, not the vault."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    path = Path(output_dir) / build_filename(title, channel)
    parts = [
        _frontmatter(
            video_id=video_id,
            channel=channel,
            published=published,
            url=url,
            source=source,
            category=category,
        ),
        f"# {title}",
        "",
    ]
    if description and description.strip():
        parts += ["## Description", "", description.strip(), "", "## Transcript", ""]
    parts += [transcript.strip(), ""]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")

    # a successful transcript supersedes any earlier placeholder file
    placeholder_path = Path(output_dir) / build_filename(title, channel, placeholder=True)
    if placeholder_path.exists():
        placeholder_path.unlink()

    return path
