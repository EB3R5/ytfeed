# ytfeed — Personal YouTube Feed App

## Context

Christian wants a personal YouTube "feed" tool, separate from YouTube's own UI:
sync subscriptions/playlists/recent uploads into a local DB, browse/search/filter
that feed in a local web UI, drill into a channel's full upload history in a new
window to pick videos for transcription, and pipe transcripts + descriptions into
his Obsidian RAG vault (`/Users/christian/Documents/RAG/raw/`) for the existing
wiki-compile workflow (documented in `RAG/CLAUDE.md.md`).

The project lives at `/Users/christian/Documents/GitHub/ytfeed` (currently empty,
will become its own git repo).

### Decisions already made
- **UI**: local web app — FastAPI + Jinja2 + htmx, served to the browser. Three
  main pages: **Recents / Subscriptions / Playlists** (see Web App section).
  "Drill down into a channel in another window" = `target="_blank"` link to a
  per-channel page.
- **DB**: SQLite via SQLAlchemy 2.0, file at `data/ytfeed.db`.
- **Auth**: OAuth2 `InstalledAppFlow`, scope `youtube.readonly`, mirroring the
  working pattern in `Archive/Obsidian-IO/Playlists/Create Playlists.py` (do NOT
  reuse its MongoDB code or its hardcoded Mongo credentials — flagged separately
  as a pre-existing security issue to fix later).
- **Transcripts**: 3-tier fallback — NotebookLM (primary) → `youtube-transcript-api`
  (fallback) → placeholder stub (last resort), matching the existing
  `RAG/raw/*(PLACEHOLDER).md` convention.
- **Obsidian export target**: `/Users/christian/Documents/RAG/raw/`, filenames
  `"{Title} - {Channel}.md"`.

### Decisions from design review (grill session, 2026-06-09)
- **NotebookLM tier = free**: 50 sources/notebook, `batch_size = 50`. 100 videos
  = 2 batch notebooks. NotebookLM stays tier 1 of the transcript pipeline.
- **Notebook cleanup = auto-delete after extract**: pipeline creates a batch
  notebook, pulls all fulltexts, then deletes the notebook (free tier also caps
  total notebooks). Transcripts persist in DB + RAG vault.
- **Initial backfill = configurable N** (`sync.initial_backfill`, default 50
  videos/channel ≈ 1 API unit each). Per-channel "Load full history" button on
  the channel page triggers `force_full` backfill on demand.
- **Nav = three pages**: Recents (channel multi-select picker, empty until
  channels picked, then newest videos for the picked subs), Subscriptions (list
  of subs → per-channel recent uploads/drill-down), Playlists (list of playlists
  → videos therein).
- **Queue UI everywhere**: checkboxes + "Queue selected for transcription" on
  Recents, channel pages, and playlist pages — one shared `video_row.html`
  partial.
- **Re-queue behavior**: skip videos with `transcript_status='done'`; videos in
  `failed`/`placeholder` re-enter the pipeline (placeholder file replaced on
  success). No accidental NotebookLM spend or RAG duplicates.
- **Audio download**: code ships, `download_audio = false` by default.
- **Transcription trigger**: "Run transcription now" button on the queue page
  (BackgroundTasks + htmx polling) AND `python -m ytfeed transcribe` CLI. The
  UI button is firm scope, not optional.
- **Sync cadence = manual only**: sync button in UI + CLI. No daemon/scheduler;
  cron can call the CLI later if wanted.

### Key research finding: NotebookLM integration is already half-done

`notebooklm-py` v0.7.1 (PyPI name `notebooklm-py`, import name `notebooklm`) is
installed system-wide and **already authenticated** — `~/.notebooklm/profiles/default/`
has a `browser_profile` + `context.json` containing a real `notebook_id`. This means
`NotebookLMClient.from_storage(profile="default")` should work immediately, no new
login needed (Phase 3 should smoke-test this first thing).

Real API (verified by reading the installed package source):
```python
from notebooklm import NotebookLMClient, SourceFulltext, NotebookLimitError, SourceAddError, SourceTimeoutError, RateLimitError, SourceNotFoundError

async with NotebookLMClient.from_storage(profile="default") as client:
    notebooks = await client.notebooks.list()
    notebook = await client.notebooks.create(title="ytfeed-batch-2026-06-09")
    source = await client.sources.add_url(notebook.id, video_url, wait=False)
    await client.sources.wait_for_sources(notebook.id, [source.id])
    fulltext: SourceFulltext = await client.sources.get_fulltext(notebook.id, source.id, output_format="text")
    # fulltext.content is the transcript text, fulltext.title, fulltext.char_count
```
- `add_url` auto-detects YouTube URLs (source type 9 = youtube) and extracts the
  caption transcript as the source's fulltext.
