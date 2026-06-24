"""Stage 2b helper: obtain an audio file for whisper.

Reuses the already-downloaded source video (via ffmpeg) when present, so a
caption-less ingest doesn't download twice; otherwise grabs bestaudio with yt-dlp.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .. import config, util

_VIDEO_EXTS = (".mp4", ".mkv", ".webm", ".mov")


def _existing_audio(vdir: Path):
    return next((p for p in vdir.glob("audio.*")), None)


def ensure_audio(info: dict, video_id: str):
    """Return a Path to an audio file for transcription, or None if unobtainable."""
    vdir = config.video_dir(video_id)
    vdir.mkdir(parents=True, exist_ok=True)

    existing = _existing_audio(vdir)
    if existing:
        return existing

    # Reuse a source video already on disk (e.g. frames stage ran, or a resume).
    src = next((p for p in vdir.glob("source.*") if p.suffix.lower() in _VIDEO_EXTS), None)
    if src:
        util.require("ffmpeg", "Install ffmpeg to extract audio for transcription.")
        apath = vdir / "audio.m4a"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
             "-vn", "-q:a", "2", str(apath)],
            capture_output=True, text=True)
        if apath.exists():
            return apath

    try:
        import yt_dlp
    except ImportError:
        return None
    opts = {
        "quiet": True, "no_warnings": True, "noprogress": True,
        "format": "bestaudio/best", "outtmpl": str(vdir / "audio.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([info.get("webpage_url")])
    return _existing_audio(vdir)
