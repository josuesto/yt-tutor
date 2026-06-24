# yt-tutor

**Turn any YouTube video into something an AI agent can be *taught* — and teach back to you.**

`yt-tutor` ingests a YouTube video into a local, timestamped knowledge store that combines
the **spoken transcript** with **what's actually shown on screen** (frames analyzed at 1
frame/second). You can then ask any agent (Claude Code, Cursor Composer, …) about the video
and get answers that **cite `mm:ss` timestamps** and tell you whether each point came from
**speech, visuals, or both**.

It's a **CLI + an agent skill**, not a web app. The Python engine does the heavy,
deterministic work (download, transcribe, frame-extract, dedupe, chunk, store). The
*teaching* is done by your agent reading the engine's output — so the default path needs
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
second), but vision runs only on **keyframes** — frames where the scene actually shifts
(perceptual-hash dedup). A 20-minute talking-head video drops from ~1,200 vision calls to a
couple hundred.

---

## Install

Requires **Python 3.10+**, **ffmpeg**, and **yt-dlp** on your PATH.

```bash
# ffmpeg:  https://ffmpeg.org/download.html   (or: winget install Gyan.FFmpeg)
git clone https://github.com/josuesto/yt-tutor && cd yt-tutor
pip install -e .                 # core (transcript-only, zero keys)
pip install -e ".[whisper]"      # + local speech-to-text fallback
pip install -e ".[anthropic]"    # + the default vision provider
pip install -e ".[all]"          # everything
```

Copy `.env.example` → `.env` and fill in keys **only if** you enable the vision pass.

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

# Optional: pre-analyze keyframes with a vision model (costs money)
yt-tutor estimate "https://youtu.be/..."     # preview the cost first
yt-tutor ingest  "https://youtu.be/..." --vision
```

---

## Commands

| Command | Purpose |
|---|---|
| `ingest <url> [--vision/--no-vision] [--teach] [--force]` | Run the full pipeline (resumable). |
| `digest <id\|url> [--md\|--json]` | Emit the timestamped transcript + visual digest. |
| `summary <id\|url>` | The detailed multimodal summary. |
| `frames <id\|url> --at <ts>` | Resolve a timestamp → keyframe image path(s). |
| `search <id\|url> "<q>" [--json]` | FTS5 retrieval over chunks (evidence for agents). |
| `ask <id\|url> "<q>" [--json]` | Retrieve evidence (and optionally synthesize an answer). |
| `resource <id\|url>` | Register the video in a `teach` workspace's `RESOURCES.md`. |
| `status <id\|url>` · `list` · `estimate <url>` | Ingest progress · library · cost preview. |

---

## Use it as an agent skill

`yt-tutor` ships a `SKILL.md` so an agent knows how to: ingest a URL, load the digest to
"know" the video, answer **with timestamps**, label **speech vs visual**, and pull keyframes
for visual questions.

**With the [`teach`](https://github.com/) skill:** `yt-tutor ingest <url> --teach` registers
the video as a trusted **Knowledge** resource in your `teach` workspace's `RESOURCES.md` and
drops the digest as grounding. Then `/teach` builds mission-grounded lessons from the video,
citing real timestamps. `yt-tutor` acquires the knowledge; `teach` does the pedagogy.

---

## Headless vision providers (optional)

Only needed for the headless `--vision` pass, when no interactive agent is present to look at
frames. With an agent (Claude Code, Cursor) the vision is the agent's own and these are unused.
Set `VISION_PROVIDER` in `.env`.

| Provider | Notes |
|---|---|
| `anthropic` *(default)* | Haiku-class vision. *A Max/Pro subscription does **not** include API access — needs a pay-per-use key.* |
| `gemini` | Cheapest; generous free tier. |
| `openai` | `gpt-4o-mini` vision; mature structured output. |
| `ollama` | Local + free (e.g. `llava`); slower, needs a decent GPU. |

---

## Troubleshooting

- **`ffmpeg not found`** — install it and ensure it's on PATH (`ffmpeg -version`).
- **`Private/age-restricted video`** — yt-tutor reports it and exits; these can't be ingested.
- **`No captions`** — install `[whisper]` to transcribe from audio, or it'll tell you none exist.
- **Ingest crashed?** — just run `ingest` again; it resumes from the last completed step and
  never re-pays for frames already analyzed.

## Roadmap

Web UI + clickable player, embeddings/hybrid retrieval, OCR-only pre-pass, playlists,
multi-video knowledge bases, background queue. See [`docs/DESIGN.md`](docs/DESIGN.md).

## License

MIT
