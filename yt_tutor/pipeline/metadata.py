"""Stage 1: fetch video metadata via yt-dlp (as a library, not the CLI).

Returns a plain dict. The raw yt-dlp `info` is passed back under `_info` so later
stages (captions, frame download) can reuse it without a second network round-trip —
but it is never persisted (the spec forbids storing huge raw responses)."""

from __future__ import annotations

from .. import errors


def fetch_metadata(url: str) -> dict:
    try:
        import yt_dlp
    except ImportError as e:  # pragma: no cover
        raise errors.DependencyMissing(
            "yt-dlp is not installed. Run: pip install yt-dlp") from e

    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        raise errors.VideoUnavailable(_friendly(str(e))) from e

    if info is None:
        raise errors.VideoUnavailable(f"Could not fetch metadata for: {url}")
    if info.get("_type") == "playlist":
        raise errors.VideoUnavailable(
            "That's a playlist URL — pass a single video (playlists arrive in v2).")

    chapters = None
    if info.get("chapters"):
        chapters = [
            {"title": c.get("title"), "start": c.get("start_time"), "end": c.get("end_time")}
            for c in info["chapters"]
        ]

    return {
        "id": info["id"],
        "youtube_url": info.get("webpage_url", url),
        "title": info.get("title"),
        "channel": info.get("uploader") or info.get("channel"),
        "duration_seconds": int(info["duration"]) if info.get("duration") else None,
        "description": info.get("description"),
        "chapters": chapters,
        "_info": info,
    }


def _friendly(message: str) -> str:
    m = message.lower()
    if "private" in m:
        return "This video is private and can't be ingested."
    if "age" in m and "restrict" in m:
        return "This video is age-restricted and can't be ingested without sign-in."
    if "members-only" in m or "members only" in m:
        return "This is a members-only video and can't be ingested."
    if "unavailable" in m or "removed" in m or "not available" in m:
        return "This video is unavailable or has been removed."
    return f"yt-dlp could not fetch this video: {message.strip()}"
