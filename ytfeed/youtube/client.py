"""Thin paginated wrappers around the YouTube Data API."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from typing import Any

# per-process API request counter — each Data API request costs >= 1 quota
# unit, so this is a lower-bound estimate of quota burn
_counter_lock = threading.Lock()
_api_calls = 0


def count_call() -> None:
    global _api_calls
    with _counter_lock:
        _api_calls += 1


def get_api_calls() -> int:
    return _api_calls


def paginate(request_factory, **kwargs) -> Iterator[dict[str, Any]]:
    """Yield items across all pages of a list endpoint.

    request_factory is e.g. youtube.subscriptions().list; kwargs are passed
    through, with pageToken managed here.
    """
    page_token: str | None = None
    while True:
        params = dict(kwargs)
        if page_token:
            params["pageToken"] = page_token
        count_call()
        response = request_factory(**params).execute()
        yield from response.get("items", [])
        page_token = response.get("nextPageToken")
        if not page_token:
            return


def fetch_subscriptions(youtube) -> Iterator[dict[str, Any]]:
    return paginate(
        youtube.subscriptions().list,
        part="snippet,contentDetails",
        mine=True,
        maxResults=50,
    )


def fetch_my_playlists(youtube) -> Iterator[dict[str, Any]]:
    return paginate(
        youtube.playlists().list,
        part="snippet,contentDetails",
        mine=True,
        maxResults=50,
    )


def fetch_playlist_items_paged(youtube, playlist_id: str) -> Iterator[list[dict[str, Any]]]:
    """Yield playlistItems one PAGE at a time (sync needs page granularity for early-stop)."""
    page_token: str | None = None
    while True:
        params: dict[str, Any] = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,
        }
        if page_token:
            params["pageToken"] = page_token
        count_call()
        response = youtube.playlistItems().list(**params).execute()
        yield response.get("items", [])
        page_token = response.get("nextPageToken")
        if not page_token:
            return


def fetch_playlist_items(youtube, playlist_id: str) -> Iterator[dict[str, Any]]:
    for page in fetch_playlist_items_paged(youtube, playlist_id):
        yield from page


def fetch_playlists_by_ids(youtube, playlist_ids: list[str]) -> list[dict[str, Any]]:
    """Fetch playlist resources by ID (works for any accessible playlist)."""
    result: list[dict[str, Any]] = []
    for i in range(0, len(playlist_ids), 50):
        batch = playlist_ids[i : i + 50]
        count_call()
        response = (
            youtube.playlists()
            .list(part="snippet,contentDetails", id=",".join(batch), maxResults=50)
            .execute()
        )
        result.extend(response.get("items", []))
    return result


def fetch_channels_content_details(youtube, channel_ids: list[str]) -> dict[str, str]:
    """Resolve uploads playlist IDs for channels, batched 50 per request."""
    result: dict[str, str] = {}
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i : i + 50]
        count_call()
        response = (
            youtube.channels()
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
