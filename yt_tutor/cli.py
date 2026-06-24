"""yt-tutor command-line interface.

Heavy imports (pipeline, providers) are deferred into each handler so the package
imports instantly and `--help` works even before optional deps are installed.
Commands not yet built print a clear "arrives in Phase N" message.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__, config, db, errors


def _open_db():
    config.load_dotenv()
    conn = db.connect()
    db.init_db(conn)
    return conn


# --- implemented commands --------------------------------------------------

def cmd_list(args) -> int:
    conn = _open_db()
    rows = db.list_videos(conn)
    if not rows:
        print('No videos ingested yet. Try:  yt-tutor ingest "<url>" --no-vision')
        return 0
    for r in rows:
        dur = int(r["duration_seconds"] or 0)
        print(f"{r['id']:<12}  {r['status']:<10}  {dur // 60:>3}m{dur % 60:02d}  {r['title'] or ''}")
    return 0


def cmd_status(args) -> int:
    conn = _open_db()
    v = db.get_video(conn, args.video)
    if not v:
        print(f"Unknown video: {args.video}", file=sys.stderr)
        return 1
    print(f"{v['id']}  status={v['status']}  last_step={v['last_step'] or '-'}")
    if v["error"]:
        print(f"  error: {v['error']}")
    for step in db.STEPS:
        print(f"  {step:<10} {db.get_step(conn, v['id'], step) or '-'}")
    return 0


def cmd_ingest(args) -> int:
    config.load_dotenv()
    from .pipeline import runner

    pcfg = config.get_provider_config()
    if args.vision:
        vision = True
    elif args.no_vision:
        vision = False
    else:
        vision = pcfg.vision_enabled

    try:
        vid = runner.ingest(
            args.url, vision=vision, do_teach=args.teach,
            force=args.force, keyframe_threshold=args.keyframe_threshold,
        )
    except errors.YtTutorError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted - re-run `ingest` to resume from the last step.", file=sys.stderr)
        return 130

    print(f"\ningested {vid}.  Next:  yt-tutor digest {vid} --md")
    return 0


# --- placeholder until the phase lands -------------------------------------

def _todo(phase: int):
    def handler(args) -> int:
        print(f"`{args._cmd}` is not implemented yet (arrives in Phase {phase}).",
              file=sys.stderr)
        return 2
    return handler


# --- parser ----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="yt-tutor",
                                description="Teach an AI agent a YouTube video.")
    p.add_argument("--version", action="version", version=f"yt-tutor {__version__}")
    sub = p.add_subparsers(dest="command")

    # ingest
    sp = sub.add_parser("ingest", help="Download, transcribe, frame-extract, chunk, store.")
    sp.add_argument("url")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--vision", action="store_true",
                   help="Analyze keyframes with a vision model (costs money).")
    g.add_argument("--no-vision", action="store_true",
                   help="Transcript + frames only (free, no API key).")
    sp.add_argument("--teach", action="store_true",
                    help="Also register the video in a teach workspace RESOURCES.md.")
    sp.add_argument("--force", action="store_true", help="Re-run completed steps.")
    sp.add_argument("--keyframe-threshold", type=int, default=None, metavar="N",
                    help="Hamming-distance threshold for keyframe dedup "
                         "(default 10; higher = fewer frames analyzed). See docs/MANUAL.md.")
    sp.set_defaults(func=cmd_ingest, _cmd="ingest")

    # query / export commands (built in later phases)
    specs = {
        "digest": (4, "Emit the timestamped transcript + visual digest."),
        "summary": (4, "Show the detailed multimodal summary."),
        "search": (4, "FTS5 retrieval over chunks."),
        "ask": (4, "Retrieve evidence (and optionally synthesize an answer)."),
        "frames": (4, "Resolve a timestamp to keyframe image path(s)."),
        "resource": (5, "Register the video in a teach workspace RESOURCES.md."),
        "estimate": (6, "Preview the vision-pass cost before ingesting."),
    }
    for name, (phase, help_text) in specs.items():
        s = sub.add_parser(name, help=help_text)
        s.add_argument("target", metavar="video|url",
                       help="A YouTube id or URL (a URL for `estimate`).")
        if name in ("search", "ask"):
            s.add_argument("query")
        if name == "frames":
            s.add_argument("--at", required=True, help="Timestamp, e.g. 3:15 or 195.")
        if name == "digest":
            s.add_argument("--md", action="store_true")
            s.add_argument("--json", action="store_true")
        if name in ("search", "ask"):
            s.add_argument("--json", action="store_true")
        s.set_defaults(func=_todo(phase), _cmd=name)

    s = sub.add_parser("list", help="List ingested videos.")
    s.set_defaults(func=cmd_list, _cmd="list")

    s = sub.add_parser("status", help="Show ingest progress for a video.")
    s.add_argument("video")
    s.set_defaults(func=cmd_status, _cmd="status")

    return p


def _force_utf8() -> None:
    """Make stdout/stderr UTF-8 so output can never crash on a non-UTF-8 console
    (e.g. Windows cp1252). errors='replace' guarantees printing is always safe."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None) -> int:
    _force_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
