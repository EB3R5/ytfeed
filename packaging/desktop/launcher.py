"""Desktop window launcher — the same file in every app repo; only the CONFIG block differs.

Run by path (never imported; `packaging/` has no __init__.py on purpose so it can't shadow
the PyPI `packaging` package):

    ./.venv/bin/python packaging/desktop/launcher.py

The macOS .app (packaging/desktop/macos) and the Linux .desktop entry (packaging/desktop/linux)
both exec exactly that.

Behaviour: if PREFERRED_PORT already answers /healthz (the Docker container, or a dev server),
attach a window to it. Otherwise start uvicorn on a free port in a thread and shut it down when
the window closes. Docker owns PREFERRED_PORT in normal operation; this launcher is a window
onto it, and only becomes the server when nothing else is running.
"""

import os
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

# ---- CONFIG (the only part that differs per repo) -------------------------------------
APP_NAME = "ytfeed"
ASGI_APP = "ytfeed.web.app:app"
PREFERRED_PORT = 8040
START_PATH = "/"
WINDOW_SIZE = (1280, 860)
ICON_ENV = "YTFEED_APP_ICON"        # set by the .app's C stub to Contents/Resources/<app>.icns
ALLOW_DOWNLOADS = False            # no download links in this app
PRIVATE_MODE = True                # no login cookie to persist
LOAD_DOTENV = False                # ytfeed reads config.toml, not .env
# ----------------------------------------------------------------------------------------

REPO = Path(__file__).resolve().parents[2]
HEALTH_PATH = "/healthz"


def _up(url: str, timeout: float = 1.0) -> bool:
    try:
        urllib.request.urlopen(url + HEALTH_PATH, timeout=timeout)
        return True
    except OSError:
        return False


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_up(url: str, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _up(url):
            return True
        time.sleep(0.2)
    return False


def _set_dock_icon() -> None:
    # The .app execs python, so the Dock shows Python's icon unless we set ours on the shared
    # NSApplication (the same instance pywebview uses). No-op off macOS / without pyobjc.
    icon = os.environ.get(ICON_ENV)
    if not icon or not os.path.exists(icon):
        return
    try:
        from AppKit import NSApplication, NSImage

        img = NSImage.alloc().initWithContentsOfFile_(icon)
        if img:
            NSApplication.sharedApplication().setApplicationIconImage_(img)
    except Exception:
        pass


def main() -> int:
    os.chdir(REPO)
    sys.path.insert(0, str(REPO))          # so ASGI_APP imports when run by path
    if LOAD_DOTENV:
        try:
            from dotenv import load_dotenv
            load_dotenv(REPO / ".env")
        except ImportError:
            pass

    import webview

    server = None
    preferred = f"http://127.0.0.1:{PREFERRED_PORT}"
    if _up(preferred):
        url = preferred                    # attach to the running server (Docker / dev)
    else:
        import uvicorn

        port = _free_port()
        server = uvicorn.Server(uvicorn.Config(
            ASGI_APP, host="127.0.0.1", port=port, log_level="warning"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{port}"
        if not _wait_until_up(url):
            server.should_exit = True
            raise SystemExit(f"{APP_NAME} server failed to start on {url}")

    _set_dock_icon()
    if ALLOW_DOWNLOADS:
        webview.settings["ALLOW_DOWNLOADS"] = True
    webview.create_window(APP_NAME, url + START_PATH,
                          width=WINDOW_SIZE[0], height=WINDOW_SIZE[1])
    webview.start(private_mode=PRIVATE_MODE)

    if server is not None:                 # we started it → shut it down on window close
        server.should_exit = True
        thread.join(timeout=10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
