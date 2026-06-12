# Graph Report - ytfeed  (2026-06-12)

## Corpus Check
- 37 files · ~14,954 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 404 nodes · 1321 edges · 28 communities
- Extraction: 75% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS · INFERRED: 332 edges (avg confidence: 0.67)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ad185a98`
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

## God Nodes (most connected - your core abstractions)
1. `_()` - 104 edges
2. `Video` - 43 edges
3. `oe()` - 34 edges
4. `He()` - 34 edges
5. `t()` - 32 edges
6. `re()` - 31 edges
7. `Config` - 30 edges
8. `Ce()` - 29 edges
9. `Channel` - 27 edges
10. `Fe()` - 27 edges

## Surprising Connections (you probably didn't know these)
- `ArgumentParser` --uses--> `Channel`  [INFERRED]
  ytfeed/cli.py → ytfeed/db/models.py
- `Config` --uses--> `Config`  [INFERRED]
  ytfeed/web/dependencies.py → ytfeed/config.py
- `Session` --uses--> `Config`  [INFERRED]
  ytfeed/web/dependencies.py → ytfeed/config.py
- `Request` --uses--> `Video`  [INFERRED]
  ytfeed/web/routes/storage.py → ytfeed/db/models.py
- `Session` --uses--> `Video`  [INFERRED]
  ytfeed/web/routes/storage.py → ytfeed/db/models.py

## Import Cycles
- 1-file cycle: `ytfeed/youtube/sync.py -> ytfeed/youtube/sync.py`
- 1-file cycle: `ytfeed/db/models.py -> ytfeed/db/models.py`

## Communities (28 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.10
Nodes (33): Channel, _run_channel_sync(), SyncRun, _append_log(), _best_thumbnail(), _progress(), Upsert playlists + playlist_items + videos. Returns (playlists, videos_upserted), Upsert one playlist (+ items if changed or force) from a playlists().list payloa (+25 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (55): ArgumentParser, get_engine(), get_session_factory(), init_db(), Engine/session factory and schema creation., Namespace, clear_queue(), enqueue() (+47 more)

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (35): TranscriptionQueueItem, NotebookLMClient, TranscriptionQueueItem, Shared types for the transcript pipeline., Minimal video info the providers need., TranscriptResult, VideoRef, _process_chunk() (+27 more)

### Community 3 - "Community 3"
Cohesion: 0.22
Nodes (26): br(), Ce(), ct(), d(), Dt(), ee(), fr(), gt() (+18 more)

### Community 4 - "Community 4"
Cohesion: 0.16
Nodes (13): SanitizeTests, WriterTests, build_filename(), _frontmatter(), Write transcript markdown files into the Obsidian RAG vault., Transcript-only vault file: frontmatter identifies the video, the body     is th, sanitize_filename(), write_transcript_file() (+5 more)

### Community 5 - "Community 5"
Cohesion: 0.23
Nodes (21): _(), c(), de(), F(), ft(), g(), ge(), gr() (+13 more)

### Community 6 - "Community 6"
Cohesion: 0.28
Nodes (21): ae(), bt(), cr(), dr(), He(), hr(), le(), lr() (+13 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (17): Build Phasing & Verification, CLI (`ytfeed/cli.py`, argparse subparsers), Config & Secrets, Context, Database Schema (`ytfeed/db/models.py`, SQLAlchemy 2.0), Decisions already made, Decisions from design review (grill session, 2026-06-09), FastAPI Web App (`ytfeed/web/`) (+9 more)

### Community 8 - "Community 8"
Cohesion: 0.16
Nodes (18): count_call(), fetch_channels_content_details(), fetch_my_playlists(), fetch_playlist_items(), fetch_playlist_items_paged(), fetch_playlists_by_ids(), fetch_subscriptions(), paginate() (+10 more)

### Community 9 - "Community 9"
Cohesion: 0.30
Nodes (15): ar(), at(), be(), er(), ir(), je(), L(), mr() (+7 more)

### Community 10 - "Community 10"
Cohesion: 0.36
Nodes (13): A(), B(), e(), Fe(), ie(), ke(), kt(), me() (+5 more)

### Community 11 - "Community 11"
Cohesion: 0.20
Nodes (9): Engineering notes, Launching, Schema, Setup, Tests, Transcript pipeline (3 tiers), Usage, Web UI (+1 more)

### Community 12 - "Community 12"
Cohesion: 0.39
Nodes (8): Recents page: newest videos from monitored (or one-off picked) channels., Picked channels override; otherwise monitored channels. Returns (ids, used_picke, _recent_videos(), recents(), _selected_channel_ids(), toggle_monitor(), Request, Session

### Community 13 - "Community 13"
Cohesion: 0.29
Nodes (6): download_audio(), fetch_video_metadata(), yt-dlp helpers: metadata enrichment and optional audio download., Download audio as mp3 (requires ffmpeg). Returns the file path or None., Any, Path

### Community 14 - "Community 14"
Cohesion: 0.43
Nodes (7): et(), nt(), qe(), Rt(), se(), tt(), y()

### Community 23 - "Community 23"
Cohesion: 0.33
Nodes (14): SyncRun, _mask(), Settings page: config summary, DB stats, manual sync., Queue a sync unless one is already running. Returns True if started., settings_page(), start_sync(), stop_sync(), sync_is_running() (+6 more)

### Community 24 - "Community 24"
Cohesion: 0.24
Nodes (17): Channel, ChannelUpload, Video, backfill_channel(), channel_page(), Subscriptions list and per-channel drill-down pages., refresh_channel(), subscriptions() (+9 more)

### Community 25 - "Community 25"
Cohesion: 0.24
Nodes (16): Playlist, PlaylistItem, Exception, playlist_page(), playlists(), Playlists list and per-playlist video pages., sync_one_playlist(), _is_quota_error() (+8 more)

### Community 26 - "Community 26"
Cohesion: 0.23
Nodes (13): Credentials, Base, DeclarativeBase, Engine, Resource, sessionmaker, get_credentials(), get_youtube_client() (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.67
Nodes (3): SQLAlchemy 2.0 models for ytfeed., utcnow(), datetime

## Knowledge Gaps
- **30 isolated node(s):** `PathsConfig`, `SyncConfig`, `NotebookLMConfig`, `DownloadConfig`, `Any` (+25 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Video` connect `Community 24` to `Community 0`, `Community 1`, `Community 2`, `Community 12`, `Community 23`, `Community 25`, `Community 26`, `Community 27`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Why does `Config` connect `Community 26` to `Community 0`, `Community 1`, `Community 2`, `Community 24`, `Community 25`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Why does `write_transcript_file()` connect `Community 4` to `Community 2`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 31 inferred relationships involving `Video` (e.g. with `Channel` and `Exception`) actually correct?**
  _`Video` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `oe()` (e.g. with `A()` and `Fe()`) actually correct?**
  _`oe()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `He()` (e.g. with `ar()` and `Ce()`) actually correct?**
  _`He()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `t()` (e.g. with `ar()` and `ct()`) actually correct?**
  _`t()` has 13 INFERRED edges - model-reasoned connections that need verification._