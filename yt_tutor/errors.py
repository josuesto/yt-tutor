"""Typed errors. Every YtTutorError carries a message that is safe to show the user."""

from __future__ import annotations


class YtTutorError(Exception):
    """Base class for expected, user-facing failures."""


class DependencyMissing(YtTutorError):
    """A required external tool (ffmpeg, yt-dlp) or optional package is absent."""


class VideoUnavailable(YtTutorError):
    """The video is private, age-restricted, removed, or otherwise unfetchable."""


class NoTranscript(YtTutorError):
    """No captions and no available transcription fallback."""
