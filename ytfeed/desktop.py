"""Desktop launcher: run the ytfeed server on a free port inside a pywebview window."""

import os
import socket
import threading
import time
import urllib.request


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_up(url: str, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except OSError:
            time.sleep(0.2)
    return False


def _set_dock_icon() -> None:
    # the .app bundle execs python, so the Dock shows Python's icon unless we
    # set ours on the shared NSApplication (same instance pywebview uses)
    icon = os.environ.get("YTFEED_APP_ICON")
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
    import uvicorn
    import webview

    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(
            "ytfeed.web.app:app", host="127.0.0.1", port=port, log_level="warning"
        )
    )
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    url = f"http://127.0.0.1:{port}"
    if not _wait_until_up(url):
        server.should_exit = True
        raise SystemExit(f"ytfeed server failed to start on {url}")

    _set_dock_icon()
    webview.create_window("ytfeed", url, width=1280, height=860)
    webview.start()

    # window closed: ask uvicorn to shut down cleanly
    server.should_exit = True
    server_thread.join(timeout=10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