- Source limits: 50/notebook (free), 300 (Plus), 600 (Ultra) — batch in groups of
  50 by default (configurable). `notebooks.create` raises `NotebookLimitError` if
  the account's notebook quota is hit.
- The library is async (httpx-based) — `notebooklm_provider.py` will be `async def`,
  invoked via `asyncio.run()` from the CLI, or `await`ed directly in FastAPI.
- Catch `SourceAddError`, `SourceTimeoutError`, `RateLimitError`, `SourceNotFoundError`,
  `NotebookLimitError` individually — on any of these for a video, fall through to
  tier 2 (`youtube-transcript-api`).

There's also a leftover `~/.ytradar/` directory (token.json, profiles.json) from
what looks like an earlier abandoned attempt at a similar tool — no project code
remains, not directly reused, but ignore/leave it alone.

---

## Project Structure

```
/Users/christian/Documents/GitHub/ytfeed/
├── .gitignore
├── README.md
├── pyproject.toml              # installable package, console entry point
├── requirements.txt
├── config.example.toml         # committed template
├── config.toml                 # gitignored, user's actual config
├── data/.gitkeep                # ytfeed.db lives here (gitignored)
├── secrets/.gitkeep             # client_secret.json / token.json (gitignored)
├── ytfeed/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   ├── cli.py
│   ├── db/
│   │   ├── models.py
│   │   └── session.py
│   ├── youtube/
│   │   ├── auth.py
│   │   ├── client.py           # paginated API wrappers
│   │   └── sync.py              # sync engine
│   ├── metadata/
│   │   └── ytdlp_client.py      # yt-dlp metadata + optional audio download
│   ├── transcripts/
│   │   ├── base.py               # TranscriptResult, provider protocol
│   │   ├── notebooklm_provider.py
│   │   ├── youtube_api_provider.py
│   │   ├── placeholder.py
│   │   ├── markdown_writer.py
│   │   └── pipeline.py           # 3-tier orchestration
│   └── web/
│       ├── app.py
│       ├── dependencies.py
│       ├── routes/
│       │   ├── recents.py
│       │   ├── channel.py        # subscriptions list + per-channel page
│       │   ├── playlist.py
│       │   ├── queue.py
│       │   └── settings.py
│       ├── templates/
│       │   ├── base.html, recents.html, subscriptions.html, channel.html,
│       │   │   playlists.html, playlist.html, queue.html, settings.html
│       │   └── partials/video_row.html, flash.html
│       └── static/style.css
└── tests/
```

---

## Database Schema (`ytfeed/db/models.py`, SQLAlchemy 2.0)

- **`channels`** — subscribed channels: `channel_id` (unique), `title`,
  `description`, `thumbnail_url`, `uploads_playlist_id`, `subscribed_at`,
  `last_synced_at`, `last_video_published_at`, `is_active`, `is_monitored`
  (bool, default false — channels the user has starred for the Recents page).
- **`playlists`** — user's own playlists: `playlist_id` (unique), `title`,
  `description`, `thumbnail_url`, `item_count`, `last_synced_at`.
- **`videos`** — canonical, deduped by `video_id`: `channel_id` (nullable FK),
  `channel_title`, `title`, `description`, `thumbnail_url`, `published_at`
  (indexed), `duration_seconds`, `tags` (JSON text), `source`,
  `transcript_status` (`none|queued|in_progress|done|failed|placeholder`),
  `transcript_source` (`notebooklm|youtube_api|placeholder`), `transcript_path`,
  `audio_status`, `audio_path`, `notebooklm_notebook_id`.
- **`playlist_items`** — join table `(playlist_id, video_id, position, added_at)`,
  unique on `(playlist_id, video_id)`.
- **`channel_uploads`** — join table `(channel_id, video_id, published_at)`,
  unique on `(channel_id, video_id)`, indexed on `(channel_id, published_at)`.
- **`transcription_queue`** — `(video_id, status, requested_at, started_at,
  completed_at, error_message, attempt_count)`.
- **`sync_runs`** — audit log: `(started_at, finished_at, kind,
  channels_synced, videos_upserted, error_message)`.

Indexes: `videos.published_at`, `videos.transcript_status`, `videos.channel_id`,
`videos.title`.

---

## YouTube Sync Engine (`ytfeed/youtube/`)

