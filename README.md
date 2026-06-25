# yt-tutor

[![CI](https://github.com/josuesto/yt-tutor/actions/workflows/ci.yml/badge.svg)](https://github.com/josuesto/yt-tutor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/josuesto/yt-tutor/blob/main/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

**Turn any YouTube video into something an AI agent can be *taught*, then have it teach the video back to you.**

![yt-tutor in action: ingest a talk, ask it, read a slide, search a slide's words](https://raw.githubusercontent.com/josuesto/yt-tutor/main/docs/demo.gif)

`yt-tutor` ingests a YouTube video into a local, timestamped knowledge store that combines
the **spoken transcript** with **the frames shown on screen** (captured at 1 frame/second, then
collapsed to keyframes). For a visual question the agent **reads the relevant keyframe itself**;
nothing forces a paid vision pass. You can then ask any agent (Claude Code, Cursor Composer, and
others) about the video and get answers that **cite `mm:ss` timestamps** and tell you whether each
point came from **speech, visuals, or both**.

It's a **CLI plus an agent skill**, not a web app. The Python engine does the heavy,
deterministic work (download, transcribe, frame-extract, dedupe, chunk, store). The
*teaching* is done by your agent reading the engine's output, so the default path needs
**no API key and costs nothing** beyond local compute.

> Think "NotebookLM for a single YouTube video", but as a local tool any coding agent can drive.

---

## Why it's built this way

**Dumb engine, smart agent.** The engine never calls an LLM on the default path. It uses
only local, deterministic tools (`yt-dlp`, `ffmpeg`, `faster-whisper`, SQLite). **Vision comes
from the agent running the skill:** it reads the relevant keyframes itself, and can record what
it sees back into the store with `set-vision`. A paid per-frame vision pass (`--vision`) exists
only for *headless* runs where no vision-capable agent is present.

**Vision only on scene changes.** Frames are extracted at 1 fps (so there's a record every
second), but vision runs only on **keyframes**, the frames where the scene actually shifts
(perceptual-hash dedup). A 20-minute talking-head video drops from ~1,200 vision calls to a
couple hundred.

---

## Install

Requires **Python 3.10+** and **ffmpeg** on your PATH. `yt-dlp` is a Python dependency and
installs automatically with the package, so you do not need it on PATH separately.

Not on PyPI yet. Install straight from GitHub:

```bash
# ffmpeg:  https://ffmpeg.org/download.html   (or: winget install Gyan.FFmpeg)

# Quickest: install the CLI into its own isolated environment
pipx install "git+https://github.com/josuesto/yt-tutor"

# Or clone for development / to hack on it
git clone https://github.com/josuesto/yt-tutor && cd yt-tutor
pip install -e .                 # core (transcript-only, zero keys)
pip install -e ".[whisper]"      # + local speech-to-text fallback
pip install -e ".[anthropic]"    # + the default vision provider
pip install -e ".[all]"          # everything
```

To pull in extras with pipx, add them to the spec, for example
`pipx install "yt-tutor[whisper] @ git+https://github.com/josuesto/yt-tutor"`.

Copy `.env.example` to `.env` and fill in keys **only if** you enable the vision pass.

**Where your data lives:** by default, a stable per-user directory
(`%LOCALAPPDATA%\yt-tutor` on Windows, `~/Library/Application Support/yt-tutor` on macOS,
`~/.local/share/yt-tutor` on Linux), so one library serves you from any folder. Override it with
`YT_TUTOR_DATA_DIR` (for example, point it inside a repo while developing).

### Install as a Claude Code skill

`yt-tutor` ships a root `SKILL.md`, so linking the repo into your skills directory makes it
a `/`-invokable skill that drives the CLI for you:

```bash
ln -s "$PWD" ~/.claude/skills/yt-tutor          # macOS / Linux (from the cloned repo)
```
On Windows, copy the folder to `%USERPROFILE%\.claude\skills\yt-tutor`.

---

## Quickstart

```bash
# 1. Ingest (free, transcript + frames only)
yt-tutor ingest "https://www.youtube.com/watch?v=..." --no-vision

# 2. See the timestamped, multimodal digest (the "lesson material")
yt-tutor digest <video-id-or-url> --md

# 3. Ask about it (returns timestamped evidence; add --json for agents)
yt-tutor search <video-id-or-url> "what did they say about attention?"

# 4. Pull the exact frame shown at a moment (for visual questions)
yt-tutor frames <video-id-or-url> --at 3:15

# 5. Verify a lesson's citations against the source, in one pass, before teaching from it
yt-tutor verify <video-id-or-url> --lesson lesson.html

# Optional, headless only: pre-analyze keyframes with a paid vision model
yt-tutor estimate "https://youtu.be/..."     # preview the cost first
yt-tutor ingest  "https://youtu.be/..." --vision
```

---

## Demo

The clip at the top is generated from real session output (every line is genuine `yt-tutor`
output from the sample talk), rendered deterministically by `python scripts/make_demo_gif.py`
(Pillow only, no recorder needed). A step-by-step walkthrough with the full command output is in
[`docs/DEMO.md`](https://github.com/josuesto/yt-tutor/blob/main/docs/DEMO.md), and a complete worked
lesson is in [`docs/examples/`](https://github.com/josuesto/yt-tutor/tree/main/docs/examples). A
[`vhs`](https://github.com/charmbracelet/vhs) tape
([`docs/demo.tape`](https://github.com/josuesto/yt-tutor/blob/main/docs/demo.tape)) is also included
for a live-terminal recording.

---

## Commands

| Command | Purpose |
|---|---|
| `ingest <url> [--no-vision] [--teach] [--force]` | Run the full pipeline (resumable). |
| `digest <id\|url> [--md\|--json]` | The timestamped transcript and frame index an agent loads to know the video. |
| `summary <id\|url>` | Free structural overview (stats, chapters, timeline). |
| `search <id\|url> "<q>" [--json]` | FTS5 retrieval over chunks (long-video fallback). |
| `ask <id\|url> "<q>" [--json]` | Timestamped evidence for a question, labeled speech/visual. |
| `frames <id\|url> --at <ts>` | Resolve a timestamp to the keyframe image to read. |
| `transcript <id\|url> --at <ts>` | Spoken transcript around a moment (verify a claim). |
| `keyframes <id\|url> [--pending] [--by-salience]` | List the frames worth looking at, richest first. |
| `set-vision <id\|url> --at <ts> --file <json>` | Record the agent's own analysis of a frame. |
| `rechunk <id\|url>` | Fold recorded visuals into digest and search. |
| `verify <id\|url> --lesson <file>` | Check every timestamp a lesson cites against the source, one pass. |
| `resource <id\|url>` | Optional: export the video to a separate `teach` workspace's `RESOURCES.md`. |
| `status <id>` · `list` · `estimate <url>` | Ingest progress · library · headless-vision cost preview. |

Full reference: [`references/cli.md`](https://github.com/josuesto/yt-tutor/blob/main/references/cli.md).
Tuning knobs: [`docs/MANUAL.md`](https://github.com/josuesto/yt-tutor/blob/main/docs/MANUAL.md).

---

## Use it as an agent skill

`yt-tutor` ships a `SKILL.md`, so the whole experience is one step: **point the skill at a YouTube
link.** The agent ingests the video, loads the digest to "know" it, then either answers questions
or **teaches it**, all in one place, with no other skill and no workspace to set up.

**Teaching is built in.** When you ask to be taught, the agent builds short, dense, beautiful
lessons grounded entirely in the video: one idea each, every claim cited to a clickable `mm:ss`
moment, the actual on-screen keyframes embedded (not described), and check-questions to close the
loop. Before any lesson reaches you it runs `yt-tutor verify --lesson <file>`, a one-pass check of
every cited timestamp against the transcript and frames, so nothing is taught that the video does
not actually say or show.

> Optional: if you separately run a `teach` skill, `yt-tutor ingest <url> --teach` can also register
> the video as a Knowledge resource there. You do not need it. Teaching here is native.

---

## Headless vision providers (optional)

Only needed for the headless `--vision` pass, when no interactive agent is present to look at
frames. With an agent (Claude Code, Cursor) the vision is the agent's own and these are unused.
Set `VISION_PROVIDER` in `.env`.

| Provider | Notes |
|---|---|
| `anthropic` *(default)* | Haiku-class vision. A Max/Pro subscription does **not** include API access. It needs a pay-per-use key. |
| `gemini` | Cheapest; generous free tier. |
| `openai` | `gpt-4o-mini` vision; mature structured output. |
| `ollama` | Local and free (e.g. `llava`); slower, needs a decent GPU. |

---

## Troubleshooting

- **`ffmpeg not found`**: install it and ensure it's on PATH (`ffmpeg -version`).
- **`Private/age-restricted video`**: yt-tutor reports it and exits. These can't be ingested.
- **`No captions`**: install `[whisper]` to transcribe from audio, or it'll tell you none exist.
- **Ingest crashed?** Run `ingest` again. It resumes from the last completed step and never
  re-pays for frames already analyzed.

## Roadmap

Web UI plus clickable player, embeddings/hybrid retrieval, OCR-only pre-pass, playlists,
multi-video knowledge bases, background queue. See
[`docs/DESIGN.md`](https://github.com/josuesto/yt-tutor/blob/main/docs/DESIGN.md).
Project state and how to resume:
[`docs/HANDOFF.md`](https://github.com/josuesto/yt-tutor/blob/main/docs/HANDOFF.md).

## Contributing

Issues and pull requests are welcome. See
[CONTRIBUTING.md](https://github.com/josuesto/yt-tutor/blob/main/CONTRIBUTING.md) for dev setup and
the one design rule. Changes are logged in
[CHANGELOG.md](https://github.com/josuesto/yt-tutor/blob/main/CHANGELOG.md).

## License

Released under the [MIT License](https://github.com/josuesto/yt-tutor/blob/main/LICENSE).
