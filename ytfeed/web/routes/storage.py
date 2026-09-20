"""Storage stats: how much disk ytfeed uses locally."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ytfeed.config import PROJECT_ROOT
from ytfeed.db.models import Video
from ytfeed.web.dependencies import get_config, get_db, templates

router = APIRouter()


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:,.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:,.1f} TB"


def _file_sizes(paths: list[str | None]) -> tuple[int, int, int]:
    """(count_existing, total_bytes, count_missing) for a list of file paths."""
    count = total = missing = 0
    for p in paths:
        if not p:
            continue
        try:
            total += os.path.getsize(p)
            count += 1
        except OSError:
            missing += 1
    return count, total, missing


def _dir_size(path: Path) -> tuple[int, int]:
    """(file_count, total_bytes) for a directory tree; (0, 0) if absent."""
    count = total = 0
    if not path.is_dir():
        return 0, 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
                count += 1
            except OSError:
                pass
    return count, total


@router.get("/storage", response_class=HTMLResponse)
def storage_page(request: Request, db: Session = Depends(get_db)):
    config = get_config()

    db_path = Path(config.paths.db_path)
    db_bytes = 0
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(db_path) + suffix)
        if candidate.exists():
            db_bytes += candidate.stat().st_size

    transcript_paths = list(
        db.scalars(select(Video.transcript_path).where(Video.transcript_status == "done"))
    )
    t_count, t_bytes, t_missing = _file_sizes(transcript_paths)

    placeholder_paths = list(
        db.scalars(
            select(Video.transcript_path).where(Video.transcript_status == "placeholder")
        )
    )
    p_count, p_bytes, p_missing = _file_sizes(placeholder_paths)

    a_count, a_bytes = _dir_size(Path(config.paths.audio_output_dir))
    env_count, env_bytes = _dir_size(PROJECT_ROOT / ".venv")

    rows = [
        {
            "label": "Database",
            "detail": f"{db_path.name} (+ WAL/SHM)",
            "count": None,
            "bytes": db_bytes,
        },
        {
            "label": "Transcripts in vault",
            "detail": str(config.paths.rag_output_dir or "(not set)"),
            "count": t_count,
            "bytes": t_bytes,
        },
        {
            "label": "Placeholder files in vault",
            "detail": "re-queueable failures",
            "count": p_count,
            "bytes": p_bytes,
        },
        {
            "label": "Audio downloads",
            "detail": str(config.paths.audio_output_dir),
            "count": a_count,
            "bytes": a_bytes,
        },
        {
            "label": "App environment",
            "detail": ".venv (recreatable via pip install)",
            "count": env_count,
            "bytes": env_bytes,
        },
    ]
    for row in rows:
        row["size"] = human_size(row["bytes"])

    data_total = db_bytes + t_bytes + p_bytes + a_bytes
    missing = t_missing + p_missing

    return templates.TemplateResponse(
        request,
        "storage.html",
        {
            "request": request,
            "active_page": "storage",
            "rows": rows,
            "data_total": human_size(data_total),
            "grand_total": human_size(data_total + env_bytes),
            "missing": missing,
        },
    )