**`auth.py`** — port `Create Playlists.py`'s OAuth flow:
```python
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
def get_credentials(client_secret_path, token_path) -> Credentials: ...
def get_youtube_client(config) -> Resource: ...
```
`config.toml` should point `client_secret_path` directly at the existing
`/Users/christian/Documents/GitHub/Archive/Obsidian-IO/Tokens/inputoutput.json`
(no copy needed) — `token_path` defaults to `secrets/token.json` (fresh OAuth on
first run, browser opens via `run_local_server(port=0)`).

**`client.py`** — generic paginator + thin wrappers:
- `fetch_subscriptions(youtube)` → `subscriptions().list(part='snippet,contentDetails', mine=True, maxResults=50)`
- `fetch_my_playlists(youtube)` → `playlists().list(part='snippet,contentDetails', mine=True, maxResults=50)`
- `fetch_playlist_items(youtube, playlist_id)` → `playlistItems().list(part='snippet,contentDetails', playlistId=..., maxResults=50)`
- `fetch_channels_content_details(youtube, channel_ids)` → batches of 50 via `channels().list(part='contentDetails', id=','.join(...))`, returns `{channel_id: uploads_playlist_id}`

**`sync.py`** — core functions:
- `sync_subscriptions(session, youtube)`: upsert `channels` from
  `fetch_subscriptions`; for any with `uploads_playlist_id IS NULL`, resolve via
  `fetch_channels_content_details` in batches of 50.
- `sync_my_playlists(session, youtube)`: upsert `playlists` + `playlist_items` +
  `videos` for each of the user's playlists.
- `sync_channel_uploads(session, youtube, channel, force_full=False)`:
  paginate `playlistItems().list(playlistId=channel.uploads_playlist_id,
  maxResults=50)` (newest-first). **Stop early** (unless `force_full`) once a
  video is found that already has a `channel_uploads` row for this channel, or
  `published_at <= channel.last_video_published_at`. On a channel's FIRST sync
  (no prior rows), cap at `config.sync.initial_backfill` videos (default 50 ≈
  one page = 1 quota unit) instead of walking full history; `force_full=True`
  (the per-channel "Load full history" button / `sync --full`) ignores both the
  cap and early-stop. Upsert `videos` + `channel_uploads` for new ones. Update
  `channel.last_synced_at` and `last_video_published_at`.
- `sync_all(session, youtube, progress_cb=None)`: runs all three phases, wraps
  each in a `sync_runs` row, commits incrementally per-channel.

This early-stop logic keeps steady-state syncs to ~1 API unit per channel
(`playlistItems.list` = 1 quota unit when the first page already hits a known video).

---

## FastAPI Web App (`ytfeed/web/`)

Top nav: **Recents | Subscriptions | Playlists | Queue | Settings**. Every
video list uses the shared `partials/video_row.html` (thumbnail, title, channel,
published date, transcript-status badge, queue checkbox) so queueing works from
all three browse pages.

- **`routes/recents.py`** — `GET /` (Recents): defaults to newest videos from
  **monitored** channels (`channels.is_monitored = true`), newest first. If no
  channels are monitored yet, page is empty with the channel picker prompting
  selection. Channel multi-select picker overrides/filters the view for
  one-off sessions (URL params, not persisted). Supports `q` search and
  `transcript_status` filter. htmx swaps in `video_row` partials on
  picker/search change (`hx-trigger="change, keyup changed delay:300ms"`).
  - `POST /channels/{channel_id}/monitor` — toggle `is_monitored`; star
    button rendered on Subscriptions list, channel pages, and the Recents
    picker.
- **`routes/channel.py`**:
  - `GET /subscriptions` — list of all subscriptions, each linking
    `target="_blank"` to `/channels/{channel_id}`.
  - `GET /channels/{channel_id}` — that channel's synced uploads
    (`channel_uploads` joined to `videos`, newest first), checkboxes per video,
    "Queue selected for transcription" form, optional `q` search.
  - `POST /channels/{channel_id}/refresh` — on-demand `sync_channel_uploads`
    for just this channel.
  - `POST /channels/{channel_id}/backfill` — "Load full history" button:
    `sync_channel_uploads(..., force_full=True)` via `BackgroundTasks`.
- **`routes/playlist.py`**:
  - `GET /playlists` — list of the user's playlists.
  - `GET /playlists/{playlist_id}` — videos in that playlist (via
    `playlist_items`), same checkboxes + queue form.
