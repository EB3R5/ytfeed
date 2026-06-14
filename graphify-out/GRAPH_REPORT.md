# Graph Report - ytfeed  (2026-06-13)

## Corpus Check
- 39 files · ~16,197 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 494 nodes · 1512 edges · 24 communities
- Extraction: 77% EXTRACTED · 23% INFERRED · 0% AMBIGUOUS · INFERRED: 344 edges (avg confidence: 0.66)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5f61e538`
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

## God Nodes (most connected - your core abstractions)
1. `_()` - 104 edges
2. `Video` - 47 edges
3. `oe()` - 34 edges
4. `He()` - 34 edges
5. `t()` - 32 edges
6. `Config` - 31 edges
7. `re()` - 31 edges
8. `Ce()` - 29 edges
9. `Channel` - 27 edges
10. `Fe()` - 27 edges

## Surprising Connections (you probably didn't know these)
- `CategorizeTests` --uses--> `Base`  [INFERRED]
  tests/test_categorize.py → ytfeed/db/models.py
- `CategorizeTests` --uses--> `Playlist`  [INFERRED]
  tests/test_categorize.py → ytfeed/db/models.py
- `CategorizeTests` --uses--> `PlaylistItem`  [INFERRED]
  tests/test_categorize.py → ytfeed/db/models.py
- `_playlist()` --calls--> `Playlist`  [EXTRACTED]
  tests/test_categorize.py → ytfeed/db/models.py
- `_playlist()` --calls--> `PlaylistItem`  [EXTRACTED]
  tests/test_categorize.py → ytfeed/db/models.py

## Import Cycles
- 1-file cycle: `ytfeed/youtube/sync.py -> ytfeed/youtube/sync.py`
- 1-file cycle: `ytfeed/db/models.py -> ytfeed/db/models.py`

## Communities (24 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (100): ArgumentParser, Channel, Credentials, Base, Channel, ChannelUpload, Playlist, PlaylistItem (+92 more)

### Community 1 - "Community 1"
Cohesion: 0.24
Nodes (9): get_engine(), get_session_factory(), Engine/session factory and schema creation., asset_v(), get_db(), Shared FastAPI dependencies: config, DB session, templates., File mtime as a cache-busting version for static asset URLs., Config (+1 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (50): TranscriptionQueueItem, NotebookLMClient, TranscriptionQueueItem, Shared types for the transcript pipeline., Minimal video info the providers need., TranscriptResult, VideoRef, _process_chunk() (+42 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (103): _(), A(), ae(), ar(), at(), B(), be(), br() (+95 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (35): InterviewAnalysis, EnsureCategoryTests, EnsureDescriptionTests, SanitizeTests, WriterTests, build_filename(), ensure_category_frontmatter(), ensure_description_section() (+27 more)

### Community 5 - "Community 5"
Cohesion: 0.31
Nodes (10): clear_queue(), enqueue(), queue_view(), Transcription queue: enqueue, view, run, retry., Empty the queue page: cancel pending items, hide finished ones.      Rows stay i, retry_item(), run_queue(), BackgroundTasks (+2 more)

### Community 6 - "Community 6"
Cohesion: 0.27
Nodes (15): init_db(), Namespace, build_parser(), cmd_describe(), cmd_init_db(), cmd_people(), cmd_refile(), cmd_serve() (+7 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (17): Build Phasing & Verification, CLI (`ytfeed/cli.py`, argparse subparsers), Config & Secrets, Context, Database Schema (`ytfeed/db/models.py`, SQLAlchemy 2.0), Decisions already made, Decisions from design review (grill session, 2026-06-09), FastAPI Web App (`ytfeed/web/`) (+9 more)

### Community 8 - "Community 8"
Cohesion: 0.16
Nodes (18): count_call(), fetch_channels_content_details(), fetch_my_playlists(), fetch_playlist_items(), fetch_playlist_items_paged(), fetch_playlists_by_ids(), fetch_subscriptions(), paginate() (+10 more)

### Community 9 - "Community 9"
Cohesion: 0.39
Nodes (8): Recents page: newest videos from monitored (or one-off picked) channels., Picked channels override; otherwise monitored channels. Returns (ids, used_picke, _recent_videos(), recents(), _selected_channel_ids(), toggle_monitor(), Request, Session

### Community 10 - "Community 10"
Cohesion: 0.31
Nodes (4): CategorizeTests, _playlist(), category_for_video(), Name of the smallest playlist containing the video (live item counts,     not th

### Community 11 - "Community 11"
Cohesion: 0.17
Nodes (11): Engineering notes, Launching, Schema, Setup, Tests, Transcript pipeline (3 tiers), Usage, Vault file layout (+3 more)

### Community 12 - "Community 12"
Cohesion: 0.13
Nodes (19): _run_pipeline_bg(), Process pending queue items in batches. Returns per-video results., Process pending queue items in batches. Returns per-video results., Process pending queue items in batches. Returns per-video results., Process pending queue items in batches. Returns per-video results., Process pending queue items in batches. Returns per-video results., Process pending queue items in batches. Returns per-video results., Reset items stuck in 'processing' (e.g. after a server restart killed a run). (+11 more)

### Community 13 - "Community 13"
Cohesion: 0.29
Nodes (6): download_audio(), fetch_video_metadata(), yt-dlp helpers: metadata enrichment and optional audio download., Download audio as mp3 (requires ffmpeg). Returns the file path or None., Any, Path

### Community 14 - "Community 14"
Cohesion: 0.22
Nodes (8): DownloadConfig, NotebookLMConfig, PathsConfig, PeopleConfig, Path, Load config.toml (falling back to config.example.toml) into a Config object., _resolve(), SyncConfig

### Community 23 - "Community 23"
Cohesion: 0.25
Nodes (10): _dir_size(), _file_sizes(), human_size(), Storage stats: how much disk ytfeed uses locally., (count_existing, total_bytes, count_missing) for a list of file paths., (file_count, total_bytes) for a directory tree; (0, 0) if absent., storage_page(), Path (+2 more)

## Knowledge Gaps
- **32 isolated node(s):** `PathsConfig`, `SyncConfig`, `NotebookLMConfig`, `DownloadConfig`, `Any` (+27 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Video` connect `Community 0` to `Community 2`, `Community 5`, `Community 6`, `Community 9`, `Community 23`?**
  _High betweenness centrality (0.117) - this node is a cross-community bridge._
- **Why does `write_transcript_file()` connect `Community 4` to `Community 2`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `Config` connect `Community 0` to `Community 1`, `Community 2`, `Community 6`, `Community 12`, `Community 14`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `Video` (e.g. with `ArgumentParser` and `Channel`) actually correct?**
  _`Video` has 34 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `oe()` (e.g. with `A()` and `Fe()`) actually correct?**
  _`oe()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `He()` (e.g. with `ar()` and `Ce()`) actually correct?**
  _`He()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `t()` (e.g. with `ar()` and `ct()`) actually correct?**
  _`t()` has 13 INFERRED edges - model-reasoned connections that need verification._