from yt_tutor import db, teach_export


def _seed(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.init_db(conn)
    db.upsert_video(conn, id="vid", youtube_url="https://youtu.be/vid",
                    title="T", channel="C", duration_seconds=10)
    return conn


def test_register_creates_resources_with_knowledge(tmp_path):
    conn = _seed(tmp_path)
    path, added = teach_export.register_resource(conn, "vid", workspace=tmp_path)
    assert added is True
    text = path.read_text(encoding="utf-8")
    assert "## Knowledge" in text
    assert "https://youtu.be/vid" in text
    assert "[Video: T - C]" in text


def test_register_is_idempotent(tmp_path):
    conn = _seed(tmp_path)
    teach_export.register_resource(conn, "vid", workspace=tmp_path)
    path, added = teach_export.register_resource(conn, "vid", workspace=tmp_path)
    assert added is False
    assert path.read_text(encoding="utf-8").count("https://youtu.be/vid") == 1


def test_register_preserves_existing_content(tmp_path):
    conn = _seed(tmp_path)
    res = tmp_path / "RESOURCES.md"
    res.write_text("# My Topic Resources\n\n## Wisdom (Communities)\n- [r/foo](https://example.com)\n",
                   encoding="utf-8")
    teach_export.register_resource(conn, "vid", workspace=tmp_path)
    text = res.read_text(encoding="utf-8")
    assert "## Knowledge" in text       # section added
    assert "r/foo" in text              # existing content kept
    assert "https://youtu.be/vid" in text
