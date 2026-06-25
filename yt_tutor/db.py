"""SQLite store: schema + core CRUD. This is the single source of truth for an
ingested video. The schema is designed so every pipeline stage is idempotent and
resumable (see UNIQUE/PRIMARY KEY constraints).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import config

# --- schema ---------------------------------------------------------------

CORE_SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id               TEXT PRIMARY KEY,              -- YouTube video id (deterministic)
    youtube_url      TEXT NOT NULL,
    title            TEXT,
    channel          TEXT,
    duration_seconds INTEGER,
    description      TEXT,
    chapters_json    TEXT,                          -- JSON [{title,start,end}]
    created_at       TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'new',   -- new|ingesting|done|failed
    last_step        TEXT,
    error            TEXT
);

CREATE TABLE IF NOT EXISTS transcript_segments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id      TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    start_seconds REAL NOT NULL,
    end_seconds   REAL NOT NULL,
    text          TEXT NOT NULL,
    source        TEXT NOT NULL                     -- youtube_captions|whisper
);
CREATE INDEX IF NOT EXISTS idx_segments_video ON transcript_segments(video_id, start_seconds);

CREATE TABLE IF NOT EXISTS frames (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id                TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    timestamp_seconds       INTEGER NOT NULL,
    file_path               TEXT NOT NULL,
    phash                   TEXT,
    salience                REAL,                   -- edge-density content score 0..1
    is_keyframe             INTEGER NOT NULL DEFAULT 0,
    duplicate_of            INTEGER,                -- timestamp of the keyframe reused
    vision_status           TEXT NOT NULL DEFAULT 'pending', -- pending|done|reused|skipped|failed
    scene_description       TEXT,
    visible_text            TEXT,                   -- JSON array (OCR)
    detected_objects_json   TEXT,                   -- JSON array
    people                  TEXT,
    screen_or_slide_summary TEXT,
    notable_details_json    TEXT,                   -- JSON array
    vision_summary          TEXT,
    UNIQUE(video_id, timestamp_seconds)
);
CREATE INDEX IF NOT EXISTS idx_frames_video ON frames(video_id, timestamp_seconds);

CREATE TABLE IF NOT EXISTS chunks (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id         TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    start_seconds    REAL NOT NULL,
    end_seconds      REAL NOT NULL,
    transcript_text  TEXT,
    visual_summary   TEXT,
    frame_paths_json TEXT,                          -- JSON array of file paths
    embedding_text   TEXT                           -- text for search / future embeddings
);
CREATE INDEX IF NOT EXISTS idx_chunks_video ON chunks(video_id, start_seconds);

CREATE TABLE IF NOT EXISTS summaries (
    video_id    TEXT PRIMARY KEY REFERENCES videos(id) ON DELETE CASCADE,
    tl_dr       TEXT,
    detailed_md TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ingest_state (
    video_id   TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    step       TEXT NOT NULL,                       -- metadata|transcript|frames|vision|chunks|summary
    status     TEXT NOT NULL,                       -- pending|done|failed
    updated_at TEXT NOT NULL,
    PRIMARY KEY (video_id, step)
);
"""

# FTS5 may be unavailable in some SQLite builds; created separately + guarded.
FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    video_id UNINDEXED,
    chunk_id UNINDEXED,
    text
);
"""

STEPS = ("metadata", "transcript", "frames", "vision", "chunks", "summary")


# --- connection / init -----------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(path) if path else config.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def has_fts5(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts_probe USING fts5(x)")
        conn.execute("DROP TABLE IF EXISTS _fts_probe")
        return True
    except sqlite3.OperationalError:
        return False


def init_db(conn: sqlite3.Connection) -> bool:
    """Create the schema. Returns True if FTS5 (search) is available."""
    conn.executescript(CORE_SCHEMA)
    _ensure_columns(conn)
    fts = has_fts5(conn)
    if fts:
        conn.executescript(FTS_SCHEMA)
    conn.commit()
    return fts


def _ensure_columns(conn: sqlite3.Connection) -> None:
    """Forward-compat: add columns introduced after a DB was first created."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(frames)")}
    if "salience" not in cols:
        conn.execute("ALTER TABLE frames ADD COLUMN salience REAL")


# --- videos ----------------------------------------------------------------

