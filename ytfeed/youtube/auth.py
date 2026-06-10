"""OAuth2 InstalledAppFlow for the YouTube Data API (readonly)."""

from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from ytfeed.config import Config

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


def get_credentials(client_secret_path: Path, token_path: Path) -> Credentials:
    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secret_path.exists():
                raise FileNotFoundError(
                    f"OAuth client secret not found at {client_secret_path}. "
                    "Set paths.client_secret_path in config.toml."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())

    return creds


def get_youtube_client(config: Config) -> Resource:
    creds = get_credentials(
        Path(config.paths.client_secret_path), Path(config.paths.token_path)
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)
