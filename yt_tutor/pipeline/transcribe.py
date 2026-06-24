"""Stage 2b: free local transcription with faster-whisper (CTranslate2, CPU-capable).

Only runs when a video has no captions. faster-whisper is an optional extra
(`pip install "yt-tutor[whisper]"`); when it's absent, `available()` is False and
the runner reports that plainly instead of failing.
"""

from __future__ import annotations

from .. import config
from . import audio as audio_mod


def available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def maybe_whisper(info: dict, video_id: str):
    """Transcribe the video's audio locally. Returns [(start, end, text)] or None
    (no faster-whisper installed, no audio obtainable, or no speech detected)."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None

    cfg = config.get_provider_config()
    apath = audio_mod.ensure_audio(info, video_id)
    if apath is None:
        return None

    model = WhisperModel(cfg.whisper_model, device=cfg.whisper_device, compute_type="int8")
    segments, _info = model.transcribe(str(apath))
    out = []
    for s in segments:
        text = (s.text or "").strip()
        if text:
            out.append((float(s.start), float(s.end), text))
    return out or None
