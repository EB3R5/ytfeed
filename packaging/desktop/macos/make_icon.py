"""Produce the 1024px master PNG for ytfeed.icns.

The source is icon-1024.png next to this file (extracted from the original ytfeed.app bundle);
this just copies it so build.sh has one code path across repos.
Usage: python make_icon.py <output.png>
"""
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "icon-1024.png"
OUT = sys.argv[1] if len(sys.argv) > 1 else "icon_1024.png"
shutil.copyfile(SRC, OUT)
print("wrote", OUT)
