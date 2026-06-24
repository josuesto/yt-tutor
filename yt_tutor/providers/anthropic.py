"""Default vision provider: Anthropic Claude (Haiku-class) via the official SDK.

Uses forced tool-use to guarantee the per-frame JSON: a single tool whose
input_schema IS the frame schema, with tool_choice pinned to it, so the model
must return a structured object (returned already-parsed as block.input).
"""

from __future__ import annotations

import base64
from pathlib import Path

from .. import errors
from .base import FRAME_SCHEMA, SYSTEM_PROMPT, VisionProvider

_TOOL_NAME = "record_frame_analysis"


class AnthropicVision(VisionProvider):
    def __init__(self, cfg):
        if not cfg.anthropic_api_key:
            raise errors.DependencyMissing(
                "ANTHROPIC_API_KEY is not set. The vision pass uses the pay-per-use "
                "Anthropic API (a Max/Pro subscription does not include API access).")
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover
            raise errors.DependencyMissing(
                'Install the vision extra:  pip install "yt-tutor[anthropic]"') from e
        self._client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
        self._model = cfg.anthropic_vision_model

    def analyze_keyframe(self, image_path, timestamp_seconds) -> dict:
        data = base64.standard_b64encode(Path(image_path).read_bytes()).decode("ascii")
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[{
                "name": _TOOL_NAME,
                "description": "Record the structured analysis of the video frame.",
                "input_schema": FRAME_SCHEMA,
            }],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": "image/jpeg", "data": data}},
                    {"type": "text",
                     "text": f"Analyze this video frame captured at {timestamp_seconds} seconds."},
                ],
            }],
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == _TOOL_NAME:
                return dict(block.input)
        raise errors.YtTutorError("Anthropic vision returned no structured result.")
