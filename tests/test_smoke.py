"""Phase 0 smoke tests: the package imports and the schema is sound."""

from yt_tutor import db


def test_schema_and_video_roundtrip(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    fts = db.init_db(conn)
    assert isinstance(fts, bool)  # FTS5 may or may not be available; must not crash

    tables = {r["name"] for r in
              conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"videos", "transcript_segments", "frames",
            "chunks", "summaries", "ingest_state"} <= tables

    db.upsert_video(conn, id="abc123", youtube_url="https://youtu.be/abc123", title="Test")
    v = db.get_video(conn, "abc123")
    assert v["title"] == "Test"
    assert v["status"] == "ingesting"


def test_resume_ledger(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.init_db(conn)
    db.upsert_video(conn, id="vid", youtube_url="u")
    assert db.step_done(conn, "vid", "frames") is False
    db.set_step(conn, "vid", "frames", "done")
    assert db.step_done(conn, "vid", "frames") is True


def test_frame_timestamp_is_unique(tmp_path):
    import sqlite3
    conn = db.connect(tmp_path / "t.db")
    db.init_db(conn)
    db.upsert_video(conn, id="vid", youtube_url="u")
    conn.execute("INSERT INTO frames (video_id, timestamp_seconds, file_path) VALUES (?,?,?)",
                 ("vid", 1, "f1.jpg"))
    conn.commit()
    # same (video_id, timestamp) must be rejected -> idempotent extraction
    try:
        conn.execute("INSERT INTO frames (video_id, timestamp_seconds, file_path) VALUES (?,?,?)",
                     ("vid", 1, "f1-dup.jpg"))
        conn.commit()
        raised = False
    except sqlite3.IntegrityError:
        raised = True
    assert raised
