"""Alternate vision provider: Google Gemini (2.0 Flash class). Experimental."""

from __future__ import annotations

import json
from pathlib import Path

from .. import errors
from .base import FRAME_SCHEMA, SYSTEM_PROMPT, VisionProvider


class GeminiVision(VisionProvider):
    def __init__(self, cfg):
        if not cfg.gemini_api_key:
            raise errors.DependencyMissing("GEMINI_API_KEY is not set.")
        try:
            import google.generativeai as genai
        except ImportError as e:  # pragma: no cover
            raise errors.DependencyMissing('Install:  pip install "yt-tutor[gemini]"') from e
        genai.configure(api_key=cfg.gemini_api_key)
        self._genai = genai
        self._model = cfg.gemini_vision_model

    def analyze_keyframe(self, image_path, timestamp_seconds) -> dict:
        data = Path(image_path).read_bytes()
        model = self._genai.GenerativeModel(self._model, system_instruction=SYSTEM_PROMPT)
        resp = model.generate_content(
            [{"mime_type": "image/jpeg", "data": data},
             f"Analyze this video frame at {timestamp_seconds} seconds."],
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": FRAME_SCHEMA,
            },
        )
        return json.loads(resp.text)
