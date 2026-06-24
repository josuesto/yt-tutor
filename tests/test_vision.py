from yt_tutor import db
from yt_tutor.pipeline import vision


class FakeProvider:
    def __init__(self):
        self.calls = 0

    def analyze_keyframe(self, path, ts):
        self.calls += 1
        return {
            "scene_description": f"scene at {ts}",
            "visible_text": ["HELLO"],
            "objects": ["laptop"],
            "people": "one person speaking",
            "screen_or_slide_summary": "",
            "notable_details": [],
        }


def _seed(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.init_db(conn)
    db.upsert_video(conn, id="v", youtube_url="u")
    db.insert_frames(conn, [
        {"video_id": "v", "timestamp_seconds": 0, "file_path": "a.jpg",
         "phash": "0", "is_keyframe": 1, "duplicate_of": None},
        {"video_id": "v", "timestamp_seconds": 1, "file_path": "a.jpg",
         "phash": "0", "is_keyframe": 0, "duplicate_of": 0},
        {"video_id": "v", "timestamp_seconds": 2, "file_path": "b.jpg",
         "phash": "1", "is_keyframe": 1, "duplicate_of": None},
    ])
    return conn


def test_analyzes_keyframes_only(tmp_path):
    conn = _seed(tmp_path)
    fp = FakeProvider()
    n = vision.run(conn, "v", provider=fp)
    assert n == 2 and fp.calls == 2  # only the two keyframes, never the duplicate
    kfs = db.get_keyframes(conn, "v")
    assert all(r["vision_status"] == "done" for r in kfs)
    assert kfs[0]["scene_description"].startswith("scene at")
    assert kfs[0]["vision_summary"] == "scene at 0"


def test_resumable_never_repays(tmp_path):
    conn = _seed(tmp_path)
    fp = FakeProvider()
    vision.run(conn, "v", provider=fp)
    fp.calls = 0
    vision.run(conn, "v", provider=fp)  # second pass
    assert fp.calls == 0  # everything already done


def test_duplicates_marked_reused(tmp_path):
    conn = _seed(tmp_path)
    vision.run(conn, "v", provider=FakeProvider())
    dup = [r for r in db.get_frames(conn, "v") if r["is_keyframe"] == 0][0]
    assert dup["vision_status"] == "reused"


def test_frame_failure_is_isolated(tmp_path):
    conn = _seed(tmp_path)

    class Boom:
        def analyze_keyframe(self, p, t):
            raise RuntimeError("boom")

    n = vision.run(conn, "v", provider=Boom())  # must not raise
    assert n == 0
    assert all(r["vision_status"] == "failed" for r in db.get_keyframes(conn, "v"))
