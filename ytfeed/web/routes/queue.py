"""Transcription queue: enqueue, view, run, retry."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ytfeed.db.models import TranscriptionQueueItem, Video, utcnow
from ytfeed.web.dependencies import get_config, get_db, templates

router = APIRouter()

# statuses that should not be re-queued
SKIP_VIDEO_STATUSES = {"done"}
PENDING_QUEUE_STATUSES = {"pending", "processing"}


@router.post("/queue")
def enqueue(
    request: Request,
    db: Session = Depends(get_db),
    video_ids: list[str] = Form(default=[]),
    next_url: str = Form(default="/queue"),
):
    queued, skipped = 0, 0
    for video_id in video_ids:
        video = db.scalar(select(Video).where(Video.video_id == video_id))
        if video is None:
            skipped += 1
            continue
        # skip videos already transcribed; failed/placeholder may re-enter
        if video.transcript_status in SKIP_VIDEO_STATUSES:
            skipped += 1
            continue
        already_pending = db.scalar(
            select(TranscriptionQueueItem).where(
                TranscriptionQueueItem.video_id == video_id,
                TranscriptionQueueItem.status.in_(PENDING_QUEUE_STATUSES),
            )
        )
        if already_pending is not None:
            skipped += 1
            continue
        db.add(TranscriptionQueueItem(video_id=video_id, status="pending"))
        video.transcript_status = "queued"
        queued += 1
    db.commit()
    return RedirectResponse(
        f"/queue?queued={queued}&skipped={skipped}", status_code=303
    )


@router.get("/queue", response_class=HTMLResponse)
def queue_view(
    request: Request,
    db: Session = Depends(get_db),
    queued: int | None = None,
    skipped: int | None = None,
):
    rows = db.execute(
        select(TranscriptionQueueItem, Video)
        .join(Video, Video.video_id == TranscriptionQueueItem.video_id)
        .where(TranscriptionQueueItem.is_hidden.is_(False))
        .order_by(TranscriptionQueueItem.requested_at.desc())
        .limit(200)
    ).all()
    pending_count = sum(1 for item, _ in rows if item.status == "pending")
    processing = any(item.status == "processing" for item, _ in rows)
    context = {
        "request": request,
        "active_page": "queue",
        "rows": rows,
        "pending_count": pending_count,
        "processing": processing,
        "queued": queued,
        "skipped": skipped,
    }
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/queue_table.html", context)
    return templates.TemplateResponse(request, "queue.html", context)


def _run_pipeline_bg() -> None:
    from ytfeed.db.session import get_session_factory
    from ytfeed.transcripts.pipeline import run_transcription_pipeline

    config = get_config()
    factory = get_session_factory(config)
    with factory() as session:
        run_transcription_pipeline(session, config)


@router.post("/queue/run")
def run_queue(request: Request, background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_pipeline_bg)
    return RedirectResponse("/queue", status_code=303)


@router.post("/queue/clear")
def clear_queue(request: Request, db: Session = Depends(get_db)):
    """Empty the queue page: cancel pending items, hide finished ones.

    Rows stay in the DB as history; items mid-processing are left visible.
    """
    items = list(
        db.scalars(
            select(TranscriptionQueueItem).where(
                TranscriptionQueueItem.is_hidden.is_(False)
            )
        )
    )
    for item in items:
        if item.status == "processing":
            continue
        if item.status == "pending":
            item.status = "cancelled"
            video = db.scalar(select(Video).where(Video.video_id == item.video_id))
            if video is not None and video.transcript_status == "queued":
                video.transcript_status = "none"
        item.is_hidden = True
    db.commit()
    return RedirectResponse("/queue", status_code=303)


@router.post("/queue/{item_id}/retry")
def retry_item(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(TranscriptionQueueItem, item_id)
    if item is not None and item.status == "failed":
        item.status = "pending"
        item.error_message = None
        item.requested_at = utcnow().replace(tzinfo=None)
        video = db.scalar(select(Video).where(Video.video_id == item.video_id))
        if video is not None and video.transcript_status != "done":
            video.transcript_status = "queued"
        db.commit()
    return RedirectResponse("/queue", status_code=303)
