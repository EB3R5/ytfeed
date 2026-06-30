# Graph Report - ytfeed  (2026-06-21)

## Corpus Check
- 44 files · ~64,438 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 647 nodes · 1951 edges · 30 communities
- Extraction: 75% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS · INFERRED: 488 edges (avg confidence: 0.61)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ee797511`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 31|Community 31]]

## God Nodes (most connected - your core abstractions)
1. `_()` - 104 edges
2. `Video` - 61 edges
3. `Channel` - 45 edges
4. `Config` - 40 edges
5. `YouTubeSource` - 36 edges
6. `oe()` - 34 edges
7. `He()` - 34 edges
8. `SyncRun` - 32 edges
9. `t()` - 32 edges
10. `ChannelUpload` - 31 edges

## Surprising Connections (you probably didn't know these)
- `CategorizeTests` --uses--> `Base`  [INFERRED]
  tests/test_categorize.py → ytfeed/db/models.py
- `CategorizeTests` --uses--> `Playlist`  [INFERRED]
  tests/test_categorize.py → ytfeed/db/models.py
- `CategorizeTests` --uses--> `PlaylistItem`  [INFERRED]
  tests/test_categorize.py → ytfeed/db/models.py
- `FakeSource` --uses--> `GoogleYouTubeSource`  [INFERRED]
  tests/test_sync.py → ytfeed/youtube/client.py
- `ChannelUploadsTests` --uses--> `GoogleYouTubeSource`  [INFERRED]
  tests/test_sync.py → ytfeed/youtube/client.py

## Import Cycles
- 1-file cycle: `ytfeed/youtube/sync.py -> ytfeed/youtube/sync.py`
- 1-file cycle: `ytfeed/db/models.py -> ytfeed/db/models.py`

## Communities (30 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (40): Channel, PlaylistItem, _run_sync_bg(), SyncRun, _append_log(), _best_thumbnail(), _parse_dt(), _progress() (+32 more)

### Community 1 - "Community 1"
Cohesion: 0.18
Nodes (11): Reset items stuck in 'processing' (e.g. after a server restart killed a run)., Reset items stuck in 'processing' (e.g. after a server restart killed a run)., Reset items stuck in 'processing' (e.g. after a server restart killed a run)., Reset items stuck in 'processing' (e.g. after a server restart killed a run)., Reset items stuck in 'processing' (e.g. after a server restart killed a run)., recover_stale_processing(), FastAPI app: Recents | Subscriptions | Playlists | Queue | Settings., Pick up deferred queue items (e.g. IP-block retries) once they're due. (+3 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (68): TranscriptionQueueItem, NotebookLMClient, clear_queue(), enqueue(), queue_view(), Transcription queue: enqueue, view, run, retry., Empty the queue page: cancel pending items, hide finished ones.      Rows stay i, retry_item() (+60 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (103): _(), A(), ae(), ar(), at(), B(), be(), br() (+95 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (38): InterviewAnalysis, CategorizeTests, _playlist(), EnsureCategoryTests, EnsureDescriptionTests, SanitizeTests, WriterTests, category_for_video() (+30 more)

### Community 5 - "Community 5"
Cohesion: 0.23
Nodes (12): get_engine(), get_session_factory(), init_db(), Engine/session factory and schema creation., Engine, _run_channel_sync(), build_source(), Authenticate and wrap the YouTube Data API in a YouTubeSource. (+4 more)

### Community 6 - "Community 6"
Cohesion: 0.19
Nodes (17): Namespace, ensure_people_frontmatter(), For files written before person tagging existed; empty lists remove a     stale, build_parser(), cmd_describe(), cmd_init_db(), cmd_people(), cmd_refile() (+9 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (17): Build Phasing & Verification, CLI (`ytfeed/cli.py`, argparse subparsers), Config & Secrets, Context, Database Schema (`ytfeed/db/models.py`, SQLAlchemy 2.0), Decisions already made, Decisions from design review (grill session, 2026-06-09), FastAPI Web App (`ytfeed/web/`) (+9 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (25): count_call(), fetch_channels_content_details(), fetch_my_playlists(), fetch_playlist_items(), fetch_playlist_items_paged(), fetch_playlists_by_ids(), fetch_subscriptions(), GoogleYouTubeSource (+17 more)

### Community 9 - "Community 9"
Cohesion: 0.39
Nodes (8): Recents page: newest videos from monitored (or one-off picked) channels., Picked channels override; otherwise monitored channels. Returns (ids, used_picke, _recent_videos(), recents(), _selected_channel_ids(), toggle_monitor(), Request, Session

### Community 10 - "Community 10"
Cohesion: 0.67
Nodes (3): SQLAlchemy 2.0 models for ytfeed., utcnow(), datetime

### Community 11 - "Community 11"
Cohesion: 0.17
Nodes (11): Engineering notes, Launching, Schema, Setup, Tests, Transcript pipeline (3 tiers), Usage, Vault file layout (+3 more)

### Community 12 - "Community 12"
Cohesion: 0.12
Nodes (11): sessionmaker, AuditedRunTests, ReporterTests, audited_run(), Open a SyncRun, yield its reporter, and write the terminal state on exit.      S, Open a SyncRun, yield its reporter, and write the terminal state on exit.      S, Writes progress/log/quota-accounting into one SyncRun row.      The API-unit bas, RunReporter (+3 more)

### Community 13 - "Community 13"
Cohesion: 0.29
Nodes (6): download_audio(), fetch_video_metadata(), yt-dlp helpers: metadata enrichment and optional audio download., Download audio as mp3 (requires ffmpeg). Returns the file path or None., Any, Path

### Community 14 - "Community 14"
Cohesion: 0.29
Nodes (6): DownloadConfig, NotebookLMConfig, PathsConfig, PeopleConfig, Load config.toml (falling back to config.example.toml) into a Config object., SyncConfig

### Community 23 - "Community 23"
Cohesion: 0.15
Nodes (17): _dir_size(), _file_sizes(), human_size(), Storage stats: how much disk ytfeed uses locally., (count_existing, total_bytes, count_missing) for a list of file paths., (file_count, total_bytes) for a directory tree; (0, 0) if absent., storage_page(), asset_v() (+9 more)

### Community 24 - "Community 24"
Cohesion: 0.13
Nodes (34): ChannelCategory, ChannelCategory, Group -> Category -> Type taxonomy assigned to subscribed channels.      Mirrors, backfill_channel(), add_category(), api_add(), api_delete(), api_items() (+26 more)

### Community 25 - "Community 25"
Cohesion: 0.32
Nodes (7): Credentials, Resource, get_credentials(), get_youtube_client(), OAuth2 InstalledAppFlow for the YouTube Data API (readonly)., Config, Path

### Community 26 - "Community 26"
Cohesion: 0.10
Nodes (30): SyncRun, Exception, Reporter, RunReporter, _is_quota_error(), Upsert playlists + playlist_items + videos. Returns (playlists, videos_upserted), Raised inside the sync worker when the user pressed Stop., Upsert playlists + playlist_items + videos. Returns (playlists, videos_upserted) (+22 more)

### Community 27 - "Community 27"
Cohesion: 0.11
Nodes (22): ArgumentParser, Base, Channel, ChannelUpload, Video, DeclarativeBase, Protocol, ChannelUploadsTests (+14 more)

### Community 28 - "Community 28"
Cohesion: 0.19
Nodes (22): Playlist, playlist_page(), playlists(), Playlists list and per-playlist video pages., sync_one_playlist(), _mask(), Settings page: config summary, DB stats, manual sync., Queue a sync unless one is already running. Returns True if started. (+14 more)

### Community 31 - "Community 31"
Cohesion: 0.23
Nodes (5): buildGrid(), columnDefs(), loadItems(), refreshGrid(), selectSection()

## Knowledge Gaps
- **32 isolated node(s):** `PathsConfig`, `SyncConfig`, `NotebookLMConfig`, `DownloadConfig`, `Any` (+27 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Video` connect `Community 27` to `Community 0`, `Community 2`, `Community 6`, `Community 9`, `Community 10`, `Community 23`, `Community 24`, `Community 26`, `Community 28`?**
  _High betweenness centrality (0.117) - this node is a cross-community bridge._
- **Why does `Config` connect `Community 2` to `Community 0`, `Community 5`, `Community 6`, `Community 8`, `Community 12`, `Community 14`, `Community 23`, `Community 25`, `Community 26`, `Community 27`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `Channel` connect `Community 27` to `Community 0`, `Community 6`, `Community 9`, `Community 10`, `Community 24`, `Community 26`, `Community 28`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 47 inferred relationships involving `Video` (e.g. with `ArgumentParser` and `Channel`) actually correct?**
  _`Video` has 47 INFERRED edges - model-reasoned connections that need verification._
- **Are the 35 inferred relationships involving `Channel` (e.g. with `ArgumentParser` and `Channel`) actually correct?**
  _`Channel` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 32 inferred relationships involving `Config` (e.g. with `Channel` and `Credentials`) actually correct?**
  _`Config` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `YouTubeSource` (e.g. with `Reporter` and `ChannelUploadsTests`) actually correct?**
  _`YouTubeSource` has 23 INFERRED edges - model-reasoned connections that need verification._