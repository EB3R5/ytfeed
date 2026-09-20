#!/usr/bin/env bash
# Launch ytfeed as a native desktop window (pywebview + GTK/WebKit2).
#
# The .venv runs its own Python, so it can't see the system PyGObject (`gi`) or
# the GObject-introspection typelibs unless we point at them explicitly. Both are
# provided by python-gobject / gtk3 / webkit2gtk-4.1 (Arch) or python3-gi / gir1.2-gtk-3.0 /
# gir1.2-webkit2-4.1 (Debian).
#
# `gi` itself is exposed to the venv via .venv/.../site-packages/system-gi.pth
# (written by install.sh), which *appends* the distro site-packages to sys.path so
# the venv's own packages still win. We only need the typelib path here.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO"

for d in /usr/lib/girepository-1.0 /usr/lib/x86_64-linux-gnu/girepository-1.0; do
  [ -d "$d" ] && export GI_TYPELIB_PATH="$d${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}"
done

# WebKitGTK's DMA-BUF renderer dies with "Error 71 (Protocol error) dispatching to Wayland
# display" on Hyprland + NVIDIA; the software path is fine for this app. Harmless elsewhere.
export WEBKIT_DISABLE_DMABUF_RENDERER=1

exec ./.venv/bin/python packaging/desktop/launcher.py