def upsert_video(conn, *, id, youtube_url, title=None, channel=None,
                 duration_seconds=None, description=None, chapters=None) -> None:
    conn.execute(
        """INSERT INTO videos (id, youtube_url, title, channel, duration_seconds,
                               description, chapters_json, created_at, status)
           VALUES (?,?,?,?,?,?,?,?, 'ingesting')
           ON CONFLICT(id) DO UPDATE SET
             youtube_url      = excluded.youtube_url,
             title            = COALESCE(excluded.title, videos.title),
             channel          = COALESCE(excluded.channel, videos.channel),
             duration_seconds = COALESCE(excluded.duration_seconds, videos.duration_seconds),
             description      = COALESCE(excluded.description, videos.description),
             chapters_json    = COALESCE(excluded.chapters_json, videos.chapters_json)
        """,
        (id, youtube_url, title, channel, duration_seconds, description,
         json.dumps(chapters) if chapters is not None else None, now_iso()),
    )
    conn.commit()


def get_video(conn, video_id):
    return conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()


def list_videos(conn):
    return conn.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()


def set_video_status(conn, video_id, status, *, last_step=None, error=None) -> None:
    conn.execute(
        "UPDATE videos SET status=?, last_step=COALESCE(?, last_step), error=? WHERE id=?",
        (status, last_step, error, video_id),
    )
    conn.commit()


# --- resumability ledger ---------------------------------------------------

def set_step(conn, video_id, step, status) -> None:
    conn.execute(
        """INSERT INTO ingest_state (video_id, step, status, updated_at) VALUES (?,?,?,?)
           ON CONFLICT(video_id, step) DO UPDATE SET
             status=excluded.status, updated_at=excluded.updated_at""",
        (video_id, step, status, now_iso()),
    )
    conn.commit()


def get_step(conn, video_id, step):
    row = conn.execute(
        "SELECT status FROM ingest_state WHERE video_id=? AND step=?", (video_id, step)
    ).fetchone()
    return row["status"] if row else None


def step_done(conn, video_id, step) -> bool:
    return get_step(conn, video_id, step) == "done"


# --- transcript ------------------------------------------------------------

def clear_transcript(conn, video_id) -> None:
    conn.execute("DELETE FROM transcript_segments WHERE video_id=?", (video_id,))
    conn.commit()


def add_transcript_segments(conn, video_id, segments, source) -> None:
    """segments: iterable of (start_seconds, end_seconds, text)."""
    conn.executemany(
        """INSERT INTO transcript_segments (video_id, start_seconds, end_seconds, text, source)
           VALUES (?,?,?,?,?)""",
        [(video_id, s, e, t, source) for (s, e, t) in segments],
    )
    conn.commit()


def get_segments(conn, video_id):
    return conn.execute(
        """SELECT start_seconds, end_seconds, text, source FROM transcript_segments
           WHERE video_id=? ORDER BY start_seconds""", (video_id,)).fetchall()


def get_segments_around(conn, video_id, start, end):
    """Transcript segments overlapping the window [start, end] seconds (for verification)."""
    return conn.execute(
        """SELECT start_seconds, end_seconds, text, source FROM transcript_segments
           WHERE video_id=? AND end_seconds>=? AND start_seconds<=? ORDER BY start_seconds""",
        (video_id, start, end)).fetchall()


def count_segments(conn, video_id) -> int:
    return conn.execute(
        "SELECT COUNT(*) c FROM transcript_segments WHERE video_id=?", (video_id,)).fetchone()["c"]


# --- frames ----------------------------------------------------------------

def clear_frames(conn, video_id) -> None:
    conn.execute("DELETE FROM frames WHERE video_id=?", (video_id,))
    conn.commit()


def insert_frames(conn, rows) -> None:
    """rows: iterable of dicts with video_id, timestamp_seconds, file_path, phash,
    is_keyframe, duplicate_of. Idempotent via UNIQUE(video_id, timestamp_seconds)."""
    conn.executemany(
        """INSERT OR IGNORE INTO frames
           (video_id, timestamp_seconds, file_path, phash, salience,
            is_keyframe, duplicate_of, vision_status)
           VALUES (:video_id, :timestamp_seconds, :file_path, :phash, :salience,
                   :is_keyframe, :duplicate_of, 'pending')""",
        [{"salience": None, **r} for r in rows],  # default missing optional keys
    )
    conn.commit()


def get_frames(conn, video_id):
    return conn.execute(
        "SELECT * FROM frames WHERE video_id=? ORDER BY timestamp_seconds", (video_id,)).fetchall()


def get_keyframes(conn, video_id):
    return conn.execute(
        "SELECT * FROM frames WHERE video_id=? AND is_keyframe=1 ORDER BY timestamp_seconds",
        (video_id,)).fetchall()


