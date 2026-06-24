from yt_tutor.pipeline.chunks import build_chunks


def test_chunks_group_to_target_and_snap_to_cue_boundaries():
    segs = [(i, i + 5, f"t{i}") for i in range(0, 50, 5)]  # 0..50s in 5s cues
    kfs = [(3, "a.jpg"), (25, "b.jpg")]
    chunks = build_chunks(segs, kfs, target_seconds=20, duration=50)

    bounds = [(c["start_seconds"], c["end_seconds"]) for c in chunks]
    assert bounds == [(0, 20), (20, 40), (40, 50)]
    assert "a.jpg" in chunks[0]["frame_paths"]
    assert "b.jpg" in chunks[1]["frame_paths"]
    assert chunks[0]["transcript_text"].startswith("t0")
    assert chunks[0]["embedding_text"]


def test_silent_video_falls_back_to_fixed_windows():
    chunks = build_chunks([], [(1, "x.jpg")], target_seconds=20, duration=30)
    assert [(c["start_seconds"], c["end_seconds"]) for c in chunks] == [(0, 20), (20, 30)]
    assert chunks[0]["transcript_text"] is None


def test_chapter_titles_enter_embedding_text():
    segs = [(0, 10, "intro words")]
    chapters = [{"title": "Overview", "start": 0, "end": 100}]
    chunks = build_chunks(segs, [], target_seconds=5, duration=10, chapters=chapters)
    assert "[Overview]" in chunks[0]["embedding_text"]


def test_keyframe_visuals_aggregate_into_chunk_and_search_text():
    segs = [(0, 20, "the speaker explains attention")]
    # keyframe 3-tuple carries its visual summary
    kfs = [(3, "a.jpg", "a slide showing a query key value diagram")]
    chunks = build_chunks(segs, kfs, target_seconds=20, duration=20)
    assert chunks[0]["visual_summary"] == "a slide showing a query key value diagram"
    # both speech and visuals land in the searchable embedding_text
    assert "attention" in chunks[0]["embedding_text"]
    assert "query key value" in chunks[0]["embedding_text"]
    # backward-compatible: 2-tuples (no vision) still work, visual_summary stays None
    plain = build_chunks(segs, [(3, "a.jpg")], target_seconds=20, duration=20)
    assert plain[0]["visual_summary"] is None
