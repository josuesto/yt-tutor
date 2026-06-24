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
    fts = has_fts5(conn)
    if fts:
        conn.executescript(FTS_SCHEMA)
    conn.commit()
    return fts


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
