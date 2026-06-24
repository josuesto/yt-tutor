from yt_tutor import db
from yt_tutor.qa import ask as ask_mod
from yt_tutor.qa import digest as digest_mod
from yt_tutor.qa import search as search_mod


def _seed(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    fts = db.init_db(conn)
    db.upsert_video(conn, id="vid", youtube_url="https://youtu.be/vid",
                    title="T", channel="C", duration_seconds=60)
    chunks = [
        {"start_seconds": 0, "end_seconds": 20,
         "transcript_text": "we discuss self attention and tokens",
         "visual_summary": None, "frame_paths": ["a.jpg"],
         "embedding_text": "we discuss self attention and tokens"},
        {"start_seconds": 20, "end_seconds": 40,
         "transcript_text": "now about convolution layers",
         "visual_summary": None, "frame_paths": [],
         "embedding_text": "now about convolution layers"},
    ]
    db.insert_chunks(conn, "vid", chunks, fts=fts)
    return conn


def test_search_ranks_relevant_chunk_first(tmp_path):
    conn = _seed(tmp_path)
    res = search_mod.search(conn, "vid", "attention")
    assert res
    assert res[0]["start_seconds"] == 0


def test_search_handles_punctuation_safely(tmp_path):
    conn = _seed(tmp_path)
    # punctuation/quotes must not raise an FTS syntax error
    assert search_mod.search(conn, "vid", 'what about "attention"?? :)') is not None


def test_digest_has_timestamps_and_frames(tmp_path):
    conn = _seed(tmp_path)
    d = digest_mod.build_digest(conn, "vid")
    md = digest_mod.render_markdown(d)
    assert "0:00" in md
    assert "self attention" in md
    assert d["chunks"][0]["frames"] == ["a.jpg"]


def test_ask_labels_speech_vs_visual(tmp_path):
    conn = _seed(tmp_path)
    ev = ask_mod.gather_evidence(conn, "vid", "attention")
    assert ev["evidence"]
    first = ev["evidence"][0]
    assert first["has_speech"] is True
    assert first["has_visual"] is True  # has a frame path
    md = ask_mod.render_markdown(ev)
    assert "speech" in md
