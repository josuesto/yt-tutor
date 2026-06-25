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
    segments = parse_vtt(text, rolling=is_auto)
    return (segments, "youtube_captions") if segments else (None, None)


# Matches HH:MM:SS.mmm or MM:SS.mmm (hours optional).
_TS = re.compile(r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})")


def _ts(match) -> float:
    hours = int(match.group(1) or 0)
    return hours * 3600 + int(match.group(2)) * 60 + int(match.group(3)) + int(match.group(4)) / 1000


_TAIL_WORDS = 60  # how far back to look for a rolling overlap (a held line is short)


def parse_vtt(text: str, *, rolling: bool = True):
    """Parse WebVTT into [(start, end, text)].

    YouTube auto-captions *roll*: each cue repeats the previous completed line
    (the held top line) before adding the new words being typed, so cue text
    looks like "<previous line> <new line>". With ``rolling=True`` we strip, word
    by word, the longest prefix of each cue that the prior text already emitted,
    keeping only the NEW speech. Taking the *longest* overlap preserves genuine
    repeats (e.g. "what's a cfp? cfp stands for...") because the match aligns to
    the whole held line, not a stray word. ``rolling=False`` keeps the
    conservative exact-duplicate collapse for clean manual subtitles."""
    segments: list[tuple[float, float, str]] = []
    tail: list[str] = []   # recently emitted words, for overlap detection
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

        if rolling:
            new_words = _strip_overlap(tail, clean.split())
        elif segments and clean == segments[-1][2]:
            new_words = []                       # exact duplicate cue
        else:
            new_words = clean.split()

        if not new_words:                        # fully contained in prior text
            if segments:
                s, _e, t = segments[-1]
                segments[-1] = (s, end, t)       # just extend its end time
            continue

        segments.append((start, end, " ".join(new_words)))
        tail = (tail + new_words)[-_TAIL_WORDS:]
    return segments


def _strip_overlap(tail: list[str], words: list[str]) -> list[str]:
    """Drop the longest prefix of ``words`` that equals a suffix of ``tail``."""
    for k in range(min(len(tail), len(words)), 0, -1):
        if tail[-k:] == words[:k]:
            return words[k:]
    return words


def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)      # <00:00:01.000>, <c>, </c>, etc.
    return re.sub(r"\s+", " ", s).strip()