def visual_texts_for_frame(row):
    """Two views of a keyframe's recorded vision, for chunk building.

    Returns (display_summary, index_text):
    - display_summary: one concise line for the digest (scene/slide summary).
    - index_text: everything searchable, including the OCR'd on-screen text
      (`visible_text`) and `notable_details`, so a slide's actual words become
      findable. This is the difference between describing a slide and indexing it.
    """
    def _val(key):
        try:
            return (row[key] or "").strip()
        except (IndexError, KeyError):
            return ""

    def _list(key):
        try:
            raw = row[key]
        except (IndexError, KeyError):
            return []
        if not raw:
            return []
        try:
            return [str(x) for x in json.loads(raw)]
        except (TypeError, ValueError):
            return []

    scene = _val("scene_description")
    slide = _val("screen_or_slide_summary")
    display = scene or slide or _val("vision_summary") or None

    parts = [p for p in (scene, slide) if p]
    visible = _list("visible_text")
    if visible:
        parts.append(" ".join(visible))
    notable = _list("notable_details_json")
    if notable:
        parts.append(" ".join(notable))
    index_text = " ".join(parts).strip() or display
    return display, index_text


def count_frames(conn, video_id):
    """Returns (total_frames, keyframes)."""
    r = conn.execute(
        "SELECT COUNT(*) c, COALESCE(SUM(is_keyframe),0) k FROM frames WHERE video_id=?",
        (video_id,)).fetchone()
    return r["c"], r["k"]


# --- chunks ----------------------------------------------------------------

def clear_chunks(conn, video_id, fts=True) -> None:
    if fts:
        try:
            conn.execute("DELETE FROM chunks_fts WHERE video_id=?", (video_id,))
        except sqlite3.OperationalError:
            pass
    conn.execute("DELETE FROM chunks WHERE video_id=?", (video_id,))
    conn.commit()


def insert_chunks(conn, video_id, chunks, fts=True) -> None:
    """chunks: iterable of dicts(start_seconds, end_seconds, transcript_text,
    visual_summary, frame_paths(list), embedding_text)."""
    for c in chunks:
        cur = conn.execute(
            """INSERT INTO chunks
               (video_id, start_seconds, end_seconds, transcript_text, visual_summary,
                frame_paths_json, embedding_text)
               VALUES (?,?,?,?,?,?,?)""",
            (video_id, c["start_seconds"], c["end_seconds"], c.get("transcript_text"),
             c.get("visual_summary"), json.dumps(c.get("frame_paths", [])), c.get("embedding_text")),
        )
        if fts and c.get("embedding_text"):
            try:
                conn.execute(
                    "INSERT INTO chunks_fts (video_id, chunk_id, text) VALUES (?,?,?)",
                    (video_id, cur.lastrowid, c["embedding_text"]))
            except sqlite3.OperationalError:
                pass
    conn.commit()


def count_chunks(conn, video_id) -> int:
    return conn.execute(
        "SELECT COUNT(*) c FROM chunks WHERE video_id=?", (video_id,)).fetchone()["c"]


def get_chunks(conn, video_id):
    return conn.execute(
        "SELECT * FROM chunks WHERE video_id=? ORDER BY start_seconds", (video_id,)).fetchall()


# --- summary ---------------------------------------------------------------

def upsert_summary(conn, video_id, tl_dr, detailed_md) -> None:
    conn.execute(
        """INSERT INTO summaries (video_id, tl_dr, detailed_md, created_at) VALUES (?,?,?,?)
           ON CONFLICT(video_id) DO UPDATE SET
             tl_dr=excluded.tl_dr, detailed_md=excluded.detailed_md, created_at=excluded.created_at""",
        (video_id, tl_dr, detailed_md, now_iso()))
    conn.commit()


def get_summary(conn, video_id):
    return conn.execute("SELECT * FROM summaries WHERE video_id=?", (video_id,)).fetchone()


# --- vision (per-keyframe) -------------------------------------------------

def update_frame_vision(conn, frame_id, *, status, scene_description=None, visible_text=None,
                        objects=None, people=None, screen_or_slide_summary=None,
                        notable_details=None, vision_summary=None) -> None:
    conn.execute(
        """UPDATE frames SET
             vision_status=?, scene_description=?, visible_text=?, detected_objects_json=?,
             people=?, screen_or_slide_summary=?, notable_details_json=?, vision_summary=?
           WHERE id=?""",
        (status, scene_description,
         json.dumps(visible_text) if visible_text is not None else None,
         json.dumps(objects) if objects is not None else None,
         people, screen_or_slide_summary,
         json.dumps(notable_details) if notable_details is not None else None,
         vision_summary, frame_id),
    )
    conn.commit()


def mark_duplicates_reused(conn, video_id) -> None:
    """Non-keyframe seconds inherit their keyframe's analysis; mark them reused."""
    conn.execute(
        """UPDATE frames SET vision_status='reused'
           WHERE video_id=? AND is_keyframe=0 AND vision_status='pending'""",
        (video_id,),
    )
    conn.commit()