- **`routes/queue.py`**:
  - `POST /queue` — inserts `transcription_queue` rows for selected
    `video_id`s; **skips videos with `transcript_status='done'`** and any
    already pending/processing; `failed`/`placeholder` videos are allowed back
    in. Sets `videos.transcript_status='queued'`.
  - `GET /queue` — status view of pending/processing/done/failed items.
  - `POST /queue/run` — "Run transcription now": kicks
    `run_transcription_pipeline()` via `BackgroundTasks`; page polls status
    via htmx.
  - `POST /queue/{id}/retry` — resets a failed item to `pending`.
- **`routes/settings.py`**:
  - `GET /settings` — config summary (masked secrets), per-channel last-sync
    times, DB stats.
  - `POST /settings/sync` — runs `sync_all()` via `BackgroundTasks`; `/settings`
    polls the latest `sync_runs` row via htmx (`hx-trigger="every 2s"`).

---

## Transcript Pipeline (`ytfeed/transcripts/`)

**`base.py`**:
```python
@dataclass
class TranscriptResult:
    video_id: str
    success: bool
    text: str | None = None
    source: str | None = None  # "notebooklm" | "youtube_api"
    error: str | None = None
```

**`notebooklm_provider.py`** (async, see API details in Context above):
```python
async def transcribe_batch(videos: list[VideoRef], batch_size=50, profile="default") -> dict[str, TranscriptResult]:
    # chunk videos into groups of batch_size (50 = free-tier source limit)
    # for each chunk: create a notebook ("ytfeed-batch-{timestamp}"),
    #   add_url() each video (wait=False), wait_for_sources() on the batch,
    #   get_fulltext() per source -> TranscriptResult(success=True, text=fulltext.content, source="notebooklm")
    #   then DELETE the notebook (client.notebooks.delete) — transcripts are
    #   extracted; free tier caps total notebooks, so don't accumulate them.
    #   Delete even on partial failure (failed videos fall to tier 2 anyway).
    # catch SourceAddError/SourceTimeoutError/RateLimitError/SourceNotFoundError/NotebookLimitError
    #   per-video -> TranscriptResult(success=False, error=...)
```
Before building this out, Phase 3 should start with a **smoke test**:
`async with NotebookLMClient.from_storage(profile="default") as client: print(await client.notebooks.list())`
to confirm the existing stored session still works. ytfeed never touches the
user's pre-existing notebook (`context.json`'s `notebook_id`) — it only creates
and deletes its own `ytfeed-batch-*` notebooks.

**`youtube_api_provider.py`** — `youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)`,
join segments, catch `TranscriptsDisabled`/`NoTranscriptFound`/`VideoUnavailable`.
Build and verify this tier FIRST (no auth needed, simplest).

**`placeholder.py`** / **`markdown_writer.py`** — write to `RAG/raw/`:
- Filename: `"{Title} - {Channel}.md"` (sanitized), `" (PLACEHOLDER)"` suffix
  for stubs.
- YAML frontmatter: `video_id, channel, published, url, source, tags: []`.
- Body: `# {Title}`, metadata block, `## Description` (from yt-dlp), `## Transcript`
  (full text) — or for placeholders, `## Transcription Status` with the error and
  manual-fallback instructions, mirroring the existing
  `RAG/raw/*(PLACEHOLDER).md` tone/structure.

**`pipeline.py`** — `run_transcription_pipeline(session, config, video_ids=None)`:
1. Select pending `transcription_queue` rows (or specific `video_ids`).
2. If NotebookLM enabled: `asyncio.run(notebooklm_provider.transcribe_batch(...))`
   for all pending videos.
3. For any without a successful result: `youtube_api_provider.fetch(...)` one at
   a time.
4. For any still without a transcript: `placeholder.write_placeholder_file(...)`.
5. For successes: optionally enrich with `ytdlp_client.fetch_video_metadata()`
   description, then `markdown_writer.write_transcript_file(...)`.
6. Update `videos.transcript_status/source/path` and `transcription_queue.status`,
   commit per-video.

**`metadata/ytdlp_client.py`**:
- `fetch_video_metadata(video_id)` — `YoutubeDL({'quiet': True, 'skip_download': True}).extract_info(url, download=False)`, returns `None` on `DownloadError`.
- `download_audio(video_id, output_dir)` — optional, mirrors
  `Archive/Obsidian-IO/Transcriptions/Transcribe Playlists.py`'s yt-dlp+ffmpeg
  mp3 pattern; only called if `config.download_audio=True`.

---

## CLI (`ytfeed/cli.py`, argparse subparsers)

- `python -m ytfeed init-db` — create SQLite file + tables.
- `python -m ytfeed sync [--full] [--channel CHANNEL_ID]`
- `python -m ytfeed serve [--host] [--port] [--reload]` — runs uvicorn.
- `python -m ytfeed transcribe [--video-id ID ...] [--limit N]`

