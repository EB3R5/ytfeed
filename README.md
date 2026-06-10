# ytfeed

Personal YouTube feed: sync subscriptions/playlists/recent uploads into a local
SQLite DB, browse/search/filter them in a local web UI, queue videos for
transcription, and pipe transcripts + descriptions into the Obsidian RAG vault
(`~/Documents/RAG/raw/`).

## Setup

```bash
cd ~/Documents/GitHub/ytfeed
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp config.example.toml config.toml   # then edit paths if needed
.venv/bin/python -m ytfeed init-db
```

## Usage

```bash
.venv/bin/python -m ytfeed sync            # first run opens a browser for OAuth
.venv/bin/python -m ytfeed sync --full     # ignore early-stop, walk full history
.venv/bin/python -m ytfeed serve           # web UI at http://127.0.0.1:8000
.venv/bin/python -m ytfeed transcribe --limit 5
```

### Web UI

- **Recents** — newest videos from your ★-monitored channels (star them on
  Subscriptions). The channel picker overrides for one-off views; search and
  transcript-status filters included.
- **Subscriptions** — all subs; click a channel to open its upload history in a
  new tab, with "Refresh recent" and "Load full history" buttons.
- **Playlists** — your playlists and their videos.
- **Queue** — checkboxes on every video list feed "Queue selected for
  transcription"; "Run transcription now" processes the queue in-process.
- **Settings** — config summary, DB stats, manual "Sync now".

### Transcript pipeline (3 tiers)

1. **NotebookLM** (`notebooklm-py`, stored profile in `~/.notebooklm/`) — videos
   are batched 50 per throwaway `ytfeed-batch-*` notebook; transcripts extracted
   via source fulltext, then the notebook is deleted.
2. **youtube-transcript-api** — direct caption fetch, per-video fallback.
3. **Placeholder** — `*(PLACEHOLDER).md` stub matching the existing vault
   convention; re-queuing a placeholder/failed video re-enters the pipeline,
   and a later success replaces the stub.

Videos already `done` are never re-queued.

## Tests

```bash
.venv/bin/python -m unittest discover tests
```
