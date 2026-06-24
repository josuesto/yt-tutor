"""Stage 2a: YouTube captions (the free, preferred transcript source).

Prefers human-authored subtitles, falls back to auto-generated. Both are free.
If none exist, returns (None, None) and the runner tries free local whisper."""

from __future__ import annotations

import re

from .. import config, errors

_EN = ("en", "en-US", "en-GB", "en-orig")


def choose_track(info: dict):
    """Pick (lang, is_auto). Manual subs win over auto; English variants win within each."""
    subs = info.get("subtitles") or {}
    autos = info.get("automatic_captions") or {}
    for lang in _EN:
        if lang in subs:
            return lang, False
    if subs:
        return next(iter(subs)), False
    for lang in _EN:
        if lang in autos:
            return lang, True
    if autos:
        return next(iter(autos)), True
    return None, None


def fetch_captions(info: dict, video_id: str):
    """Return (segments, source) or (None, None). segments: list of (start, end, text)."""
    try:
        import yt_dlp
    except ImportError as e:  # pragma: no cover
        raise errors.DependencyMissing("yt-dlp is not installed.") from e

    lang, is_auto = choose_track(info)
    if lang is None:
        return None, None

    vdir = config.video_dir(video_id)
    vdir.mkdir(parents=True, exist_ok=True)
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "skip_download": True,
        "writesubtitles": not is_auto,
        "writeautomaticsub": is_auto,
        "subtitleslangs": [lang],
        "subtitlesformat": "vtt",
        "outtmpl": str(vdir / "%(id)s.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([info.get("webpage_url")])

    candidates = list(vdir.glob(f"*{lang}*.vtt")) or list(vdir.glob("*.vtt"))
    if not candidates:
        return None, None
    text = candidates[0].read_text(encoding="utf-8", errors="ignore")
    segments = parse_vtt(text)
    return (segments, "youtube_captions") if segments else (None, None)


# Matches HH:MM:SS.mmm or MM:SS.mmm (hours optional).
_TS = re.compile(r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})")


def _ts(match) -> float:
    hours = int(match.group(1) or 0)
    return hours * 3600 + int(match.group(2)) * 60 + int(match.group(3)) + int(match.group(4)) / 1000


def parse_vtt(text: str):
    """Parse WebVTT into [(start, end, text)], stripping inline tags and collapsing
    the rolling-duplicate lines auto-captions emit (extending the prior cue's end)."""
    segments: list[tuple[float, float, str]] = []
    last_text = None
    for block in re.split(r"\n\s*\n", text):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        timing_idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if timing_idx is None:
            continue
        stamps = list(_TS.finditer(lines[timing_idx]))
        if len(stamps) < 2:
            continue
        start, end = _ts(stamps[0]), _ts(stamps[1])
        clean = _clean(" ".join(lines[timing_idx + 1:]))
        if not clean:
            continue
        if clean == last_text:
            if segments:
                s, _e, t = segments[-1]
                segments[-1] = (s, end, t)
            continue
        segments.append((start, end, clean))
        last_text = clean
    return segments


def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)      # <00:00:01.000>, <c>, </c>, etc.
    return re.sub(r"\s+", " ", s).strip()
