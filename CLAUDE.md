# CLAUDE.md

Conventions for any coding agent (or human) working in this repository.

## What this is

`yt-tutor` ingests a YouTube video into a local, timestamped store of transcript plus visual
keyframes, so an agent can be taught the video and teach it back, citing `mm:ss`. It ships as a
Python CLI (`yt_tutor/`) and an agent skill (`SKILL.md`).

## The one rule that governs every change

**Dumb engine, smart agent.** The Python engine must do no LLM reasoning on the default path. It
downloads, transcribes, extracts frames, dedupes, chunks, and stores, using only local
deterministic tools (`yt-dlp`, `ffmpeg`, `faster-whisper`, SQLite, Pillow). All reasoning
(teaching, answering, vision) belongs to the agent running the skill and lives in `SKILL.md`, not
in the engine. A paid vision provider exists only as a headless fallback, never on the default path.

## Layout

- `yt_tutor/` engine. `pipeline/` runs ingest stages; `qa/` builds the digest, search, and ask;
  `providers/` are the headless vision adapters; `db.py` is the SQLite store; `cli.py` is the
  argparse entry point.
- `SKILL.md` plus `references/cli.md` are the agent-facing skill.
- `docs/` holds the design spec, the implementation plan, the manual, and the handoff.
- `tests/` is the unit suite. `data/` is generated output and is gitignored; never commit it.

## Commands

```bash
pip install -e ".[dev]"     # dev setup
ruff check .                # lint (CI runs this)
pytest -q                   # test (CI runs this)
```

Run both before committing. On Windows, the dev tools live under the system interpreter; invoke it
with the `py` launcher if `python` resolves elsewhere on your PATH.

## Expectations

- Add a test for any behavior you change. Keep the suite fast: no network, no ffmpeg, no model
  downloads in tests. Stub providers and generate fixtures in-process.
- Keep core dependencies tiny. Anything heavy is an opt-in extra in `pyproject.toml`.
- Follow the existing style. Match the surrounding code's naming, comment density, and idiom.
