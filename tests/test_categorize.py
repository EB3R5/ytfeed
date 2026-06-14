import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ytfeed.db.models import Base, Playlist, PlaylistItem
from ytfeed.transcripts.categorize import category_for_video


def _playlist(session, playlist_id, title, video_ids, added_at=None):
    session.add(Playlist(playlist_id=playlist_id, title=title))
    for vid in video_ids:
        session.add(
            PlaylistItem(playlist_id=playlist_id, video_id=vid, added_at=added_at)
        )


class CategorizeTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        self.session = Session(engine)

    def test_no_playlist_means_no_category(self):
        self.assertIsNone(category_for_video(self.session, "v1"))

    def test_single_playlist_wins(self):
        _playlist(self.session, "p1", "Cooking", ["v1", "v2"])
        self.session.commit()
        self.assertEqual(category_for_video(self.session, "v1"), "Cooking")

    def test_most_recent_add_wins(self):
        # filed into a tiny playlist first, then deliberately into Cooking
        # seconds later — the latest filing decision is the category
        _playlist(
            self.session, "p1", "Cocktail", ["v1"], added_at=datetime(2026, 5, 17, 0, 49, 45)
        )
        _playlist(
            self.session,
            "p2",
            "Cooking",
            ["v1", "v2", "v3"],
            added_at=datetime(2026, 5, 17, 0, 49, 51),
        )
        self.session.commit()
        self.assertEqual(category_for_video(self.session, "v1"), "Cooking")

    def test_smallest_playlist_wins_without_timestamps(self):
        _playlist(self.session, "p1", "Movies", ["v1", "v2", "v3"])
        _playlist(self.session, "p2", "Directing", ["v1"])
        self.session.commit()
        self.assertEqual(category_for_video(self.session, "v1"), "Directing")

    def test_timestamped_membership_beats_untimestamped(self):
        _playlist(self.session, "p1", "Tiny", ["v1"])
        _playlist(
            self.session,
            "p2",
            "Cooking",
            ["v1", "v2"],
            added_at=datetime(2026, 1, 1),
        )
        self.session.commit()
        self.assertEqual(category_for_video(self.session, "v1"), "Cooking")

    def test_duplicate_playlist_names_merge(self):
        # two playlists both named "Work" count as one category
        _playlist(self.session, "p1", "Work", ["v1"])
        _playlist(self.session, "p2", "Work", ["v2"])
        _playlist(self.session, "p3", "Tiny", ["v1"])
        self.session.commit()
        # Work totals 2 members, Tiny has 1 -> Tiny is more specific
        self.assertEqual(category_for_video(self.session, "v1"), "Tiny")

    def test_category_is_filesystem_safe(self):
        _playlist(self.session, "p1", "AC/DC: Live", ["v1"])
        self.session.commit()
        category = category_for_video(self.session, "v1")
        self.assertNotIn("/", category)
        self.assertNotIn(":", category)


if __name__ == "__main__":
    unittest.main()
