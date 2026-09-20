# Graph Report - ytfeed  (2026-09-16)

## Corpus Check
- 52 files · ~116,831 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 677 nodes · 1978 edges · 36 communities (30 shown, 6 thin omitted)
- Extraction: 75% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS · INFERRED: 488 edges (avg confidence: 0.61)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3f64f2e4`
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
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 35|Community 35]]

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
- `FakeSource` --uses--> `Base`  [INFERRED]
  tests/test_sync.py → ytfeed/db/models.py
- `FakeSource` --uses--> `Channel`  [INFERRED]
  tests/test_sync.py → ytfeed/db/models.py

## Import Cycles
- 1-file cycle: `ytfeed/youtube/sync.py -> ytfeed/youtube/sync.py`
- 1-file cycle: `ytfeed/db/models.py -> ytfeed/db/models.py`

## Communities (36 total, 6 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (51): utcnow(), SyncRun, _append_log(), _best_thumbnail(), _is_quota_error(), _parse_dt(), _progress(), Sync engine: subscriptions, playlists, and per-channel uploads with early-stop. (+43 more)

### Community 1 - "Community 1"
Cohesion: 0.19
Nodes (4): ChannelUploadsTests, FakeSource, _item(), A canned YouTubeSource — no network, no google client to fake.

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (74): TranscriptionQueueItem, NotebookLMClient, clear_queue(), enqueue(), queue_view(), Transcription queue: enqueue, view, run, retry., Empty the queue page: cancel pending items, hide finished ones.      Rows stay i, retry_item() (+66 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (103): _(), A(), ae(), ar(), at(), B(), be(), br() (+95 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (33): InterviewAnalysis, EnsureCategoryTests, EnsureDescriptionTests, WriterTests, build_filename(), ensure_category_frontmatter(), ensure_description_section(), ensure_people_frontmatter() (+25 more)

### Community 5 - "Community 5"
Cohesion: 0.20
Nodes (6): CategorizeTests, _playlist(), SanitizeTests, category_for_video(), Name of the smallest playlist containing the video (live item counts,     not th, sanitize_filename()

### Community 6 - "Community 6"
Cohesion: 0.34
Nodes (13): _mask(), Settings page: config summary, DB stats, manual sync., Queue a sync unless one is already running. Returns True if started., settings_page(), start_sync(), stop_sync(), sync_is_running(), trigger_playlists_sync() (+5 more)

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
Cohesion: 0.52
Nodes (6): _free_port(), main(), Desktop window launcher — the same file in every app repo; only the CONFIG block, _set_dock_icon(), _up(), _wait_until_up()

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (12): Engineering notes, Launching, Packaging, Schema, Setup, Tests, Transcript pipeline (3 tiers), Usage (+4 more)

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (11): AuditedRunTests, audited_run(), _is_quota_error(), The audited sync-run lifecycle, owned in one place.  A sync run records its own, Open a SyncRun, yield its reporter, and write the terminal state on exit.      S, Open a SyncRun, yield its reporter, and write the terminal state on exit.      S, Writes progress/log/quota-accounting into one SyncRun row.      The API-unit bas, RunReporter (+3 more)

### Community 13 - "Community 13"
Cohesion: 0.29
Nodes (6): download_audio(), fetch_video_metadata(), yt-dlp helpers: metadata enrichment and optional audio download., Download audio as mp3 (requires ffmpeg). Returns the file path or None., Any, Path

### Community 14 - "Community 14"
Cohesion: 0.29
Nodes (6): desktop/launcher.py, desktop/linux, desktop/macos, docker, Packaging targets, server (venv)

### Community 23 - "Community 23"
Cohesion: 0.05
Nodes (65): Credentials, get_engine(), get_session_factory(), init_db(), Engine/session factory and schema creation., Engine, Namespace, Resource (+57 more)

### Community 24 - "Community 24"
Cohesion: 0.13
Nodes (34): ChannelCategory, ChannelCategory, Group -> Category -> Type taxonomy assigned to subscribed channels.      Mirrors, backfill_channel(), add_category(), api_add(), api_delete(), api_items() (+26 more)

### Community 26 - "Community 26"
Cohesion: 0.21
Nodes (24): Channel, ChannelUpload, Playlist, PlaylistItem, SQLAlchemy 2.0 models for ytfeed., SyncRun, Exception, Reporter (+16 more)

### Community 27 - "Community 27"
Cohesion: 0.17
Nodes (16): ArgumentParser, Base, Channel, Video, DeclarativeBase, Protocol, _FakeListEndpoint, _FakeRequest (+8 more)

### Community 28 - "Community 28"
Cohesion: 0.39
Nodes (7): playlist_page(), playlists(), Playlists list and per-playlist video pages., sync_one_playlist(), BackgroundTasks, Request, Session

### Community 31 - "Community 31"
Cohesion: 0.23
Nodes (5): buildGrid(), columnDefs(), loadItems(), refreshGrid(), selectSection()

## Knowledge Gaps
- **43 isolated node(s):** `install.sh script`, `run.sh script`, `GI_TYPELIB_PATH`, `uninstall.sh script`, `build.sh script` (+38 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Video` connect `Community 27` to `Community 0`, `Community 1`, `Community 2`, `Community 6`, `Community 9`, `Community 23`, `Community 24`, `Community 26`, `Community 28`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Why does `Config` connect `Community 2` to `Community 0`, `Community 8`, `Community 23`, `Community 26`, `Community 27`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `Channel` connect `Community 27` to `Community 0`, `Community 1`, `Community 6`, `Community 9`, `Community 23`, `Community 24`, `Community 26`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 47 inferred relationships involving `Video` (e.g. with `ArgumentParser` and `Channel`) actually correct?**
  _`Video` has 47 INFERRED edges - model-reasoned connections that need verification._
- **Are the 35 inferred relationships involving `Channel` (e.g. with `ArgumentParser` and `Channel`) actually correct?**
  _`Channel` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 32 inferred relationships involving `Config` (e.g. with `Channel` and `Credentials`) actually correct?**
  _`Config` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `YouTubeSource` (e.g. with `Reporter` and `ChannelUploadsTests`) actually correct?**
  _`YouTubeSource` has 23 INFERRED edges - model-reasoned connections that need verification._