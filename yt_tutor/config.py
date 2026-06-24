"""Configuration: deterministic paths + provider/env settings.

No third-party dependency for env loading — a tiny `.env` parser keeps the core install
featherweight. Existing environment variables always win over `.env`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE lines from `.env` (cwd by default) into os.environ.

    Does not overwrite variables already set in the real environment.
    """
    path = path or (Path.cwd() / ".env")
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# ---- deterministic paths --------------------------------------------------

def data_dir() -> Path:
    return Path(os.environ.get("YT_TUTOR_DATA_DIR", "data")).expanduser()


def db_path() -> Path:
    return data_dir() / "watcher.db"


def video_dir(video_id: str) -> Path:
    return data_dir() / "videos" / video_id


def frames_dir(video_id: str) -> Path:
    return video_dir(video_id) / "frames"


def frame_path(video_id: str, index: int) -> Path:
    """1-based frame index -> data/videos/{id}/frames/frame_000001.jpg"""
    return frames_dir(video_id) / f"frame_{index:06d}.jpg"


def digest_path(video_id: str) -> Path:
    return video_dir(video_id) / "digest.md"


def audio_path(video_id: str) -> Path:
    return video_dir(video_id) / "audio.m4a"


# ---- provider / model config ---------------------------------------------

def _flag(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class ProviderConfig:
    vision_provider: str
    vision_enabled: bool
    anthropic_api_key: str | None
    openai_api_key: str | None
    gemini_api_key: str | None
    anthropic_vision_model: str
    openai_vision_model: str
    gemini_vision_model: str
    ollama_vision_model: str
    ollama_host: str
    whisper_model: str
    whisper_device: str


def get_provider_config() -> ProviderConfig:
    return ProviderConfig(
        vision_provider=os.environ.get("VISION_PROVIDER", "anthropic"),
        vision_enabled=_flag("VISION_ENABLED", False),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        openai_api_key=os.environ.get("OPENAI_API_KEY") or None,
        gemini_api_key=os.environ.get("GEMINI_API_KEY") or None,
        # Defaults are validated against the claude-api skill when the adapter is built.
        anthropic_vision_model=os.environ.get("ANTHROPIC_VISION_MODEL", "claude-haiku-4-5-20251001"),
        openai_vision_model=os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini"),
        gemini_vision_model=os.environ.get("GEMINI_VISION_MODEL", "gemini-2.0-flash"),
        ollama_vision_model=os.environ.get("OLLAMA_VISION_MODEL", "llava"),
        ollama_host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        whisper_model=os.environ.get("WHISPER_MODEL", "base"),
        whisper_device=os.environ.get("WHISPER_DEVICE", "cpu"),
    )
