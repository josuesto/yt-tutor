"""`ask`: gather the timestamped evidence needed to answer a question, labeling
each piece as speech and/or visual. The engine does NOT synthesize the answer —
it returns evidence so the calling agent can compose one that cites timestamps."""

from __future__ import annotations

from pathlib import Path

from .. import db
from ..util import format_timestamp
from . import search as search_mod


def gather_evidence(conn, video_id: str, query: str, top_k: int = 6) -> dict:
    v = db.get_video(conn, video_id)
    results = search_mod.search(conn, video_id, query, top_k=top_k)
    evidence = []
    for r in results:
        has_visual = bool(r["visual_summary"]) or bool(r["frame_paths"])
        evidence.append({
            "start_seconds": r["start_seconds"],
            "end_seconds": r["end_seconds"],
            "timestamp": format_timestamp(r["start_seconds"]),
            "transcript_text": r["transcript_text"],
            "visual_summary": r["visual_summary"],
            "frame_paths": r["frame_paths"],
            "has_speech": bool(r["transcript_text"]),
            "has_visual": has_visual,
        })
    return {
        "video_id": video_id,
        "title": v["title"] if v else video_id,
        "url": v["youtube_url"] if v else None,
        "question": query,
        "evidence": evidence,
    }


def render_markdown(ev: dict) -> str:
    out = [f"Evidence for: {ev['question']!r}  ({ev['title']})", ""]
    if not ev["evidence"]:
        out.append("(no matching evidence — the answer may not be in this video; say so)")
        return "\n".join(out)
    for e in ev["evidence"]:
        sources = []
        if e["has_speech"]:
            sources.append("speech")
        if e["has_visual"]:
            sources.append("visual")
        out.append(f"[{e['timestamp']}] ({'+'.join(sources) or 'frame'})")
        if e["transcript_text"]:
            out.append(f"  said:  {e['transcript_text']}")
        if e["visual_summary"]:
            out.append(f"  shown: {e['visual_summary']}")
        elif e["frame_paths"]:
            out.append(f"  frames: {', '.join(Path(p).name for p in e['frame_paths'])} "
                       f"(open to inspect visual detail)")
        out.append("")
    out.append("(Answer using only this evidence. Cite the timestamps. State whether each "
               "point came from speech, visuals, or both.)")
    return "\n".join(out)
