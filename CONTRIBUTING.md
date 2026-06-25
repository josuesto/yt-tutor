# Contributing to yt-tutor

Thanks for your interest. yt-tutor is small on purpose, so contributions are easy to review.

## Dev setup

Requires Python 3.10+, with `ffmpeg` and `yt-dlp` on your PATH for the ingest pipeline.

```bash
git clone https://github.com/josuesto/yt-tutor && cd yt-tutor
pip install -e ".[dev]"     # core + ruff + pytest
```

## Before you open a PR

Run the same two checks CI runs. Both must pass:

```bash
ruff check .
pytest -q
```

Add a test for any behavior you change. The suite is fast (unit-level, no network, no ffmpeg,
no model downloads), so keep it that way: stub providers and generate fixtures in-process rather
than calling out.

## The one design rule

yt-tutor is a **dumb engine driven by a smart agent**. The Python engine does no LLM reasoning on
the default path. It only downloads, transcribes, extracts frames, dedupes, chunks, and stores,
using local deterministic tools. The intelligence (teaching, answering, vision) belongs to the
agent running the skill. Keep new engine code on that side of the line: deterministic, free on the
default path, and testable. The reasoning lives in `SKILL.md`, not in `yt_tutor/`.

See [docs/DESIGN.md](docs/DESIGN.md) for the full rationale and [CLAUDE.md](CLAUDE.md) for the
day-to-day conventions.

## Dependencies

Core dependencies stay tiny so the tool installs fast. Anything heavy (a whisper model, a vision
SDK) is an opt-in extra in `pyproject.toml`, never a core dependency.

## Scope

Keep PRs small and focused. For a larger change, open an issue first so we can agree on the shape
before you build it.
