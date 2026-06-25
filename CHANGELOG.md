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

### Fixed
- OCR'd on-screen text (`visible_text`) and `notable_details` now enter the searchable chunk
  index, not just a keyframe's one-line `scene_description`, so a slide's actual words are findable.

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
