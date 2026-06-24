"""Orchestrates the ingestion stages with resumability.

Every stage records completion in `ingest_state`; a re-run skips finished stages
(unless --force) and never re-pays for work already done. A crash mid-ingest
leaves a resumable partial. Stages not yet built (vision=Phase 3, summary=Phase 4,
teach=Phase 5) degrade with a clear message instead of failing.

Progress strings are kept ASCII-only so they render on every console codepage."""

from __future__ import annotations

from .. import config, db, errors, util
from . import captions, chunks as chunks_mod, frames, metadata


def _print(msg: str) -> None:
    print(f"  {msg}", flush=True)


def ingest(url, *, vision=False, do_teach=False, force=False,
           keyframe_threshold=None, progress=_print) -> str:
    util.require("ffmpeg", "Install ffmpeg and ensure it's on PATH (try: ffmpeg -version).")
    threshold = keyframe_threshold if keyframe_threshold is not None else config.keyframe_threshold()
    conn = db.connect()
    db.init_db(conn)

    # --- Stage 1: metadata --------------------------------------------------
    progress("metadata: fetching...")
    meta = metadata.fetch_metadata(url)
    vid = meta["id"]
    db.upsert_video(
        conn, id=vid, youtube_url=meta["youtube_url"], title=meta["title"],
        channel=meta["channel"], duration_seconds=meta["duration_seconds"],
        description=meta["description"], chapters=meta["chapters"],
    )
    db.set_step(conn, vid, "metadata", "done")
    db.set_video_status(conn, vid, "ingesting", last_step="metadata")
    dur = util.format_timestamp(meta["duration_seconds"] or 0)
    progress(f"metadata: {meta['title']!r} | {meta['channel']} | {dur}")

    info = meta["_info"]
    try:
        _transcript_stage(conn, vid, info, force, progress)
        _frames_stage(conn, vid, info, threshold, force, progress)
        _vision_stage(conn, vid, vision, force, progress)
        _chunks_stage(conn, vid, meta, force, progress)
        _summary_stage(conn, vid, vision, force, progress)

        if do_teach:
            progress("teach: handoff arrives in Phase 5 - skipping for now.")

        db.set_video_status(conn, vid, "done", last_step="chunks")
        progress("done.")
        return vid
    except errors.YtTutorError as e:
        db.set_video_status(conn, vid, "failed", error=str(e))
        raise
    except Exception as e:  # unexpected; keep the partial resumable
        db.set_video_status(conn, vid, "failed", error=f"{type(e).__name__}: {e}")
        raise


def _transcript_stage(conn, vid, info, force, progress):
    if not force and db.step_done(conn, vid, "transcript"):
        return
    progress("transcript: looking for captions (free)...")
    db.clear_transcript(conn, vid)
    segs, source = captions.fetch_captions(info, vid)
    if segs:
        db.add_transcript_segments(conn, vid, segs, source)
        progress(f"transcript: {len(segs)} caption segments ({source})")
    else:
        segs2 = None
        try:
            from . import transcribe  # Phase 2 (optional extra)
            progress("transcript: no captions - transcribing with local whisper (free)...")
            segs2 = transcribe.maybe_whisper(info, vid)
        except ImportError:
            pass
        if segs2:
            db.add_transcript_segments(conn, vid, segs2, "whisper")
            progress(f"transcript: {len(segs2)} segments (whisper, free local)")
        else:
            progress("transcript: no captions found - install `yt-tutor[whisper]` "
                     "for free local transcription.")
    db.set_step(conn, vid, "transcript", "done")
    db.set_video_status(conn, vid, "ingesting", last_step="transcript")


def _frames_stage(conn, vid, info, threshold, force, progress):
    if not force and db.step_done(conn, vid, "frames"):
        return
    progress(f"frames: downloading source + extracting 1fps (keyframe delta > {threshold})...")
    if force:
        db.clear_frames(conn, vid)
    rows, _src = frames.process_frames(info, vid, threshold=threshold, fps=config.frames_fps())
    db.insert_frames(conn, rows)
    total, keys = db.count_frames(conn, vid)
    if total:
        progress(f"frames: {total} @1fps -> {keys} keyframes "
                 f"({(1 - keys / total) * 100:.0f}% deduped, {keys} to analyze)")
    else:
        progress("frames: none extracted")
    db.set_step(conn, vid, "frames", "done")
    db.set_video_status(conn, vid, "ingesting", last_step="frames")


def _vision_stage(conn, vid, vision, force, progress):
    if not vision:
        return
    try:
        from . import vision as vision_mod  # Phase 3
    except ImportError:
        progress("vision: not available yet (arrives in Phase 3) - skipping.")
        return
    if not force and db.step_done(conn, vid, "vision"):
        return
    progress("vision: analyzing keyframes...")
    vision_mod.run(conn, vid, progress=progress)
    db.set_step(conn, vid, "vision", "done")


def _chunks_stage(conn, vid, meta, force, progress):
    if not force and db.step_done(conn, vid, "chunks"):
        return
    progress("chunks: merging transcript + frames...")
    fts = db.has_fts5(conn)
    db.clear_chunks(conn, vid, fts=fts)
    segs = [(r["start_seconds"], r["end_seconds"], r["text"]) for r in db.get_segments(conn, vid)]
    kfs = [(r["timestamp_seconds"], r["file_path"]) for r in db.get_keyframes(conn, vid)]
    chs = chunks_mod.build_chunks(segs, kfs, duration=meta["duration_seconds"],
                                  chapters=meta["chapters"])
    db.insert_chunks(conn, vid, chs, fts=fts)
    progress(f"chunks: {len(chs)} merged windows")
    db.set_step(conn, vid, "chunks", "done")
    db.set_video_status(conn, vid, "ingesting", last_step="chunks")


def _summary_stage(conn, vid, vision, force, progress):
    try:
        from . import summary as summary_mod  # Phase 4
    except ImportError:
        return
    if not force and db.step_done(conn, vid, "summary"):
        return
    summary_mod.run(conn, vid, vision=vision, progress=progress)
    db.set_step(conn, vid, "summary", "done")
