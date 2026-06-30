"""SQLAlchemy 2.0 models for ytfeed."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    uploads_playlist_id: Mapped[str | None] = mapped_column(String(64))
    subscribed_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_video_published_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=False)
    # channel-level taxonomy (independent of playlist-derived video category)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("channel_categories.id"), index=True
    )
    notes: Mapped[str] = mapped_column(Text, default="")


class ChannelCategory(Base):
    """Group -> Category -> Type taxonomy assigned to subscribed channels.

    Mirrors money-webapp's category model (Group=section, Category=item/name,
    Type=attribute); channels reference a row by FK rather than denormalizing.
    """

    __tablename__ = "channel_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)  # Category
    group: Mapped[str] = mapped_column(String(128), default="", index=True)  # Group
    type: Mapped[str | None] = mapped_column(String(128))  # Type


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    playlist_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    # YouTube's reported itemCount at the last full item walk; when the
    # current itemCount still matches, the walk is skipped (quota)
    synced_item_count: Mapped[int | None] = mapped_column(Integer)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    channel_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("channels.channel_id"), index=True
    )
    channel_title: Mapped[str] = mapped_column(String(255), default="")
    title: Mapped[str] = mapped_column(String(512), default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    published_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    tags: Mapped[str | None] = mapped_column(Text)  # JSON-encoded list
    source: Mapped[str] = mapped_column(String(32), default="sync")
    transcript_status: Mapped[str] = mapped_column(
        String(16), default="none", index=True
    )  # none|queued|in_progress|done|failed|placeholder
    transcript_source: Mapped[str | None] = mapped_column(String(16))  # notebooklm|youtube_api|placeholder
    transcript_path: Mapped[str | None] = mapped_column(String(512))
    audio_status: Mapped[str] = mapped_column(String(16), default="none")
    audio_path: Mapped[str | None] = mapped_column(String(512))
    notebooklm_notebook_id: Mapped[str | None] = mapped_column(String(64))

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


class PlaylistItem(Base):
    __tablename__ = "playlist_items"
    __table_args__ = (UniqueConstraint("playlist_id", "video_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    playlist_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("playlists.playlist_id"), index=True
    )
    video_id: Mapped[str] = mapped_column(String(32), ForeignKey("videos.video_id"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime | None] = mapped_column(DateTime)


class ChannelUpload(Base):
    __tablename__ = "channel_uploads"
    __table_args__ = (
        UniqueConstraint("channel_id", "video_id"),
        Index("ix_channel_uploads_channel_published", "channel_id", "published_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[str] = mapped_column(String(64), ForeignKey("channels.channel_id"))
    video_id: Mapped[str] = mapped_column(String(32), ForeignKey("videos.video_id"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime)


class TranscriptionQueueItem(Base):
    __tablename__ = "transcription_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[str] = mapped_column(String(32), ForeignKey("videos.video_id"), index=True)
    status: Mapped[str] = mapped_column(
        String(16), default="pending", index=True
    )  # pending|processing|done|failed|cancelled
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # deferred retry: pending items are not picked up before this time
    not_before: Mapped[datetime | None] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    kind: Mapped[str] = mapped_column(String(32), default="full")  # full|subscriptions|playlists|channel
    channels_synced: Mapped[int] = mapped_column(Integer, default=0)
    videos_upserted: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    # live progress, polled by the settings page
    phase: Mapped[str | None] = mapped_column(String(32))  # subscriptions|playlists|channels
    progress_current: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    progress_detail: Mapped[str | None] = mapped_column(String(255))
    api_calls: Mapped[int] = mapped_column(Integer, default=0)  # ≈ quota units spent
    # timestamped progress lines, viewable live and after the run
    log: Mapped[str] = mapped_column(Text, default="")
    # cooperative stop: set by the web UI, checked by the sync worker at each
    # progress update
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
