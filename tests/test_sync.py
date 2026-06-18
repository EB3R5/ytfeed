import unittest
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from ytfeed.db.models import Base, Channel, ChannelUpload, Video
from ytfeed.youtube.client import GoogleYouTubeSource, YouTubeSource
from ytfeed.youtube.sync import sync_channel_uploads


def _item(video_id: str, published: str) -> dict:
    return {
        "contentDetails": {"videoId": video_id, "videoPublishedAt": published},
        "snippet": {"title": f"title {video_id}", "channelTitle": "Chan"},
    }


class FakeSource:
    """A canned YouTubeSource — no network, no google client to fake."""

    def __init__(self, pages: dict[str, list[list[dict]]]) -> None:
        self._pages = pages
        self._api_calls = 0

    @property
    def api_calls(self) -> int:
        return self._api_calls

    def fetch_subscriptions(self) -> Iterator[dict]:
        yield from ()

    def fetch_my_playlists(self) -> Iterator[dict]:
        yield from ()

    def fetch_playlist_items_paged(self, playlist_id: str) -> Iterator[list[dict]]:
        for page in self._pages.get(playlist_id, []):
            self._api_calls += 1
            yield page

    def fetch_playlists_by_ids(self, playlist_ids: list[str]) -> list[dict]:
        return []

    def fetch_channels_content_details(self, channel_ids: list[str]) -> dict[str, str]:
        return {}


class ChannelUploadsTests(unittest.TestCase):
    def setUp(self):
        # FakeSource satisfies the protocol the sync engine depends on
        self.assertIsInstance(FakeSource({}), YouTubeSource)
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        self.session = Session(engine)

    def _channel(self, **kwargs) -> Channel:
        ch = Channel(channel_id="C1", title="Chan", uploads_playlist_id="UP", **kwargs)
        self.session.add(ch)
        self.session.commit()
        return ch

    def test_early_stop_on_known_video(self):
        ch = self._channel()
        # v_old is already recorded for this channel
        self.session.add(Video(video_id="v_old"))
        self.session.add(ChannelUpload(channel_id="C1", video_id="v_old"))
        self.session.commit()
        source = FakeSource(
            {
                "UP": [
                    [
                        _item("v3", "2026-01-03T00:00:00Z"),
                        _item("v2", "2026-01-02T00:00:00Z"),
                        _item("v_old", "2026-01-01T00:00:00Z"),
                    ]
                ]
            }
        )
        new = sync_channel_uploads(self.session, source, ch, initial_backfill=50)
        # stops at the already-known v_old; only v3 and v2 are new
        self.assertEqual(new, 2)
        ids = set(self.session.scalars(select(ChannelUpload.video_id)))
        self.assertEqual(ids, {"v_old", "v3", "v2"})

    def test_first_sync_respects_backfill_cap(self):
        ch = self._channel()
        source = FakeSource(
            {
                "UP": [
                    [_item(f"v{n}", f"2026-01-0{n}T00:00:00Z") for n in (5, 4, 3, 2, 1)]
                ]
            }
        )
        new = sync_channel_uploads(self.session, source, ch, initial_backfill=2)
        self.assertEqual(new, 2)

    def test_early_stop_on_published_older_than_last_seen(self):
        ch = self._channel(last_video_published_at=datetime(2026, 1, 2))
        source = FakeSource(
            {
                "UP": [
                    [
                        _item("v_new", "2026-01-03T00:00:00Z"),
                        _item("v_eq", "2026-01-02T00:00:00Z"),  # <= last seen -> stop
                        _item("v_older", "2026-01-01T00:00:00Z"),
                    ]
                ]
            }
        )
        new = sync_channel_uploads(self.session, source, ch, initial_backfill=50)
        self.assertEqual(new, 1)
        self.assertEqual(ch.last_video_published_at, datetime(2026, 1, 3))


class _FakeRequest:
    def __init__(self, response: dict) -> None:
        self._response = response

    def execute(self) -> dict:
        return self._response


class _FakeListEndpoint:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = responses
        self._i = 0

    def list(self, **kwargs: Any) -> _FakeRequest:
        resp = self._responses[min(self._i, len(self._responses) - 1)]
        self._i += 1
        return _FakeRequest(resp)


class _FakeYouTube:
    def __init__(self, responses: list[dict]) -> None:
        self._endpoint = _FakeListEndpoint(responses)

    def playlistItems(self) -> _FakeListEndpoint:
        return self._endpoint


class PaginationGuardTests(unittest.TestCase):
    def test_endless_token_loop_stops_and_counts_calls(self):
        # YouTube's deleted-video bug: same nextPageToken forever. The guard
        # must stop instead of burning quota indefinitely.
        responses = [{"items": [], "nextPageToken": "STUCK"}] * 10
        source = GoogleYouTubeSource(_FakeYouTube(responses))
        pages = list(source.fetch_playlist_items_paged("UP"))
        # token "STUCK" is seen on the 2nd page -> walk stops there
        self.assertEqual(len(pages), 2)
        self.assertEqual(source.api_calls, 2)


if __name__ == "__main__":
    unittest.main()
