"""Small pure helpers shared across the package."""

from __future__ import annotations

import shutil

from . import errors


def parse_timestamp(value) -> float:
    """Parse '3:15' | '1:02:03' | '195' | '195.5' into seconds."""
    text = str(value).strip()
    if ":" in text:
        parts = text.split(":")
        if len(parts) > 3:
            raise ValueError(f"Bad timestamp: {value!r}")
        seconds = 0.0
        for part in parts:
            seconds = seconds * 60 + float(part)
        return seconds
    return float(text)


def format_timestamp(seconds) -> str:
    """Seconds -> 'm:ss' (or 'h:mm:ss' past an hour) for citations."""
    total = int(round(float(seconds)))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def require(tool: str, hint: str) -> None:
    """Raise DependencyMissing if an external CLI tool isn't on PATH."""
    if shutil.which(tool) is None:
        raise errors.DependencyMissing(f"`{tool}` was not found on your PATH. {hint}")
