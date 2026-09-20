import tempfile
import unittest
from pathlib import Path

from ytfeed.transcripts.markdown_writer import (
    build_filename,
    ensure_description_section,
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

    def test_transcript_file_without_description_has_no_empty_section(self):
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
        self.assertNotIn("## Description", text)
        self.assertNotIn("**Channel**", text)
        self.assertEqual(path.name, "My Video - My Channel.md")

    def test_description_lands_between_title_and_transcript(self):
        path = write_transcript_file(
            self.dir,
            video_id="abc123",
            title="My Video",
            channel="My Channel",
            published=None,
            transcript="hello world",
            source="youtube_api",
            description="Recipe: pound the chicken thin.",
        )
        text = path.read_text()
        self.assertIn("## Description", text)
        self.assertIn("Recipe: pound the chicken thin.", text)
        self.assertIn("## Transcript", text)
        self.assertLess(text.index("## Description"), text.index("Recipe:"))
        self.assertLess(text.index("Recipe:"), text.index("## Transcript"))
        self.assertLess(text.index("## Transcript"), text.index("hello world"))

    def test_category_goes_in_frontmatter_not_subfolder(self):
        path = write_transcript_file(
            self.dir,
            video_id="abc123",
            title="My Video",
            channel="My Channel",
            published=None,
            transcript="hello",
            source="youtube_api",
            category="Cooking",
        )
        # files stay flat in the vault root; category lives in frontmatter only
        self.assertEqual(path.parent, self.dir)
        self.assertIn('category: "Cooking"', path.read_text())

    def test_placeholder_category_goes_in_frontmatter_not_subfolder(self):
        ph = write_placeholder_file(
            self.dir,
            video_id="abc123",
            title="My Video",
            channel="My Channel",
            published=None,
            error="boom",
            category="Cooking",
        )
        self.assertEqual(ph.parent, self.dir)
        self.assertIn('category: "Cooking"', ph.read_text())

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


class EnsureDescriptionTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_backfills_old_transcript_file_with_transcript_heading(self):
        path = write_transcript_file(
            self.dir,
            video_id="abc123",
            title="My Video",
            channel="My Channel",
            published=None,
            transcript="hello world",
            source="youtube_api",
        )
        self.assertTrue(ensure_description_section(path, "The recipe."))
        text = path.read_text()
        self.assertIn("## Description\n\nThe recipe.", text)
        self.assertIn("## Transcript\n\nhello world", text)

    def test_placeholder_keeps_its_own_sections(self):
        path = write_placeholder_file(
            self.dir,
            video_id="abc123",
            title="My Video",
            channel="My Channel",
            published=None,
            error="boom",
        )
        self.assertTrue(ensure_description_section(path, "The recipe."))
        text = path.read_text()
        self.assertIn("## Description\n\nThe recipe.", text)
        # the status section follows directly; no bogus Transcript heading
        # ("## Transcription Status" is a substring trap — match the full line)
        self.assertNotIn("## Transcript\n", text)
        self.assertLess(text.index("## Description"), text.index("## Transcription Status"))

    def test_idempotent_and_skips_empty(self):
        path = write_transcript_file(
            self.dir,
            video_id="abc123",
            title="My Video",
            channel="My Channel",
            published=None,
            transcript="hello",
            source="youtube_api",
            description="Already here.",
        )
        self.assertFalse(ensure_description_section(path, "Already here."))
        self.assertFalse(ensure_description_section(path, "   "))
        self.assertFalse(ensure_description_section(path, None))


if __name__ == "__main__":
    unittest.main()
