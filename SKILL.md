---
name: yt-tutor
description: This skill should be used when the user shares a YouTube video (URL or video id) and wants to understand it, be taught it, summarize it, or ask questions about what was said or shown in it. It uses the local `yt-tutor` CLI to ingest the video into a timestamped transcript plus 1-fps visual keyframes, then teaches it or answers questions citing mm:ss timestamps and distinguishing spoken content from on-screen visuals. It also integrates with the `teach` skill by registering a video as a grounded, citable Knowledge resource.
---

# yt-tutor: be taught a YouTube video

Use the local `yt-tutor` CLI to turn a YouTube video into a timestamped, multimodal
knowledge store, then teach it or answer questions from it. The CLI does the
deterministic work (download, transcript, frames, chunking); this skill is the
workflow for using its output to teach and to cite accurately.

## Prerequisites

- `yt-tutor` installed (`pip install yt-tutor`), with `ffmpeg` and `yt-dlp` on PATH.
- Ingesting a video (transcript + frames) is **free** and needs no API key.
- The optional `--vision` pass (per-keyframe analysis) **costs money** — ask the user
  before using it. Without it, read keyframe images directly (step 3) for visual detail.

## Workflow

### 1. Ingest the video
Run `yt-tutor ingest "<url>" --no-vision`. It is resumable — if it fails partway,
run the same command again to continue. It prints the video id; every later command
accepts either the id or the URL.

### 2. Load the video to "know" it
Run `yt-tutor digest <id> --md` and read the result. This is the full timestamped
transcript plus a per-section frame index — reading it is how the video becomes known.
For a quick orientation, run `yt-tutor summary <id>`. For very long videos that exceed
context, skip the full digest and use search/ask (step 3) instead.

### 3. Answer questions — always cite timestamps
- Spoken content: `yt-tutor ask <id> "<question>" --json` returns the most relevant
  timestamped evidence, each labeled speech and/or visual. Answer using only that
  evidence and cite the mm:ss timestamps.
- Keyword lookup: `yt-tutor search <id> "<terms>"`.
- Visual questions ("what's on the slide at 3:15?"): run `yt-tutor frames <id> --at 3:15`
  to get the keyframe image path, then **read that image file** and answer from it.
- Always state whether each point came from speech, visuals, or both.

### 4. Teaching mode — hand off to the `teach` skill
When the user wants to *learn* the video (not just ask one-off questions), register it
as grounded knowledge: run `yt-tutor ingest "<url>" --teach` (or `yt-tutor resource <id>`
after ingesting). This adds the video as a `## Knowledge` entry in the current `teach`
workspace's `RESOURCES.md`, pointing at the saved digest. Then follow the `teach` skill:
build mission-grounded lessons from the video, using its mm:ss timestamps as the cited,
trusted source (never guess content the digest doesn't contain).

## Answer style

Cite timestamps and name the source, e.g.: "At 3:12 the speaker explains self-attention
(speech); the slide around 3:15 shows a query/key/value diagram (visual) — so it's
supported by both."

## Command reference

See [references/cli.md](references/cli.md) for the full command list, JSON output shapes,
and tuning options (keyframe threshold, vision providers, whisper).
