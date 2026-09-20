"""Load config.toml (falling back to config.example.toml) into a Config object."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Machine-specific paths with no sensible default. They stay None until
# config.toml sets them; code that needs one calls require_path(), which
# fails with a message naming the key instead of writing to a wrong place.
REQUIRED_PATH_KEYS = ("client_secret_path", "rag_output_dir")


class ConfigError(RuntimeError):
    """A required config value is missing or unusable."""


@dataclass
class PathsConfig:
    db_path: Path = PROJECT_ROOT / "data" / "ytfeed.db"
    client_secret_path: Path | None = None   # Google OAuth desktop-app client JSON
    token_path: Path = PROJECT_ROOT / "secrets" / "token.json"
    rag_output_dir: Path | None = None       # Obsidian vault folder transcripts go to
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


def require_path(config: Config, key: str) -> Path:
    """Return config.paths.<key>, or raise ConfigError if it was never set."""
    value = getattr(config.paths, key)
    if value is None:
        raise ConfigError(
            f"paths.{key} is not set. Set it in config.toml (see config.example.toml)."
        )
    return Path(value)


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
        if key not in paths:
            continue
        value = paths[key]
        # "" in the toml means "not set" for the machine-specific keys; without
        # this, Path("") is "." which exists and would pass file checks.
        if key in REQUIRED_PATH_KEYS and not str(value).strip():
            setattr(cfg.paths, key, None)
            continue
        setattr(cfg.paths, key, _resolve(value))

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
