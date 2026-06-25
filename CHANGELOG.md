# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [0.1.0] - 2026-06-25

First public release.

### Ingest and read
- Resumable ingest pipeline: metadata (yt-dlp), captions with a free local `faster-whisper`
  fallback, frames captured at 1 fps, perceptual-hash keyframe dedup, chunking, and a SQLite store.
- Read commands: `digest`, `summary`, `search` (SQLite FTS5), `ask` (timestamped evidence),
  `frames` (timestamp to keyframe image), and `transcript` (spoken text around a timestamp).
- Cost `estimate` for the optional headless vision pass.
- Stable per-user data directory by default (`%LOCALAPPDATA%\yt-tutor`, `~/Library/Application
  Support/yt-tutor`, or `~/.local/share/yt-tutor`); override with `YT_TUTOR_DATA_DIR`.

### Teaching and vision
- Native teaching in the skill (`SKILL.md`): the agent builds grounded HTML lessons from the
  video, one idea per lesson, citing clickable `mm:ss` links and embedding the actual keyframes,
  with no hand-off to a separate skill. (An optional `resource` / `ingest --teach` export to an
  external `teach` workspace remains.)
- Agent-provided vision is the default: `keyframes` (`--pending`, `--by-salience`), `set-vision`,
  and `rechunk` let the agent record what it sees for free. The paid provider `--vision` pass
  (Anthropic default, plus OpenAI/Gemini/Ollama) is a headless-only fallback.
- `verify` command: a one-pass check of every timestamp a lesson cites, returning the words and
  the nearest keyframe, so a whole lesson is verified in one shot.
- Per-frame edge-density `salience` score to rank content-rich keyframes ahead of near-blank ones.
- OCR'd on-screen text (`visible_text`) and `notable_details` enter the searchable chunk index,
  so a slide's own words are findable.

### Transcript quality
- YouTube auto-caption rolling overlap is stripped (the longest already-emitted prefix per cue,
  preserving genuine repeats), so transcripts, summaries, search, chunks, and lessons stay clean.
  On the sample talk this cut 298 segments to 150 with no doubled phrases.

### Docs and project
- README with a generated demo GIF (`scripts/make_demo_gif.py`), a `docs/DEMO.md` walkthrough, a
  worked example lesson under `docs/examples/`, plus design / manual / handoff docs and a `vhs`
  tape. GitHub Actions CI runs ruff + pytest across Python 3.10-3.13. Install is from GitHub
  (not on PyPI yet).
- Packaged for PyPI (valid sdist + wheel, `twine check` clean) with a Trusted-Publishing release
  workflow; see `RELEASING.md`.

[Unreleased]: https://github.com/josuesto/yt-tutor/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/josuesto/yt-tutor/releases/tag/v0.1.0
