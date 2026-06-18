import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ytfeed.db.models import Base, SyncRun
from ytfeed.youtube.sync_run import (
    NULL_REPORTER,
    RunReporter,
    SyncCancelled,
    audited_run,
)


class ReporterTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        self.session = Session(engine)

    def _reporter(self) -> RunReporter:
        run = SyncRun(kind="full")
        self.session.add(run)
        self.session.commit()
        return RunReporter(self.session, run)

    def test_log_collapses_repeats(self):
        reporter = self._reporter()
        reporter.log("walking page")
        reporter.log("walking page")
        reporter.log("walking page")
        log = reporter.run.log
        # three identical lines collapse to one escalating "(x3)" line
        self.assertEqual(log.count("walking page"), 1)
        self.assertIn("walking page (x3)", log)

    def test_distinct_messages_each_get_a_line(self):
        reporter = self._reporter()
        reporter.log("first")
        reporter.log("second")
        self.assertIn("first", reporter.run.log)
        self.assertIn("second", reporter.run.log)

    def test_progress_raises_when_cancel_requested(self):
        reporter = self._reporter()
        # the stop button writes via another session; simulate that
        other = Session(self.session.get_bind())
        run = other.get(SyncRun, reporter.run.id)
        run.cancel_requested = True
        other.commit()
        other.close()
        with self.assertRaises(SyncCancelled):
            reporter.progress("channels", 1, 10, "Some Channel")

    def test_null_reporter_is_inert(self):
        # the CLI path: no SyncRun, no DB writes, never cancels
        NULL_REPORTER.progress("channels", 1, 1, "x")
        NULL_REPORTER.log("x")


class AuditedRunTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)
        self.session = self.Session()

    def test_success_marks_done(self):
        with audited_run(self.session, "full") as reporter:
            reporter.run.channels_synced = 3
            reporter.run.videos_upserted = 7
        run = reporter.run
        self.assertEqual(run.phase, "done")
        self.assertIsNotNone(run.finished_at)
        self.assertIsNone(run.error_message)
        self.assertIn("done — 3 channels, 7 videos", run.log)

    def test_cancel_is_swallowed_and_recorded(self):
        with audited_run(self.session, "full") as reporter:
            raise SyncCancelled
        run = reporter.run
        self.assertEqual(run.phase, "cancelled")
        self.assertEqual(run.error_message, "stopped by user")
        self.assertIsNotNone(run.finished_at)
        self.assertIn("stopped by user", run.log)

    def test_quota_error_gets_friendly_message_and_reraises(self):
        with self.assertRaises(RuntimeError):
            with audited_run(self.session, "full") as reporter:
                raise RuntimeError("the quotaExceeded limit was hit")
        run = reporter.run
        self.assertIn("daily quota exceeded", run.error_message)
        self.assertNotEqual(run.phase, "done")
        self.assertIsNotNone(run.finished_at)

    def test_other_error_records_raw_message_and_reraises(self):
        with self.assertRaises(ValueError):
            with audited_run(self.session, "channel") as reporter:
                raise ValueError("channel xyz not in database")
        run = reporter.run
        self.assertEqual(run.error_message, "channel xyz not in database")
        self.assertNotEqual(run.phase, "done")


if __name__ == "__main__":
    unittest.main()
