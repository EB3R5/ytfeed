# Packaging targets

Everything that launches the app lives here; `ytfeed/` never changes for a new target (the one
exception was adding `/healthz`, which every target probes). `packaging/` has no `__init__.py` and
is never imported — it would shadow the PyPI `packaging` library. Scripts run the launcher by path.

**Operating model.** Docker owns the app's port (8040) via `compose.yml` at the repo root. The `.app`
window, the Linux desktop entry and `scripts/ytfeed-launch` attach to whatever answers `/healthz` there;
only when nothing does, they start their own uvicorn and stop it when the window closes. The venv
server (`python -m ytfeed serve --port 8040`) is for development: run it with the container stopped,
or on another port. `data/ytfeed.db` is SQLite in WAL mode and the transcript pipeline writes the
vault, so keep one server on them at a time.

**What stays on the host.** Both Google logins are interactive and never run in the container:
- YouTube consent (`InstalledAppFlow.run_local_server`) — run `python -m ytfeed sync` in the venv
  once; it writes `secrets/token.json`, which the container then refreshes on its own.
- NotebookLM (`notebooklm login`) — writes `~/.notebooklm/profiles/<profile>/storage_state.json`;
  the container mounts `~/.notebooklm` and talks to NotebookLM over plain HTTPS with those cookies.

## server (venv)

```bash
python -m venv .venv && ./.venv/bin/pip install -e ".[desktop,dev]"
.venv/bin/python -m ytfeed serve --port 8040       # or scripts/ytfeed-launch
```

## docker

Build context is the repo root; the image runs `python -m ytfeed serve` on 8000 and health-checks
`/healthz`. It carries its own `config.toml` (`packaging/docker/config.toml`) with container paths,
so the host's `config.toml` (dockerignored) is untouched.

```bash
cp .env.example .env            # set YTFEED_VAULT (and your uid/gid, see `id -u`)
docker compose up -d --build    # publishes 127.0.0.1:8040 (YTFEED_PORT to change)
```

`compose.yml` mounts:

| host | container | why |
|---|---|---|
| `./data` | `/app/data` | `ytfeed.db`, server cache (`HOME` and `XDG_CACHE_HOME` point here) |
| `./secrets` | `/app/secrets` | `token.json`; a refresh rewrites it |
| `$YTFEED_VAULT` | `/rag/raw` | the vault folder transcripts are written to, read-write |
| `$NOTEBOOKLM_DIR` (default `~/.notebooklm`) | `/nlm` (`NOTEBOOKLM_HOME`) | NotebookLM cookies + lock files |

`Video.transcript_path` stores the absolute path as the writer saw it, so rows written by the
container start with `/rag/raw/`; the Storage page only uses them for size/missing counts.

The container runs as `YTFEED_UID:YTFEED_GID` so vault files it creates are owned by you, not
root. The image has no ffmpeg: keep `download_audio = false`. If another compose project should
own the service instead, point its build at `packaging/docker/Dockerfile` and reproduce the four
mounts; nothing in the image depends on this repo's `compose.yml`.

Without compose:

```bash
docker build -f packaging/docker/Dockerfile -t ytfeed .
docker run --rm --user "$(id -u):$(id -g)" -p 127.0.0.1:8099:8000 \
  -v ./data:/app/data -v ./secrets:/app/secrets \
  -v /path/to/vault/raw:/rag/raw -v ~/.notebooklm:/nlm ytfeed
```

## desktop/launcher.py

Shared pywebview launcher; the CONFIG block at the top is the only per-repo difference.
`./.venv/bin/python packaging/desktop/launcher.py` needs the `desktop` extra. `LOAD_DOTENV = False`:
config is `config.toml`, there is no `.env`.

## desktop/macos

`build.sh` compiles `launcher.c`, takes the icon from `icon-1024.png` via `make_icon.py`, assembles and ad-hoc signs
`/Applications/ytfeed.app`. The launcher is a compiled Mach-O, not a shell script: TCC attributes
Documents-folder access to the code signature, and a zsh launcher is attributed to `/bin/zsh` and
dies with EPERM reading the venv. Approve the Documents prompt on first launch; every rebuild
re-signs, so macOS asks again. `build.sh` compiles the path of the checkout it runs from into
the binary (`-DYTFEED_REPO`); move the repo and rebuild, or set `YTFEED_REPO` in the launch
environment to override it.

## desktop/linux

pywebview's GTK/WebKit2 backend, on Arch (Omarchy) or Debian/Ubuntu. `install.sh` checks the
distro packages (Arch: `python-gobject gtk3 webkit2gtk-4.1`; Debian: `python3-gi gir1.2-gtk-3.0
gir1.2-webkit2-4.1`), drops `system-gi.pth` into the venv so the system `gi` module is visible,
renders `ytfeed.desktop` with this repo's path, and installs it with `ytfeed.png` under
`~/.local/share`. `run.sh` is what the entry executes (venv python, no uv). `uninstall.sh` reverses it.

## scripts/ytfeed-launch

The pre-packaging launcher, kept for the terminal: starts a venv server on 8040 only if nothing
answers there, then opens the browser (`open` or `xdg-open`).
