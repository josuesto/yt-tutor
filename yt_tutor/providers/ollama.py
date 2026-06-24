"""Alternate vision provider: local Ollama (e.g. llava). Free, offline; experimental.

Uses only the stdlib (urllib) so no extra dependency is needed for the local path.
"""

from __future__ import annotations

import base64
import json
import urllib.request
from pathlib import Path

from .. import errors
from .base import SYSTEM_PROMPT, VisionProvider

_JSON_HINT = (
    " Respond with a single JSON object with keys: scene_description (string), "
    "visible_text (string array), objects (string array), people (string), "
    "screen_or_slide_summary (string), notable_details (string array)."
)


class OllamaVision(VisionProvider):
    def __init__(self, cfg):
        self._host = (cfg.ollama_host or "http://localhost:11434").rstrip("/")
        self._model = cfg.ollama_vision_model

    def analyze_keyframe(self, image_path, timestamp_seconds) -> dict:
        data = base64.standard_b64encode(Path(image_path).read_bytes()).decode("ascii")
        payload = {
            "model": self._model,
            "format": "json",
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT + _JSON_HINT},
                {"role": "user",
                 "content": f"Analyze this video frame at {timestamp_seconds} seconds.",
                 "images": [data]},
            ],
        }
        req = urllib.request.Request(
            f"{self._host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                body = json.loads(r.read().decode("utf-8"))
        except Exception as e:  # network / model missing
            raise errors.YtTutorError(f"Ollama request failed: {e}") from e
        return json.loads(body.get("message", {}).get("content") or "{}")
