"""Stage 6: a free, deterministic structural overview of the video, stored in
`summaries`. This is a skimmable scaffold (stats + chapters + timeline outline) —
the narrative "what's this about" summary is written by the agent from the digest
(or, optionally later, by a configured model). Keeping it free honors the
dumb-engine principle: no model call is required to ingest a video."""

from __future__ import annotations

import json

from .. import db
from ..util import format_timestamp


def run(conn, video_id, *, vision=False, progress=None):
    v = db.get_video(conn, video_id)
    chunks = db.get_chunks(conn, video_id)
    chapters = json.loads(v["chapters_json"]) if v["chapters_json"] else []
    total, keys = db.count_frames(conn, video_id)
    dur = format_timestamp(v["duration_seconds"] or 0)

    tl_dr = f"{v['title']} - a {dur} video by {v['channel']}."
    lines = [
        f"# Summary: {v['title']}", "", tl_dr, "",
        f"- Duration: {dur}",
        f"- Frames: {total} @1fps, {keys} keyframes",
        f"- Transcript segments: {db.count_segments(conn, video_id)}",
        f"- Chunks: {len(chunks)}",
    ]
    if chapters:
        lines.append("\n## Chapters")
        for c in chapters:
            lines.append(f"- [{format_timestamp(c.get('start') or 0)}] {c.get('title')}")
    lines.append("\n## Timeline outline")
    for c in chunks:
        text = (c["transcript_text"] or c["visual_summary"] or "").strip()
        if len(text) > 100:
            text = text[:100] + "..."
        lines.append(f"- [{format_timestamp(c['start_seconds'])}] {text}")

    detailed = "\n".join(lines)
    db.upsert_summary(conn, video_id, tl_dr, detailed)
    if progress:
        progress(f"summary: structural overview ({len(chunks)} sections)")
    return detailed
