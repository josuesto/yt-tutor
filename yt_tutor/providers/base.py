"""Vision provider interface + the per-frame JSON contract every adapter returns."""

from __future__ import annotations

from abc import ABC, abstractmethod

# The structured analysis each keyframe produces (the spec's frame schema, minus
# timestamp_seconds which the engine fills in). Kept to the subset of JSON Schema
# that providers' structured-output modes accept (no min/max constraints).
FRAME_SCHEMA = {
    "type": "object",
    "properties": {
        "scene_description": {"type": "string"},
        "visible_text": {"type": "array", "items": {"type": "string"}},
        "objects": {"type": "array", "items": {"type": "string"}},
        "people": {"type": "string"},
        "screen_or_slide_summary": {"type": "string"},
        "notable_details": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["scene_description", "visible_text", "objects", "people",
                 "screen_or_slide_summary", "notable_details"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You analyze a single still frame from a video. Describe only what is visibly "
    "present in this frame. Transcribe any on-screen text verbatim into visible_text. "
    "List concrete objects in objects. In people, say how many people appear and what "
    "they are doing, or 'none'. If the frame is a slide, screenshot, diagram, or chart, "
    "summarize it in screen_or_slide_summary, else use an empty string. Put anything "
    "noteworthy in notable_details. Do not speculate about audio or anything outside the frame."
)


class VisionError(Exception):
    """An adapter failed to analyze a frame."""


class VisionProvider(ABC):
    @abstractmethod
    def analyze_keyframe(self, image_path, timestamp_seconds) -> dict:
        """Return a dict matching FRAME_SCHEMA for the given keyframe image."""
        raise NotImplementedError


def derive_vision_summary(result: dict) -> str:
    """A short one-line visual summary for chunk aggregation."""
    return (result.get("scene_description") or result.get("screen_or_slide_summary") or "").strip()
