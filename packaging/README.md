# Packaging targets

Everything that launches the app lives here; `app/` never changes for a new target.
`packaging/` has no `__init__.py` and is never imported — it would shadow the PyPI
`packaging` library. Scripts run the launcher by path.

**Operating model.** Unlike the other apps, ytfeed is *not* in the `homelab` compose file yet: the
server on :8000 is the one `scripts/ytfeed-launch` starts (`python -m ytfeed serve`). The `.app`
window and the Linux desktop entry attach to whatever answers `/healthz` on 8000; only when nothing
does, they start their own uvicorn on a free port and stop it when the window closes. Exactly one
process may own `data/ytfeed.db` (NotebookLM batches in flight are lost if the server is killed —
check `transcription_queue` first).

## server (venv)

```bash
python -m venv .venv && ./.venv/bin/pip install -e ".[desktop,dev]"
scripts/ytfeed-launch            # or: .venv/bin/python -m ytfeed serve
```

## docker

Build context is the repo root; the image runs uvicorn on 8000 and health-checks `/healthz`. The
image builds and serves, but everything stateful is host-side and must be mounted:

| mount | why |
|---|---|
| `config.toml` → `/app/config.toml` | paths + NotebookLM settings (`config.py` reads it next to the package) |
| `secrets/` → `/app/secrets` | `token.json` — minted on the host: `ytfeed/youtube/auth.py` runs `InstalledAppFlow`, which opens a browser |
| `data/` → `/app/data` | `ytfeed.db` (+ WAL sidecars), `audio/`, `server.log` |
| the `rag_output_dir` from `config.toml` | transcript markdown output |
| `~/.notebooklm` → `/root/.notebooklm` | the `notebooklm login` profile for transcript tier 1 |

Paths inside `config.toml` are host paths (`/Users/christian/...`), so a container needs its own
copy with container paths. Plus the one-process-per-SQLite rule above. That is why the compose
service is deferred; a Proxmox move is the natural time to decide.

```bash
docker build -f packaging/docker/Dockerfile -t ytfeed .
```

## desktop/launcher.py

Shared pywebview launcher; the CONFIG block at the top is the only per-repo difference.
`./.venv/bin/python packaging/desktop/launcher.py` needs the `desktop` extra.

## desktop/macos

`build.sh` compiles `launcher.c`, takes the icon from `icon-1024.png` via `make_icon.py`, assembles and ad-hoc signs `/Applications/ytfeed.app`. The launcher is a
compiled Mach-O, not a shell script (the previous `ytfeed.app` was a zsh script): TCC attributes Documents-folder access to the code
signature, and a zsh launcher is attributed to `/bin/zsh` and dies with EPERM reading the venv.
Approve the Documents prompt on first launch; every rebuild re-signs, so macOS asks again.
The repo path is compiled in (`launcher.c`), so it assumes `~/Documents/GitHub/ytfeed`.

## desktop/linux

Debian/Ubuntu, pywebview's GTK/WebKit2 backend. `install.sh` checks the apt packages
(`python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1`), drops `system-gi.pth` into the venv so the
system `gi` module is visible, renders `ytfeed.desktop` with this repo's path, and installs it with
`ytfeed.png` under `~/.local/share`. `run.sh` is what the entry executes. `uninstall.sh` reverses it.
