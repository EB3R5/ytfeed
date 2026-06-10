import tempfile
import unittest
from pathlib import Path

from ytfeed.transcripts.markdown_writer import (
    build_filename,
    sanitize_filename,
    write_transcript_file,
)
from ytfeed.transcripts.placeholder import write_placeholder_file


class SanitizeTests(unittest.TestCase):
    def test_strips_path_separators(self):
        self.assertNotIn("/", sanitize_filename("a/b\\c:d"))

    def test_collapses_whitespace_and_trailing_dot(self):
        self.assertEqual(sanitize_filename("  a   b. "), "a b")

    def test_placeholder_suffix(self):
        self.assertEqual(
            build_filename("T", "C", placeholder=True), "T - C (PLACEHOLDER).md"
        )


class WriterTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_transcript_file_is_frontmatter_title_and_transcript_only(self):
        path = write_transcript_file(
            self.dir,
            video_id="abc123",
            title="My Video",
            channel="My Channel",
            published="2026-01-01T00:00:00Z",
            transcript="hello world",
            source="youtube_api",
        )
        text = path.read_text()
        self.assertTrue(text.startswith("---\nvideo_id: abc123"))
        self.assertIn("# My Video", text)
        self.assertIn("hello world", text)
        # metadata/description live in the DB, not the vault file
        self.assertNotIn("## Description", text)
        self.assertNotIn("**Channel**", text)
        self.assertEqual(path.name, "My Video - My Channel.md")

    def test_success_removes_placeholder(self):
        ph = write_placeholder_file(
            self.dir,
            video_id="abc123",
            title="My Video",
            channel="My Channel",
            published=None,
            error="TranscriptsDisabled",
        )
        self.assertTrue(ph.exists())
        self.assertIn("(TRANSCRIPTION UNAVAILABLE)", ph.read_text())
        write_transcript_file(
            self.dir,
            video_id="abc123",
            title="My Video",
            channel="My Channel",
            published=None,
            transcript="later success",
            source="notebooklm",
        )
        self.assertFalse(ph.exists())


if __name__ == "__main__":
    unittest.main()
