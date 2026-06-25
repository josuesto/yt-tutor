# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Native teaching inside the skill, with no hand-off to a separate `teach` skill. The agent
  builds grounded HTML lessons from the video, one idea per lesson, citing clickable `mm:ss`
  links and embedding the actual on-screen keyframes.
- `verify` command: a one-pass check of every timestamp a lesson cites, returning the words
  spoken at that moment and the nearest keyframe, so a whole lesson is verified in one shot.
- `transcript` command: prints the spoken transcript around a timestamp (the verification
  primitive for spoken claims).
- Agent-provided vision: `keyframes` (with `--pending` and `--by-salience`), `set-vision`, and
  `rechunk`, so the agent records what it sees for free instead of a paid vision pass.
- Per-frame edge-density `salience` score to rank content-rich keyframes ahead of near-blank
  transitions.

### Changed
- Vision now comes from the agent running the skill by default. The paid provider `--vision`
  pass is a headless-only fallback for runs with no vision-capable agent present.
- The `resource` / `ingest --teach` export to an external `teach` workspace is now optional and
  off the default path.
- Default data directory is now a stable per-user location (`%LOCALAPPDATA%\yt-tutor`,
  `~/Library/Application Support/yt-tutor`, or `~/.local/share/yt-tutor`) instead of `./data`
  relative to the working directory, so a global or skill install keeps one library. Override
  with `YT_TUTOR_DATA_DIR`.

### Fixed
- OCR'd on-screen text (`visible_text`) and `notable_details` now enter the searchable chunk
  index, not just a keyframe's one-line `scene_description`, so a slide's actual words are findable.
- Rolling-overlap pollution in YouTube auto-captions: each cue repeats the previous held line, so
  the parser now strips the longest already-emitted prefix per cue (preserving genuine repeats),
  instead of only collapsing exact-duplicate cues. On the sample talk this cut 298 segments to 150
  with no doubled phrases, cleaning summaries, search, chunks, and lessons.

### Docs
- Install is from GitHub (`pipx install "git+https://github.com/josuesto/yt-tutor"`); not on PyPI yet.
- Clarified that frames are *captured* at 1 fps and the agent reads keyframes on demand, rather than
  implying automatic full visual analysis.
- Added a demo GIF in the README (`docs/demo.gif`), generated deterministically from real output
  by `scripts/make_demo_gif.py` (Pillow only), plus a `docs/DEMO.md` walkthrough and a `vhs` tape.

## [0.1.0] - 2026-06-24

### Added
- Initial public release. Resumable ingest pipeline: metadata (yt-dlp), captions with a free
  local `faster-whisper` fallback, 1-fps frame extraction, perceptual-hash keyframe dedup,
  chunking, and a SQLite store.
- Read commands: `digest`, `summary`, `search` (SQLite FTS5), `ask` (timestamped evidence),
  and `frames` (timestamp to keyframe image).
- Cost `estimate` for the optional headless vision pass.
- The agent skill (`SKILL.md`) plus a CLI reference.
- Headless vision providers behind an adapter: Anthropic (default), OpenAI, Gemini, Ollama.

[Unreleased]: https://github.com/josuesto/yt-tutor/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/josuesto/yt-tutor/releases/tag/v0.1.0
