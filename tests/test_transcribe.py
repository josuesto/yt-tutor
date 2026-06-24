from yt_tutor.pipeline import transcribe


def test_available_returns_bool():
    # Must never raise, whether or not faster-whisper is installed.
    assert isinstance(transcribe.available(), bool)
