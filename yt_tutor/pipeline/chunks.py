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
        # keyframes are (ts, file_path) or (ts, file_path, visual_text)
        in_window = [kf for kf in keyframes
                     if c["start_seconds"] <= kf[0] < c["end_seconds"]]
        c["frame_paths"] = [kf[1] for kf in in_window]
        visuals = [kf[2] for kf in in_window if len(kf) > 2 and kf[2]]
        c["visual_summary"] = " ".join(v.strip() for v in visuals) or None
        title = _chapter_for(chap, c["start_seconds"])
        parts = []
        if title:
            parts.append(f"[{title}]")
        if c["transcript_text"]:
            parts.append(c["transcript_text"])
        if c["visual_summary"]:
            parts.append(c["visual_summary"])
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
