"""yt-tutor command-line interface.

Heavy imports (pipeline, qa, providers) are deferred into each handler so the
package imports instantly and `--help` works before optional deps are installed.
Commands not yet built print a clear "arrives in Phase N" message.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from . import __version__, config, db, errors


def _open_db():
    config.load_dotenv()
    conn = db.connect()
    db.init_db(conn)
    return conn


def _resolve(conn, target: str) -> str:
    """Resolve a YouTube id or URL to an ingested video id, or exit with guidance."""
    if db.get_video(conn, target):
        return target
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/embed/)([A-Za-z0-9_-]{11})", target or "")
    vid = m.group(1) if m else (target if re.fullmatch(r"[A-Za-z0-9_-]{11}", target or "") else None)
    if vid and db.get_video(conn, vid):
        return vid
    print(f"error: '{target}' is not ingested yet. Run:  yt-tutor ingest \"{target}\"",
          file=sys.stderr)
    raise SystemExit(1)


# --- library / status ------------------------------------------------------

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


# --- ingest ----------------------------------------------------------------

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


# --- read layer (Phase 4) --------------------------------------------------

def cmd_digest(args) -> int:
    conn = _open_db()
    vid = _resolve(conn, args.target)
    from .qa import digest as digest_mod
    d = digest_mod.build_digest(conn, vid)
    if args.json:
        print(digest_mod.render_json(d))
    else:
        md = digest_mod.render_markdown(d)
        print(md)
        path = digest_mod.write_digest_file(vid, md)
        print(f"\n(saved to {path})", file=sys.stderr)
    return 0


def cmd_summary(args) -> int:
    conn = _open_db()
    vid = _resolve(conn, args.target)
    row = db.get_summary(conn, vid)
    if not row:
        from .pipeline import summary as summary_mod
        summary_mod.run(conn, vid)
        row = db.get_summary(conn, vid)
    print(row["detailed_md"] if row else "(no summary available)")
    return 0


def cmd_search(args) -> int:
    conn = _open_db()
    vid = _resolve(conn, args.target)
    from .qa import search as search_mod
    results = search_mod.search(conn, vid, args.query, top_k=args.top_k)
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0
    if not results:
        print("(no matches)")
        return 0
    from .util import format_timestamp
    for r in results:
        print(f"[{format_timestamp(r['start_seconds'])}] {r['snippet']}")
    return 0


def cmd_ask(args) -> int:
    conn = _open_db()
    vid = _resolve(conn, args.target)
    from .qa import ask as ask_mod
    ev = ask_mod.gather_evidence(conn, vid, args.query, top_k=args.top_k)
    if args.json:
        print(json.dumps(ev, indent=2, ensure_ascii=False))
    else:
        print(ask_mod.render_markdown(ev))
    return 0


def cmd_frames(args) -> int:
    conn = _open_db()
    vid = _resolve(conn, args.target)
    from .util import format_timestamp, parse_timestamp
    ts = int(round(parse_timestamp(args.at)))
    window = args.window
    rows = conn.execute(
        """SELECT timestamp_seconds, file_path, is_keyframe, duplicate_of FROM frames
           WHERE video_id=? AND timestamp_seconds BETWEEN ? AND ?
           ORDER BY timestamp_seconds""",
        (vid, ts - window, ts + window)).fetchall()
    if not rows:
        print(f"(no frames near {format_timestamp(ts)})")
        return 1
    for r in rows:
        # a duplicate frame points at the keyframe that represents its scene
        repr_ts = r["timestamp_seconds"] if r["is_keyframe"] else r["duplicate_of"]
        tag = "keyframe" if r["is_keyframe"] else f"~scene@{format_timestamp(repr_ts or 0)}"
        print(f"[{format_timestamp(r['timestamp_seconds'])}] {tag:<16} {r['file_path']}")
    return 0


def cmd_resource(args) -> int:
    conn = _open_db()
    vid = _resolve(conn, args.target)
    from .qa import digest as digest_mod
    from . import teach_export
    # make sure the digest file the resource points at exists
    d = digest_mod.build_digest(conn, vid)
    digest_mod.write_digest_file(vid, digest_mod.render_markdown(d))
    path, added = teach_export.register_resource(conn, vid, workspace=args.workspace)
    print(f"{'registered in' if added else 'already present in'} {path}")
    return 0


def cmd_estimate(args) -> int:
    config.load_dotenv()
    from . import estimate as est
    from .util import format_timestamp
    try:
        e = est.estimate(args.target)
    except errors.YtTutorError as ex:
        print(f"error: {ex}", file=sys.stderr)
        return 1
    pcfg = config.get_provider_config()
    lo, hi = est.cost_range(e["keyframes_low"], e["keyframes_high"], pcfg.vision_provider)
    print(f"{e['title']}  ({format_timestamp(e['duration_seconds'])})")
    print(f"  1fps frames:                 {e['frames']}")
    print(f"  est. keyframes to analyze:   {e['keyframes_low']}-{e['keyframes_high']}")
    print(f"  est. vision cost ({pcfg.vision_provider}):  ${lo:.2f}-${hi:.2f}")
    print("  transcript + frames are free; this cost applies only to --vision.")
    print("  note: fast-cut/high-motion video can exceed the high end.")
    return 0


def cmd_keyframes(args) -> int:
    conn = _open_db()
    vid = _resolve(conn, args.target)
    from .util import format_timestamp
    rows = db.get_keyframes(conn, vid)
    if args.pending:
        rows = [r for r in rows if r["vision_status"] != "done"]
    if args.json:
        print(json.dumps([{
            "timestamp_seconds": r["timestamp_seconds"],
            "timestamp": format_timestamp(r["timestamp_seconds"]),
            "file_path": r["file_path"],
            "vision_status": r["vision_status"],
        } for r in rows], indent=2))
        return 0
    if not rows:
        print("(all keyframes have visual notes)" if args.pending else "(no keyframes)")
        return 0
    for r in rows:
        print(f"[{format_timestamp(r['timestamp_seconds'])}] {r['vision_status']:<8} {r['file_path']}")
    return 0


def cmd_set_vision(args) -> int:
    """Record the agent's own analysis of a keyframe. THIS is the default vision path:
    the model running the skill looks at the frame and stores what it sees."""
    conn = _open_db()
    vid = _resolve(conn, args.target)
    from pathlib import Path
    from .util import format_timestamp, parse_timestamp
    raw = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON ({e})", file=sys.stderr)
        return 1
    ts = int(round(parse_timestamp(args.at)))
    row = conn.execute(
        "SELECT id FROM frames WHERE video_id=? AND timestamp_seconds=?", (vid, ts)).fetchone()
    if not row:
        print(f"error: no frame at {format_timestamp(ts)} for {vid}", file=sys.stderr)
        return 1
    summary = (data.get("scene_description") or data.get("screen_or_slide_summary") or "").strip()
    db.update_frame_vision(
        conn, row["id"], status="done",
        scene_description=data.get("scene_description"),
        visible_text=data.get("visible_text"),
        objects=data.get("objects"),
        people=data.get("people"),
        screen_or_slide_summary=data.get("screen_or_slide_summary"),
        notable_details=data.get("notable_details"),
        vision_summary=summary,
    )
    print(f"recorded vision for {format_timestamp(ts)}")
    return 0


def cmd_rechunk(args) -> int:
    conn = _open_db()
    vid = _resolve(conn, args.target)
    from .pipeline import chunks as chunks_mod
    v = db.get_video(conn, vid)
    fts = db.has_fts5(conn)
    db.clear_chunks(conn, vid, fts=fts)
    segs = [(r["start_seconds"], r["end_seconds"], r["text"]) for r in db.get_segments(conn, vid)]
    kfs = [(r["timestamp_seconds"], r["file_path"], r["scene_description"] or r["vision_summary"])
           for r in db.get_keyframes(conn, vid)]
    chapters = json.loads(v["chapters_json"]) if v["chapters_json"] else None
    chs = chunks_mod.build_chunks(segs, kfs, duration=v["duration_seconds"], chapters=chapters)
    db.insert_chunks(conn, vid, chs, fts=fts)
    described = sum(1 for k in kfs if k[2])
    print(f"rechunked {vid}: {len(chs)} chunks ({described} keyframes have visual notes)")
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

    handlers = {
        "digest": cmd_digest, "summary": cmd_summary, "search": cmd_search,
        "ask": cmd_ask, "frames": cmd_frames, "resource": cmd_resource,
        "estimate": cmd_estimate,
    }
    specs = {
        "digest": (4, "Emit the timestamped transcript + visual digest."),
        "summary": (4, "Show the detailed structural overview."),
        "search": (4, "FTS5 retrieval over chunks."),
        "ask": (4, "Gather timestamped evidence for a question."),
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
            s.add_argument("--json", action="store_true")
            s.add_argument("--top-k", type=int, default=(8 if name == "search" else 6))
        if name == "frames":
            s.add_argument("--at", required=True, help="Timestamp, e.g. 3:15 or 195.")
            s.add_argument("--window", type=int, default=0, metavar="SEC",
                           help="Seconds around --at to include (default 0).")
        if name == "resource":
            s.add_argument("--workspace", default=None, metavar="DIR",
                           help="teach workspace dir (default: current directory).")
        if name == "digest":
            s.add_argument("--md", action="store_true", help="Markdown output (default).")
            s.add_argument("--json", action="store_true", help="Structured JSON output.")
        s.set_defaults(func=handlers.get(name, _todo(phase)), _cmd=name)

    s = sub.add_parser("list", help="List ingested videos.")
    s.set_defaults(func=cmd_list, _cmd="list")

    s = sub.add_parser("status", help="Show ingest progress for a video.")
    s.add_argument("video")
    s.set_defaults(func=cmd_status, _cmd="status")

    # --- agent-provided vision (the model running the skill IS the vision) ---
    s = sub.add_parser("keyframes", help="List keyframes (the frames worth looking at).")
    s.add_argument("target", metavar="video|url")
    s.add_argument("--pending", action="store_true", help="Only frames not yet described.")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_keyframes, _cmd="keyframes")

    s = sub.add_parser("set-vision",
                       help="Record YOUR analysis of a keyframe (agent-provided vision).")
    s.add_argument("target", metavar="video|url")
    s.add_argument("--at", required=True, help="Timestamp of the keyframe, e.g. 3:15 or 195.")
    s.add_argument("--file", help="JSON file with the frame analysis (else read stdin).")
    s.set_defaults(func=cmd_set_vision, _cmd="set-vision")

    s = sub.add_parser("rechunk",
                       help="Rebuild chunks so recorded visuals flow into digest + search.")
    s.add_argument("target", metavar="video|url")
    s.set_defaults(func=cmd_rechunk, _cmd="rechunk")

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
