"""Pull every timestamp a lesson cites, so the whole lesson can be checked in one pass.

Lessons cite moments two ways: as `?t=NNNs` in a YouTube link and as `mm:ss` chip text.
We collect both, de-duplicate to seconds, and (optionally) drop anything past the video's end.
"""

from __future__ import annotations

import re

_T_PARAM = re.compile(r"[?&]t=(\d+)s?\b")
_MMSS = re.compile(r"\b(\d{1,2}):([0-5]\d)(?::([0-5]\d))?\b")


def extract_timestamps(text: str, max_seconds=None) -> list[int]:
    found: set[int] = set()
    for m in _T_PARAM.finditer(text or ""):
        found.add(int(m.group(1)))
    for m in _MMSS.finditer(text or ""):
        a, b, c = int(m.group(1)), int(m.group(2)), m.group(3)
        found.add(a * 3600 + b * 60 + int(c) if c is not None else a * 60 + b)
    if max_seconds:
        found = {s for s in found if s <= max_seconds + 1}
    return sorted(found)
