"""Stage 4 (opt-in, paid): analyze keyframes with a vision provider.

Resumable + cached: only keyframes still 'pending' are analyzed, so a re-run or a
crash mid-pass never re-pays for frames already done. Per-frame errors are caught
and recorded as 'failed' (the ingest continues). Non-keyframe seconds inherit their
keyframe's analysis and are marked 'reused'.
"""

from __future__ import annotations

from .. import config, db
from ..providers import derive_vision_summary, get_vision_provider


def run(conn, video_id, *, provider=None, progress=None) -> int:
    if provider is None:
        provider = get_vision_provider(config.get_provider_config())  # may raise YtTutorError

    keyframes = db.get_keyframes(conn, video_id)
    total = len(keyframes)
    done = failed = 0
    for r in keyframes:
        if r["vision_status"] == "done":
            done += 1
            continue
        try:
            result = provider.analyze_keyframe(r["file_path"], r["timestamp_seconds"])
            db.update_frame_vision(
                conn, r["id"], status="done",
                scene_description=result.get("scene_description"),
                visible_text=result.get("visible_text"),
                objects=result.get("objects"),
                people=result.get("people"),
                screen_or_slide_summary=result.get("screen_or_slide_summary"),
                notable_details=result.get("notable_details"),
                vision_summary=derive_vision_summary(result),
            )
            done += 1
        except Exception as e:  # one bad frame must not abort the whole pass
            db.update_frame_vision(conn, r["id"], status="failed")
            failed += 1
            if progress:
                progress(f"vision: frame at {r['timestamp_seconds']}s failed ({type(e).__name__})")

    db.mark_duplicates_reused(conn, video_id)
    if progress:
        tail = f", {failed} failed" if failed else ""
        progress(f"vision: {done}/{total} keyframes analyzed{tail}")
    return done
