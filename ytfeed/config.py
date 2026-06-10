"""Load config.toml (falling back to config.example.toml) into a Config object."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class PathsConfig:
    db_path: Path = PROJECT_ROOT / "data" / "ytfeed.db"
    client_secret_path: Path = Path(
        "/Users/christian/Documents/GitHub/Archive/Obsidian-IO/Tokens/inputoutput.json"
    )
    token_path: Path = PROJECT_ROOT / "secrets" / "token.json"
    rag_output_dir: Path = Path("/Users/christian/Documents/RAG/raw")
    audio_output_dir: Path = PROJECT_ROOT / "data" / "audio"


@dataclass
class SyncConfig:
    initial_backfill: int = 50


@dataclass
class NotebookLMConfig:
    enabled: bool = True
    batch_size: int = 50
    profile: str = "default"
    delete_notebook_after_extract: bool = True


@dataclass
class DownloadConfig:
    download_audio: bool = False


@dataclass
class Config:
    paths: PathsConfig = field(default_factory=PathsConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)
    notebooklm: NotebookLMConfig = field(default_factory=NotebookLMConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)
    config_file: Path | None = None


def _resolve(value: str) -> Path:
    p = Path(value).expanduser()
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


def load_config(path: str | Path | None = None) -> Config:
    if path is not None:
        config_file = Path(path)
    else:
        config_file = PROJECT_ROOT / "config.toml"
        if not config_file.exists():
            config_file = PROJECT_ROOT / "config.example.toml"

    cfg = Config()
    if not config_file.exists():
        return cfg
    cfg.config_file = config_file

    with open(config_file, "rb") as f:
        raw = tomllib.load(f)

    paths = raw.get("paths", {})
    for key in ("db_path", "client_secret_path", "token_path", "rag_output_dir", "audio_output_dir"):
        if key in paths:
            setattr(cfg.paths, key, _resolve(paths[key]))

    sync = raw.get("sync", {})
    if "initial_backfill" in sync:
        cfg.sync.initial_backfill = int(sync["initial_backfill"])

    nlm = raw.get("notebooklm", {})
    for key in ("enabled", "batch_size", "profile", "delete_notebook_after_extract"):
        if key in nlm:
            setattr(cfg.notebooklm, key, nlm[key])

    dl = raw.get("download", {})
    if "download_audio" in dl:
        cfg.download.download_audio = bool(dl["download_audio"])

    return cfg
