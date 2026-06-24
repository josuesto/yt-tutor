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
- **You are the vision.** When a question needs the picture, look at the frame yourself
  (read the image file). The engine never needs a paid vision model for this. A `--vision`
  flag exists only for *headless* runs where no vision-capable agent is present.

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

### Choose how to learn it (ask once the digest is loaded)

Ask the user, as a **single-select** question, how they want to engage with the video:

- **Talk about it here** (default) — stay in this agent: ask anything and get answers with
  `mm:ss` citations, pulling frames as needed. Best for exploring, summarizing, spot questions.
- **Teach it to me** — hand off to the `/teach` skill, which builds mission-grounded lessons
  from the video over time (step 4). Best when the goal is to genuinely learn the topic.

Honor the answer. If the user has no preference, default to talking here, and offer `/teach`
again the moment the conversation turns into wanting to actually learn the material. Do not
force `/teach`: a quick question should never require setting up a lesson workspace.

### 3. Answer questions — always cite timestamps
- Spoken content: `yt-tutor ask <id> "<question>" --json` returns the most relevant
  timestamped evidence, each labeled speech and/or visual. Answer using only that
  evidence and cite the mm:ss timestamps.
- Keyword lookup: `yt-tutor search <id> "<terms>"`.
- Visual questions ("what's on the slide at 3:15?"): run `yt-tutor frames <id> --at 3:15`,
  **read that image file yourself**, and answer from what you see.
- Always state whether each point came from speech, visuals, or both.

### Recording what you see (so visuals enter the digest and search)

For a one-off question, reading a single frame is enough. To teach the video with real
visual understanding, record what you see so the picture lands in the digest and is searchable:

1. `yt-tutor keyframes <id> --pending --by-salience --json` lists keyframes that have no
   description yet, richest content first (each carries a `salience` score; near-blank
   transition frames sink to the bottom and usually are not worth describing).
2. For each frame that carries meaning (a slide, diagram, scene change), **read the image**,
   then write a JSON object with: `scene_description`, `visible_text` (array; transcribe any
   on-screen text), `objects` (array), `people`, `screen_or_slide_summary`, `notable_details`
   (array).
3. Store it: `yt-tutor set-vision <id> --at <ts> --file analysis.json`.
4. When finished, `yt-tutor rechunk <id>` folds your notes into the digest and search.

You do not have to describe every frame. This produces the same enriched store the paid
`--vision` pass would, except the vision is yours and it is free.

### 4. Teaching mode — hand off to the `teach` skill
When the user wants to *learn* the video (not just ask one-off questions), register it
as grounded knowledge: run `yt-tutor ingest "<url>" --teach` (or `yt-tutor resource <id>`
after ingesting). This adds the video as a `## Knowledge` entry in the current `teach`
workspace's `RESOURCES.md`, pointing at the saved digest. Then follow the `teach` skill:
build mission-grounded lessons from the video, using its mm:ss timestamps as the cited,
trusted source (never guess content the digest doesn't contain). When a lesson covers
something shown on screen, **embed the actual keyframe image** (copy or link the file from
`frames --at`); show the diagram or slide, do not just describe it. Keep lessons dense and
grounded, not a one-paragraph stub.

## Verify every claim against the source (before teaching or answering)

This is the cardinal rule, the same one the `teach` skill enforces: never assert anything the
video does not actually contain, and never cite a timestamp you have not checked. A lesson or
answer is only as trustworthy as its citations. Before presenting any lesson, summary, or answer:

- For every **spoken** claim with a timestamp, run `yt-tutor transcript <id> --at <ts>` and confirm
  the words there actually support the claim. Move the timestamp or drop the claim if they do not.
  A number or term you assert (for example a specific count) must appear at the time you cite, not
  merely nearby.
- For every **visual** claim, run `yt-tutor frames <id> --at <ts>` and **read the image** to confirm
  what is on screen. Never describe a frame you have not opened.
- If a claim cannot be grounded in the transcript or a frame, do not make it. Say what is missing.

This applies to lessons handed to `/teach` too: verify the lesson's content against the video
before the learner sees it.

## Answer style

Cite timestamps and name the source, e.g.: "At 3:12 the speaker explains self-attention
(speech); the slide around 3:15 shows a query/key/value diagram (visual) — so it's
supported by both."

## Command reference

See [references/cli.md](references/cli.md) for the full command list, JSON output shapes,
and tuning options (keyframe threshold, vision providers, whisper).