---

## Config & Secrets

**`config.example.toml`** (committed):
```toml
[paths]
db_path = "data/ytfeed.db"
client_secret_path = "/Users/christian/Documents/GitHub/Archive/Obsidian-IO/Tokens/inputoutput.json"
token_path = "secrets/token.json"
rag_output_dir = "/Users/christian/Documents/RAG/raw"
audio_output_dir = "data/audio"

[sync]
initial_backfill = 50   # videos per channel on first sync; full history on demand

[notebooklm]
enabled = true
batch_size = 50          # free-tier source limit per notebook
profile = "default"
delete_notebook_after_extract = true

[download]
download_audio = false
```
`config.toml` (gitignored) is the user's editable copy.

**`.gitignore`**: `__pycache__/`, `.venv/`, `*.egg-info/`, `config.toml`,
`secrets/`, `data/`, `.DS_Store`. Note: NotebookLM session state lives in
`~/.notebooklm/` (outside the project) — nothing to gitignore there.

**`requirements.txt`**:
```
fastapi
uvicorn[standard]
jinja2
python-multipart
sqlalchemy>=2.0
google-api-python-client
google-auth-oauthlib
google-auth
yt-dlp
youtube-transcript-api
notebooklm-py
```

---

## Build Phasing & Verification

### Phase 1 — Auth + Sync + DB + CLI (headless, verifiable via sqlite3)
Scaffold structure, `git init`, `pyproject.toml`/`requirements.txt`/`.gitignore`,
implement `db/models.py`, `db/session.py`, `config.py`, `youtube/auth.py`,
`youtube/client.py`, `youtube/sync.py`, `cli.py` (`init-db`, `sync`).

**Verify**: `python -m ytfeed init-db` creates `data/ytfeed.db` with all tables
(`sqlite3 data/ytfeed.db ".tables"`). `python -m ytfeed sync` triggers OAuth
(browser opens first run), populates `channels`/`playlists`/`playlist_items`/
`videos`/`channel_uploads` (check counts via `sqlite3`). Run `sync` again — should
be fast (early-stop) with no duplicate rows.

### Phase 2 — FastAPI Recents/Subscriptions/Playlists UI + queue
Implement `web/app.py`, `dependencies.py`, templates, `routes/recents.py`,
`routes/channel.py`, `routes/playlist.py`, `routes/queue.py`,
`routes/settings.py`, `cli.py serve`.

**Verify**: `python -m ytfeed serve`, open `http://127.0.0.1:8000/`. Recents
starts empty; pick 2-3 channels → their newest videos appear. Subscriptions
lists subs; clicking one opens `/channels/{id}` in a new tab; "Load full
history" backfills that channel. Playlists page shows playlists and their
videos. Queue videos from all three pages; confirm `transcription_queue` rows +
`transcript_status='queued'` via the `/queue` view or `sqlite3`; confirm
re-queueing a `done` video is skipped.

### Phase 3 — Transcript pipeline + Obsidian export
Smoke-test `NotebookLMClient.from_storage(profile="default")` first. Implement
`metadata/ytdlp_client.py`, `transcripts/base.py`, `markdown_writer.py`,
`placeholder.py`, `youtube_api_provider.py` (verify this tier alone first),
then `notebooklm_provider.py` (incl. notebook auto-delete), then `pipeline.py`,
then `cli.py transcribe`, then the "Run transcription now" button in
`routes/queue.py` via `BackgroundTasks` (firm scope, not optional).

**Verify**: queue 1-2 videos, run `python -m ytfeed transcribe --limit 2`. Check
`videos.transcript_status` becomes `done`/`placeholder`, and a new `.md` file
appears in `/Users/christian/Documents/RAG/raw/` with correct filename,
frontmatter, and transcript/placeholder content. Test the fallback path by
setting `notebooklm.enabled = false` and using a video with captions disabled —
confirm the placeholder file matches the existing convention's tone/structure.

---

## Notes / Open Items
- The hardcoded MongoDB credentials in `Archive/Obsidian-IO/Playlists/Create
  Playlists.py` are unrelated to ytfeed but should be rotated/removed separately.
- `ytfeed/` will be its own git repo nested inside the home-directory repo —
  fine, git won't descend into it; optionally add `ytfeed/` to the home repo's
  `.gitignore` later if it shows up as untracked clutter.
- `videos.tags` stored as JSON text for v1 (searchable via `LIKE`); SQLite FTS5
  is a possible future enhancement, not required now.
