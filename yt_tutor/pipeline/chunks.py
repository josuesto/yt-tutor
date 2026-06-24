"""Stage 5: merge transcript + frames into 15-30s chunks (the retrieval unit).

Boundary policy: accumulate caption cues until the chunk spans the target length,
then snap at the cue boundary so we never cut mid-sentence. Silent videos (no
transcript) fall back to fixed time windows so frames are still grouped."""

from __future__ import annotations

from .. import config


def build_chunks(segments, keyframes, *, target_seconds=None, duration=None, chapters=None):
    """segments: [(start, end, text)]; keyframes: [(ts, file_path)].
    Returns chunk dicts (visual_summary is filled later by the vision stage)."""
    target = target_seconds or config.chunk_target_seconds()
    chunks = []

    if segments:
        cur_start = cur_end = None
        cur_text: list[str] = []
        for start, end, text in segments:
            if cur_start is None:
                cur_start = start
            cur_end = end
            cur_text.append(text)
            if cur_end - cur_start >= target:
                chunks.append(_mk_chunk(cur_start, cur_end, cur_text))
                cur_start = cur_end = None
                cur_text = []
        if cur_text:
            chunks.append(_mk_chunk(cur_start, cur_end, cur_text))
    elif duration:
        t = 0
        while t < duration:
            chunks.append(_mk_chunk(t, min(t + target, duration), []))
            t += target

    chap = chapters or []
    for c in chunks:
        c["frame_paths"] = [fp for (ts, fp) in keyframes
                            if c["start_seconds"] <= ts < c["end_seconds"]]
        title = _chapter_for(chap, c["start_seconds"])
        parts = []
        if title:
            parts.append(f"[{title}]")
        if c["transcript_text"]:
            parts.append(c["transcript_text"])
        c["visual_summary"] = None
        c["embedding_text"] = " ".join(parts).strip() or None
    return chunks


def _mk_chunk(start, end, text_parts):
    text = " ".join(tp.strip() for tp in text_parts if tp).strip()
    return {"start_seconds": start, "end_seconds": end, "transcript_text": text or None}


def _chapter_for(chapters, ts):
    for c in chapters:
        s, e = c.get("start"), c.get("end")
        if s is not None and e is not None and s <= ts < e:
            return c.get("title")
    return None
