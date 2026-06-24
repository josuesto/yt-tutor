"""Alternate vision provider: OpenAI (gpt-4o-mini class) via structured outputs."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from .. import errors
from .base import FRAME_SCHEMA, SYSTEM_PROMPT, VisionProvider


class OpenAIVision(VisionProvider):
    def __init__(self, cfg):
        if not cfg.openai_api_key:
            raise errors.DependencyMissing("OPENAI_API_KEY is not set.")
        try:
            import openai
        except ImportError as e:  # pragma: no cover
            raise errors.DependencyMissing('Install:  pip install "yt-tutor[openai]"') from e
        self._client = openai.OpenAI(api_key=cfg.openai_api_key)
        self._model = cfg.openai_vision_model

    def analyze_keyframe(self, image_path, timestamp_seconds) -> dict:
        data = base64.standard_b64encode(Path(image_path).read_bytes()).decode("ascii")
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{data}"}},
                    {"type": "text",
                     "text": f"Analyze this video frame at {timestamp_seconds} seconds."},
                ]},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "frame_analysis", "schema": FRAME_SCHEMA, "strict": True},
            },
        )
        return json.loads(resp.choices[0].message.content)
