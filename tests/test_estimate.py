from yt_tutor.estimate import cost_range, keyframe_range
from yt_tutor.pipeline.metadata import _friendly


def test_keyframe_range_scales_with_duration():
    assert keyframe_range(0) == (0, 0)
    low, high = keyframe_range(600)  # 10 minutes @1fps
    assert 0 < low < high <= 600


def test_cost_range_orders_and_local_is_free():
    lo, hi = cost_range(50, 200, "anthropic")
    assert 0 < lo < hi
    assert cost_range(50, 200, "ollama") == (0.0, 0.0)


def test_friendly_error_messages():
    assert "private" in _friendly("ERROR: Private video").lower()
    assert "age-restricted" in _friendly("Sign in to confirm your age").lower()
    assert "unavailable" in _friendly("Video unavailable").lower()
