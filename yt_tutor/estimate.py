"""Pre-ingest cost preview for the (opt-in) vision pass.

Transcript + frames are free, so the only thing worth previewing is how many
keyframes the vision provider would analyze and roughly what that costs. Exact
keyframe count depends on the video's content, so we give a range from a
heavy-dedup case (static slides / talking head) to a dynamic one.
"""

from __future__ import annotations

# Rough USD per analyzed keyframe (image in + small JSON out). Order-of-magnitude,
# meant for a "cents vs dollars" gut check, not billing.
_PER_KEYFRAME_USD = {
    "anthropic": 0.0020,  # claude-haiku-4-5
    "openai": 0.0010,     # gpt-4o-mini
    "gemini": 0.0004,     # gemini-2.0-flash
    "ollama": 0.0,        # local, free
}
# Fraction of 1fps frames that survive dedup as keyframes: static .. dynamic.
# Tuned for talk/lecture/screencast content. Fast-cut video (music videos, action,
# gameplay) can exceed the high end — see the caveat printed by `estimate`.
_DEDUP_LOW = 0.08
_DEDUP_HIGH = 0.50


def keyframe_range(duration_seconds) -> tuple[int, int]:
    frames = max(int(duration_seconds or 0), 0)
    if not frames:
        return 0, 0
    return int(frames * _DEDUP_LOW), max(int(frames * _DEDUP_HIGH), 1)


def cost_range(low_kf: int, high_kf: int, provider: str) -> tuple[float, float]:
    rate = _PER_KEYFRAME_USD.get((provider or "anthropic").lower(), _PER_KEYFRAME_USD["anthropic"])
    return low_kf * rate, high_kf * rate


def estimate(url: str) -> dict:
    from .pipeline import metadata
    meta = metadata.fetch_metadata(url)
    dur = meta["duration_seconds"] or 0
    low_kf, high_kf = keyframe_range(dur)
    return {
        "title": meta["title"], "channel": meta["channel"],
        "duration_seconds": dur, "frames": int(dur),
        "keyframes_low": low_kf, "keyframes_high": high_kf,
    }
