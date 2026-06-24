"""Vision provider adapters. The default path needs none of these (transcript-only);
they are imported lazily so the package installs without any model SDK."""

from __future__ import annotations

from .. import errors
from .base import (
    FRAME_SCHEMA,
    SYSTEM_PROMPT,
    VisionError,
    VisionProvider,
    derive_vision_summary,
)

__all__ = [
    "FRAME_SCHEMA", "SYSTEM_PROMPT", "VisionError", "VisionProvider",
    "derive_vision_summary", "get_vision_provider",
]


def get_vision_provider(cfg) -> VisionProvider:
    """Construct the configured vision provider. Raises a YtTutorError (e.g. missing
    key or SDK) that the runner treats as 'skip vision', never a hard crash."""
    name = (cfg.vision_provider or "anthropic").lower()
    if name == "anthropic":
        from .anthropic import AnthropicVision
        return AnthropicVision(cfg)
    if name == "openai":
        from .openai import OpenAIVision
        return OpenAIVision(cfg)
    if name == "gemini":
        from .gemini import GeminiVision
        return GeminiVision(cfg)
    if name == "ollama":
        from .ollama import OllamaVision
        return OllamaVision(cfg)
    raise errors.YtTutorError(f"Unknown VISION_PROVIDER: {cfg.vision_provider!r}")
