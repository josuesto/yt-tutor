"""FTS5 retrieval over chunks — the long-video fallback and the evidence source
for `ask`. Degrades to a LIKE scan if FTS5 isn't available in the SQLite build."""

from __future__ import annotations

import json
import re

from .. import db


def _fts_query(text: str):
    """Build a safe FTS5 query: quote each alphanumeric term and OR them together,
    so user punctuation can never produce an FTS syntax error."""
    terms = re.findall(r"[A-Za-z0-9_]+", text or "")
    if not terms:
        return None
    return " OR ".join(f'"{t}"' for t in terms)


def search(conn, video_id: str, query: str, top_k: int = 8):
    if db.has_fts5(conn):
        ftsq = _fts_query(query)
        if ftsq:
            try:
                rows = conn.execute(
                    """SELECT c.id, c.start_seconds, c.end_seconds, c.transcript_text,
                              c.visual_summary, c.frame_paths_json,
                              snippet(chunks_fts, 2, '[', ']', ' ... ', 12) AS snip
                       FROM chunks_fts f JOIN chunks c ON c.id = f.chunk_id
                       WHERE f.video_id = ? AND chunks_fts MATCH ?
                       ORDER BY bm25(chunks_fts) LIMIT ?""",
                    (video_id, ftsq, top_k)).fetchall()
                return [_fmt(r, r["snip"]) for r in rows]
            except Exception:
                pass  # fall through to LIKE
    like = f"%{query}%"
    rows = conn.execute(
        """SELECT id, start_seconds, end_seconds, transcript_text, visual_summary, frame_paths_json
           FROM chunks
           WHERE video_id=? AND (transcript_text LIKE ? OR visual_summary LIKE ?)
           ORDER BY start_seconds LIMIT ?""",
        (video_id, like, like, top_k)).fetchall()
    return [_fmt(r, (r["transcript_text"] or "")[:120]) for r in rows]


def _fmt(r, snippet):
    return {
        "chunk_id": r["id"],
        "start_seconds": r["start_seconds"],
        "end_seconds": r["end_seconds"],
        "transcript_text": r["transcript_text"],
        "visual_summary": r["visual_summary"],
        "frame_paths": json.loads(r["frame_paths_json"]) if r["frame_paths_json"] else [],
        "snippet": (snippet or "").strip(),
    }
