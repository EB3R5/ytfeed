"""ytfeed CLI: init-db, sync, serve, transcribe, describe."""

from __future__ import annotations

import argparse
import logging
import sys

from ytfeed.config import load_config


def cmd_init_db(args: argparse.Namespace) -> int:
    from ytfeed.db.session import init_db

    config = load_config(args.config)
    init_db(config)
    print(f"Database initialized at {config.paths.db_path}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    from sqlalchemy import select

    from ytfeed.db.models import Channel
    from ytfeed.db.session import get_session_factory, init_db
    from ytfeed.youtube.client import build_source
    from ytfeed.youtube.sync import sync_all, sync_channel_uploads

    config = load_config(args.config)
    init_db(config)
    source = build_source(config)
    factory = get_session_factory(config)
    with factory() as session:
        if args.channel:
            channel = session.scalar(
                select(Channel).where(Channel.channel_id == args.channel)
            )
            if channel is None:
                print(f"Channel {args.channel} not found in DB. Run a full sync first.")
                return 1
            count = sync_channel_uploads(
                session,
                source,
                channel,
                force_full=args.full,
                initial_backfill=config.sync.initial_backfill,
            )
            print(f"{channel.title}: {count} new videos.")
        else:
            run = sync_all(
                session, source, config, force_full=args.full, progress_cb=print
            )
            if run.error_message:
                return 1
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run(
        "ytfeed.web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def cmd_transcribe(args: argparse.Namespace) -> int:
    from ytfeed.db.session import get_session_factory, init_db
    from ytfeed.transcripts.pipeline import run_transcription_pipeline

    config = load_config(args.config)
    init_db(config)
    factory = get_session_factory(config)
    with factory() as session:
        results = run_transcription_pipeline(
            session, config, video_ids=args.video_id or None, limit=args.limit
        )
    if not results:
        print("Nothing to transcribe (queue empty).")
        return 0
    ok = sum(1 for r in results.values() if r.success)
    placeholders = sum(
        1 for r in results.values() if not r.success
    )
    print(f"Transcribed {ok}/{len(results)} videos ({placeholders} placeholder/failed).")
    return 0


def cmd_describe(args: argparse.Namespace) -> int:
    """Backfill ## Description sections into existing vault files from the DB
    (with a yt-dlp fetch for videos whose description sync never got, when
    --fetch is given). Dry-run unless --apply."""
    from pathlib import Path

    from sqlalchemy import select

    from ytfeed.db.models import Video
    from ytfeed.db.session import get_session_factory, init_db
    from ytfeed.transcripts.markdown_writer import ensure_description_section

    config = load_config(args.config)
    init_db(config)
    factory = get_session_factory(config)
    patched = no_description = missing = already = 0
    with factory() as session:
        videos = session.scalars(
            select(Video).where(Video.transcript_path.is_not(None))
        )
        for video in videos:
            path = Path(video.transcript_path)
            if not path.exists():
                missing += 1
                continue
            if not video.description and args.fetch:
                from ytfeed.metadata import ytdlp_client

                meta = ytdlp_client.fetch_video_metadata(video.video_id)
                if meta and meta.get("description"):
                    video.description = meta["description"]
            if not video.description:
                no_description += 1
                continue
            if "\n## Description\n" in path.read_text(encoding="utf-8"):
                already += 1
                continue
            patched += 1
            if args.apply:
                ensure_description_section(path, video.description)
            else:
                print(f"would add description: {path.name}")
        if args.apply:
            session.commit()
    verb = "Patched" if args.apply else "Would patch"
    print(
        f"{verb} {patched} files ({already} already have one,"
        f" {no_description} have no description, {missing} missing on disk)."
    )
    if not args.apply and patched:
        print("Re-run with --apply to write them.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ytfeed", description="Personal YouTube feed")
    parser.add_argument("--config", default=None, help="Path to config.toml")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init-db", help="Create the SQLite database and tables")
    p_init.set_defaults(func=cmd_init_db)

    p_sync = sub.add_parser("sync", help="Sync subscriptions, playlists, and uploads")
    p_sync.add_argument("--full", action="store_true", help="Ignore early-stop; walk full history")
    p_sync.add_argument("--channel", default=None, help="Sync only this channel ID")
    p_sync.set_defaults(func=cmd_sync)

    p_serve = sub.add_parser("serve", help="Run the web UI")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--reload", action="store_true")
    p_serve.set_defaults(func=cmd_serve)

    p_tr = sub.add_parser("transcribe", help="Run the transcription pipeline")
    p_tr.add_argument("--video-id", action="append", help="Specific video ID (repeatable)")
    p_tr.add_argument("--limit", type=int, default=None, help="Max queue items to process")
    p_tr.set_defaults(func=cmd_transcribe)

    p_desc = sub.add_parser(
        "describe", help="Backfill ## Description sections into existing vault files"
    )
    p_desc.add_argument(
        "--apply", action="store_true", help="Actually patch files (default: dry run)"
    )
    p_desc.add_argument(
        "--fetch", action="store_true",
        help="Use yt-dlp for videos whose description the sync never captured",
    )
    p_desc.set_defaults(func=cmd_describe)

    return parser


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
