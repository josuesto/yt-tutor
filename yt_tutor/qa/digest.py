"""The digest: a single timestamped, multimodal document an agent loads to "know"
the whole video. For videos short enough to fit a model's context, this IS the
NotebookLM-style "taught the video" payload; longer videos use `search` instead."""

from __future__ import annotations

import json
from pathlib import Path

from .. import config, db
from ..util import format_timestamp


def build_digest(conn, video_id: str) -> dict:
    v = db.get_video(conn, video_id)
    if v is None:
        raise KeyError(video_id)
    chunks = db.get_chunks(conn, video_id)
    chapters = json.loads(v["chapters_json"]) if v["chapters_json"] else []
    total, keys = db.count_frames(conn, video_id)
    items = []
    for c in chunks:
        frames = json.loads(c["frame_paths_json"]) if c["frame_paths_json"] else []
        items.append({
            "start": c["start_seconds"], "end": c["end_seconds"],
            "transcript": c["transcript_text"], "visual": c["visual_summary"],
            "frames": frames,
        })
    return {
        "id": v["id"], "title": v["title"], "channel": v["channel"],
        "url": v["youtube_url"], "duration_seconds": v["duration_seconds"],
        "description": v["description"], "chapters": chapters,
        "frame_count": total, "keyframe_count": keys, "chunks": items,
    }


def render_markdown(d: dict) -> str:
    dur = format_timestamp(d["duration_seconds"] or 0)
    out = [
        f"# {d['title']}",
        f"**Channel:** {d['channel']}  |  **Duration:** {dur}  |  **URL:** {d['url']}",
        f"**Video ID:** `{d['id']}`  |  **Frames:** {d['frame_count']} (1fps), "
        f"{d['keyframe_count']} keyframes",
    ]
    if d.get("description"):
        out.append("\n## Description\n" + " ".join(d["description"].split())[:800])
    if d["chapters"]:
        out.append("\n## Chapters")
        for c in d["chapters"]:
            out.append(f"- [{format_timestamp(c.get('start') or 0)}] {c.get('title')}")
    out.append("\n## Timeline")
    out.append("_Each entry: time range, what was **said**, what was **shown** "
               "(open the listed frame files for visual detail)._\n")
    for it in d["chunks"]:
        out.append(f"### [{format_timestamp(it['start'])}-{format_timestamp(it['end'])}]")
        if it["transcript"]:
            out.append(f"**Said:** {it['transcript']}")
        if it["visual"]:
            out.append(f"**Shown:** {it['visual']}")
        if it["frames"]:
            out.append(f"**Frames:** {', '.join(Path(p).name for p in it['frames'])}")
        out.append("")
    return "\n".join(out)


def render_json(d: dict) -> str:
    return json.dumps(d, indent=2, ensure_ascii=False)


def write_digest_file(video_id: str, markdown: str) -> Path:
    p = config.digest_path(video_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(markdown, encoding="utf-8")
    return p
