"""YouTubeSource: the slice of the YouTube Data API the sync engine needs.

sync.py depends on the ``YouTubeSource`` protocol, not the raw googleapiclient
Resource — so the real adapter (``GoogleYouTubeSource``) and a fake adapter in
tests are interchangeable, and early-stop / backfill caps / the pagination-loop
guard become unit-testable without faking the google client several layers
deep. The per-run quota counter lives on the adapter instead of as
module-global state.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ytfeed.config import Config

logger = logging.getLogger(__name__)


@runtime_checkable
class YouTubeSource(Protocol):
    """The YouTube Data API operations the sync engine depends on."""

    @property
    def api_calls(self) -> int:
        """Lower-bound estimate of Data API quota units spent so far.

        Each list request costs >= 1 unit, so this under-counts real quota.
        """

    def fetch_subscriptions(self) -> Iterator[dict[str, Any]]:
        """Yield the user's subscription items across all pages."""

    def fetch_my_playlists(self) -> Iterator[dict[str, Any]]:
        """Yield the user's own playlists across all pages."""

    def fetch_playlist_items_paged(
        self, playlist_id: str
    ) -> Iterator[list[dict[str, Any]]]:
        """Yield playlistItems one PAGE at a time (sync needs page granularity
        for early-stop)."""

    def fetch_playlists_by_ids(
        self, playlist_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Fetch playlist resources by ID (works for any accessible playlist)."""

    def fetch_channels_content_details(
        self, channel_ids: list[str]
    ) -> dict[str, str]:
        """Resolve uploads-playlist IDs for channels, batched 50 per request."""


class GoogleYouTubeSource:
    """Real adapter: thin paginated wrappers over a googleapiclient Resource."""

    def __init__(self, youtube: Any) -> None:
        self._yt = youtube
        self._api_calls = 0

    @property
    def api_calls(self) -> int:
        return self._api_calls

    def _paginate(self, request_factory, **kwargs) -> Iterator[dict[str, Any]]:
        """Yield items across all pages of a list endpoint.

        request_factory is e.g. ``self._yt.subscriptions().list``; kwargs are
        passed through, with pageToken managed here.
        """
        page_token: str | None = None
        seen_tokens: set[str] = set()
        empty_pages = 0
        while True:
            params = dict(kwargs)
            if page_token:
                params["pageToken"] = page_token
            self._api_calls += 1
            response = request_factory(**params).execute()
            items = response.get("items", [])
            yield from items
            empty_pages = empty_pages + 1 if not items else 0
            page_token = response.get("nextPageToken")
            if not page_token:
                return
            # YouTube sometimes keeps returning a nextPageToken past the real
            # end (playlists with deleted videos) — without this guard the walk
            # loops forever and burns quota
            if page_token in seen_tokens or empty_pages >= 3:
                logger.warning("pagination loop detected; stopping walk early")
                return
            seen_tokens.add(page_token)

    def fetch_subscriptions(self) -> Iterator[dict[str, Any]]:
        return self._paginate(
            self._yt.subscriptions().list,
            part="snippet,contentDetails",
            mine=True,
            maxResults=50,
        )

    def fetch_my_playlists(self) -> Iterator[dict[str, Any]]:
        return self._paginate(
            self._yt.playlists().list,
            part="snippet,contentDetails",
            mine=True,
            maxResults=50,
        )

    def fetch_playlist_items_paged(
        self, playlist_id: str
    ) -> Iterator[list[dict[str, Any]]]:
        page_token: str | None = None
        seen_tokens: set[str] = set()
        empty_pages = 0
        while True:
            params: dict[str, Any] = {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": 50,
            }
            if page_token:
                params["pageToken"] = page_token
            self._api_calls += 1
            response = self._yt.playlistItems().list(**params).execute()
            items = response.get("items", [])
            yield items
            empty_pages = empty_pages + 1 if not items else 0
            page_token = response.get("nextPageToken")
            if not page_token:
                return
            # see _paginate(): guard against YouTube's endless-token bug
            if page_token in seen_tokens or empty_pages >= 3:
                logger.warning(
                    "playlist %s: pagination loop detected; stopping walk early",
                    playlist_id,
                )
                return
            seen_tokens.add(page_token)

    def fetch_playlists_by_ids(
        self, playlist_ids: list[str]
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for i in range(0, len(playlist_ids), 50):
            batch = playlist_ids[i : i + 50]
            self._api_calls += 1
            response = (
                self._yt.playlists()
                .list(part="snippet,contentDetails", id=",".join(batch), maxResults=50)
                .execute()
            )
            result.extend(response.get("items", []))
        return result

    def fetch_channels_content_details(
        self, channel_ids: list[str]
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        for i in range(0, len(channel_ids), 50):
            batch = channel_ids[i : i + 50]
            self._api_calls += 1
            response = (
                self._yt.channels()
                .list(part="contentDetails", id=",".join(batch), maxResults=50)
                .execute()
            )
            for item in response.get("items", []):
                uploads = (
                    item.get("contentDetails", {})
                    .get("relatedPlaylists", {})
                    .get("uploads")
                )
                if uploads:
                    result[item["id"]] = uploads
        return result


def build_source(config: Config) -> YouTubeSource:
    """Authenticate and wrap the YouTube Data API in a YouTubeSource."""
    from ytfeed.youtube.auth import get_youtube_client

    return GoogleYouTubeSource(get_youtube_client(config))
