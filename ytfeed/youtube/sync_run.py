"""The audited sync-run lifecycle, owned in one place.

A sync run records its own progress, log, API-unit spend, and terminal state
(done / cancelled / quota / error) in a SyncRun row. ``audited_run`` opens the
row, hands the body a ``RunReporter`` to call, and on exit writes the right
terminal state — so the orchestrators in sync.py shrink to just the work
between open and close.

Callers with no run to audit (the CLI) pass ``NULL_REPORTER``: same surface,
no DB writes, no cancellation.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.orm import Session

from ytfeed.db.models import SyncRun, utcnow
from ytfeed.youtube.client import YouTubeSource

logger = logging.getLogger(__name__)

# keep the run log bounded; trimmed from the oldest lines
_LOG_MAX_CHARS = 200_000

_QUOTA_MESSAGE = (
    "YouTube API daily quota exceeded — resets at midnight Pacific. "
    "Progress is saved; run sync again tomorrow."
)


class SyncCancelled(Exception):
    """Raised inside the sync worker when the user pressed Stop."""


def _is_quota_error(exc: Exception) -> bool:
    return "quotaExceeded" in str(exc)


class Reporter:
    """No-op progress surface, safe when there is no SyncRun to audit."""

    def progress(self, phase: str, current: int = 0, total: int = 0, detail: str = "") -> None:
        ...

    def log(self, message: str) -> None:
        ...


# the CLI and tests use this when they don't want an audited run
NULL_REPORTER = Reporter()


class RunReporter(Reporter):
    """Writes progress/log/quota-accounting into one SyncRun row.

    The API-unit baseline and log-repeat state live here as instance fields —
    they used to be stashed as private attributes on the ORM row, an invisible
    interface every caller had to set up in the right order.
    """

    def __init__(
        self, session: Session, run: SyncRun, source: YouTubeSource | None = None
    ) -> None:
        self._session = session
        self._run = run
        self._source = source
        self._api_calls_at_start = source.api_calls if source else 0
        self._last_log_msg: str | None = None
        self._log_repeats = 1

    @property
    def run(self) -> SyncRun:
        return self._run

    def progress(self, phase: str, current: int = 0, total: int = 0, detail: str = "") -> None:
        # the stop button writes via another session, so read the flag fresh
        if self._session.scalar(
            select(SyncRun.cancel_requested).where(SyncRun.id == self._run.id)
        ):
            raise SyncCancelled
        run = self._run
        run.phase = phase
        run.progress_current = current
        run.progress_total = total
        run.progress_detail = detail[:255]
        self._sync_api_calls()
        counter = f" {current}/{total}" if total else ""
        self._append(f"[{phase}{counter}] {detail}")
        self._session.commit()

    def log(self, message: str) -> None:
        self._append(message)
        self._session.commit()

    # --- internals, also used by audited_run for terminal lines ---

    def _sync_api_calls(self) -> None:
        if self._source is not None:
            self._run.api_calls = self._source.api_calls - self._api_calls_at_start

    def _append(self, message: str) -> None:
        log = self._run.log or ""
        stamp = utcnow().strftime("%H:%M:%S")
        if message == self._last_log_msg:
            # collapse repeats into one escalating "(xN)" line — a fast-climbing
            # counter is the signature of a retry/pagination loop
            self._log_repeats += 1
            head, _, _ = log.rstrip("\n").rpartition("\n")
            log = (head + "\n" if head else "") + f"{stamp} {message} (x{self._log_repeats})\n"
        else:
            self._last_log_msg = message
            self._log_repeats = 1
            log += f"{stamp} {message}\n"
        if len(log) > _LOG_MAX_CHARS:
            log = log[len(log) - _LOG_MAX_CHARS :]
            log = log[log.find("\n") + 1 :]
        self._run.log = log


@contextmanager
def audited_run(
    session: Session, kind: str, source: YouTubeSource | None = None
) -> Iterator[RunReporter]:
    """Open a SyncRun, yield its reporter, and write the terminal state on exit.

    SyncCancelled is swallowed (the run is recorded as cancelled); any other
    exception is recorded — with quota wording when it's a quota error — and
    re-raised. The body just does the work and updates run.channels_synced /
    run.videos_upserted. When a ``source`` is given, the run records the quota
    units it spent.
    """
    run = SyncRun(kind=kind)
    reporter = RunReporter(session, run, source)
    session.add(run)
    session.commit()

    def _finish() -> None:
        run.finished_at = utcnow().replace(tzinfo=None)
        session.commit()

    try:
        yield reporter
    except SyncCancelled:
        session.rollback()
        run.phase = "cancelled"
        run.error_message = "stopped by user"
        reporter._sync_api_calls()
        reporter._append("stopped by user — progress so far is saved")
        _finish()
    except Exception as exc:
        session.rollback()
        run.error_message = _QUOTA_MESSAGE if _is_quota_error(exc) else str(exc)
        reporter._sync_api_calls()
        reporter._append(f"FAILED: {run.error_message}")
        _finish()
        raise
    else:
        run.phase = "done"
        reporter._sync_api_calls()
        reporter._append(
            f"done — {run.channels_synced} channels, {run.videos_upserted} videos"
            f" upserted, ~{run.api_calls} API units"
        )
        _finish()
