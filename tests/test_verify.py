from yt_tutor.verify import extract_timestamps


def test_extracts_t_params_and_mmss_deduped():
    text = 'a link ?t=189s, a chip [3:09], 0:06 plus &t=205s and h:mm:ss 1:02:03'
    # 3:09 == 189 (dedups with ?t=189s); 0:06 == 6; 1:02:03 == 3723
    assert extract_timestamps(text) == [6, 189, 205, 3723]


def test_max_seconds_drops_out_of_range():
    assert extract_timestamps("?t=99999s and 0:30", max_seconds=600) == [30]


def test_ignores_non_timestamp_numbers():
    # "28x28" and "784" are not mm:ss and have no t= param
    assert extract_timestamps("a 28x28 grid is 784 pixels") == []
