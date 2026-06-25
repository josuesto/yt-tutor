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


# A faithful slice of YouTube auto-caption VTT: a held top line + a new bottom
# line being typed (with <c> word-timing tags), then the completed line alone.
ROLLING = """WEBVTT
Kind: captions

00:00:00.659 --> 00:00:04.010 align:start position:0%

okay<00:00:01.199><c> frequently</c><00:00:02.159><c> asked</c><00:00:02.700><c> for</c><00:00:03.540><c> cfps</c>

00:00:04.010 --> 00:00:04.020 align:start position:0%
okay frequently asked for cfps


00:00:04.020 --> 00:00:05.390 align:start position:0%
okay frequently asked for cfps
a<00:00:04.380><c> beginner's</c><00:00:05.040><c> guide</c>

00:00:05.390 --> 00:00:05.400 align:start position:0%
a beginner's guide


00:00:05.400 --> 00:00:06.950 align:start position:0%
a beginner's guide
speaking
"""


def test_rolling_overlap_is_stripped_no_repetition():
    texts = [t for (_s, _e, t) in parse_vtt(ROLLING)]
    # each phrase appears exactly once; the held lines are not repeated
    assert texts == ["okay frequently asked for cfps", "a beginner's guide", "speaking"]
    # and the joined transcript has no doubled phrase
    joined = " ".join(texts)
    assert joined.count("a beginner's guide") == 1


def test_rolling_preserves_genuine_repeats():
    # "what's a cfp? cfp stands..." — the speaker really says "cfp" twice.
    vtt = ("WEBVTT\n\n"
           "00:00:01.000 --> 00:00:02.000\nwhat's a cfp\n\n"
           "00:00:02.000 --> 00:00:04.000\nwhat's a cfp\ncfp stands for proposal\n")
    texts = [t for (_s, _e, t) in parse_vtt(vtt)]
    assert texts == ["what's a cfp", "cfp stands for proposal"]
    assert " ".join(texts) == "what's a cfp cfp stands for proposal"  # both cfps kept


def test_manual_subs_not_over_stripped():
    # Clean manual subtitles: a coincidental one-word boundary must NOT be merged away.
    vtt = ("WEBVTT\n\n"
           "00:00:01.000 --> 00:00:02.000\nlet's go to the\n\n"
           "00:00:02.000 --> 00:00:03.000\nthe end is near\n")
    texts = [t for (_s, _e, t) in parse_vtt(vtt, rolling=False)]
    assert texts == ["let's go to the", "the end is near"]


def test_parse_vtt_handles_short_mmss_timestamps():
    segs = parse_vtt("WEBVTT\n\n01:02.000 --> 01:04.000\nhi\n")
    assert segs == [(62.0, 64.0, "hi")]


def test_choose_track_prefers_manual_english():
    info = {"subtitles": {"es": [], "en": []}, "automatic_captions": {"en": []}}
    assert choose_track(info) == ("en", False)
    info2 = {"subtitles": {}, "automatic_captions": {"fr": [], "en": []}}
    assert choose_track(info2) == ("en", True)
    assert choose_track({}) == (None, None)
