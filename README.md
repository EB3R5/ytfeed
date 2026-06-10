# ytfeed

Personal YouTube feed: sync subscriptions/playlists/recent uploads into a local
SQLite DB, browse/search/filter them in a local web UI, queue videos for
transcription, and pipe transcripts into an Obsidian RAG vault.

**Storage split**: the Obsidian vault gets transcript-only markdown files
(frontmatter + title + transcript). Everything else — titles, channels,
descriptions, publish dates, statuses, queue history, sync audit — lives in
the SQLite DB.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp config.example.toml config.toml   # then edit paths
.venv/bin/python -m ytfeed init-db
```

Requirements outside this repo:
- A Google OAuth client secret JSON (`paths.client_secret_path`) with the
  YouTube Data API enabled — first sync opens a browser for one-time consent;
  the token is stored at `secrets/token.json`.
- An authenticated `notebooklm-py` profile in `~/.notebooklm/` (run
  `notebooklm login` once) for transcript tier 1.

## Usage

```bash
.venv/bin/python -m ytfeed sync            # subscriptions + playlists + uploads
.venv/bin/python -m ytfeed sync --full     # ignore early-stop, walk full history
.venv/bin/python -m ytfeed serve           # web UI at http://127.0.0.1:8000
.venv/bin/python -m ytfeed transcribe --limit 5
```

## Web UI

- **Recents** — newest videos from ★-monitored channels; the channel picker
  overrides for one-off views; title search and transcript-status filters.
- **Subscriptions** — all subs with star toggles; channels open in a new tab
  with "Refresh recent" and "Load full history".
- **Playlists** — your playlists and their videos.
- **Queue** — every video list has checkboxes (shift-click selects a range,
  plus a select-all toggle) and "Queue selected for transcription".
  "Run transcription now" processes the queue in batches with live progress;
  "Clear queue" cancels pending items and hides history (rows stay in the DB).
- **Settings** — config summary, DB stats, manual "Sync now".

## Transcript pipeline (3 tiers)

1. **NotebookLM** (`notebooklm-py`) — videos batched 50 per throwaway
   `ytfeed-batch-*` notebook; transcripts extracted via source fulltext
   (verbatim caption track), then the notebook is deleted.
2. **youtube-transcript-api** — direct caption fetch, paced 1 req/s.
   IP rate-limits (`IpBlocked`/`RequestBlocked`) are treated as transient:
   nothing is written, the item is deferred 5 minutes and retried
   automatically by a background monitor thread (up to 5 attempts). After
   3 consecutive blocks the rest of the batch defers immediately.
3. **Placeholder** — `*(PLACEHOLDER).md` stub for videos with no captions;
   re-queuing a placeholder/failed video re-enters the pipeline, and a later
   success replaces the stub. Videos already `done` are never re-queued.

## Engineering notes

- SQLite runs in WAL mode with a 30s busy timeout; sync keeps all network
  I/O outside write transactions so the web app stays responsive mid-sync.
- Sync early-stops per channel once it hits known videos (~1 quota
  unit/channel steady-state); first sync backfills `sync.initial_backfill`
  videos (default 50), full history on demand.
- One pipeline run at a time (process-wide lock); interrupted runs are
  recovered on server startup.

## Tests

```bash
.venv/bin/python -m unittest discover tests
```
