from yt_tutor.util import format_timestamp, parse_timestamp


def test_parse_timestamp_forms():
    assert parse_timestamp("195") == 195
    assert parse_timestamp("3:15") == 195
    assert parse_timestamp("1:02:03") == 3723
    assert parse_timestamp("10.5") == 10.5


def test_format_timestamp():
    assert format_timestamp(5) == "0:05"
    assert format_timestamp(195) == "3:15"
    assert format_timestamp(3723) == "1:02:03"
