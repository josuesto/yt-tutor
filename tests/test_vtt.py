from yt_tutor.pipeline.captions import choose_track, parse_vtt

VTT = """WEBVTT

00:00:01.000 --> 00:00:03.000
Hello world

00:00:03.000 --> 00:00:05.000
Hello world

00:00:05.000 --> 00:00:07.500
<c>Second</c> line here
"""


def test_parse_vtt_strips_tags_and_collapses_rolling_dupes():
    segs = parse_vtt(VTT)
    texts = [t for (_s, _e, t) in segs]
    assert texts == ["Hello world", "Second line here"]
    # the duplicate cue extends the prior segment's end time rather than repeating
    assert segs[0][0] == 1.0 and segs[0][1] == 5.0


def test_parse_vtt_handles_short_mmss_timestamps():
    segs = parse_vtt("WEBVTT\n\n01:02.000 --> 01:04.000\nhi\n")
    assert segs == [(62.0, 64.0, "hi")]


def test_choose_track_prefers_manual_english():
    info = {"subtitles": {"es": [], "en": []}, "automatic_captions": {"en": []}}
    assert choose_track(info) == ("en", False)
    info2 = {"subtitles": {}, "automatic_captions": {"fr": [], "en": []}}
    assert choose_track(info2) == ("en", True)
    assert choose_track({}) == (None, None)
