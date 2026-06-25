---
name: yt-tutor
description: This skill should be used when the user shares a YouTube video (URL or video id) and wants to understand it, be taught it, summarize it, or ask questions about what was said or shown in it. It uses the local `yt-tutor` CLI to ingest the video into a timestamped transcript plus 1-fps visual keyframes, then teaches it directly as dense, cited lessons or answers questions, always citing mm:ss timestamps and distinguishing spoken content from on-screen visuals. Teaching is built in: hand it a link and it ingests, learns, and teaches the video with no other skill and no workspace setup required.
---

# yt-tutor: be taught a YouTube video

Hand this skill a YouTube link and it does the whole job: ingest the video into a
timestamped, multimodal knowledge store, then teach it to the user or answer their
questions from it, citing mm:ss timestamps and distinguishing what was *said* from
what was *shown*. The `yt-tutor` CLI does the deterministic work (download, transcript,
frames, chunking); this skill is the workflow for turning that output into accurate
teaching. **Teaching is native here** — there is no hand-off to another skill and no
workspace to set up. Giving the link is the only step the user has to take.

## Prerequisites

- `yt-tutor` installed (`pipx install "git+https://github.com/josuesto/yt-tutor"`, or clone and
  `pip install -e .`; not on PyPI yet), with `ffmpeg` and `yt-dlp` on PATH.
- Ingesting a video (transcript + frames) is **free** and needs no API key.
- **You are the vision.** When a question or a lesson needs the picture, look at the frame
  yourself (read the image file). The engine never needs a paid vision model for this. A
  `--vision` flag exists only for *headless* runs where no vision-capable agent is present.

## Workflow

### 1. Ingest the video
Run `yt-tutor ingest "<url>" --no-vision`. It is resumable — if it fails partway,
run the same command again to continue. It prints the video id; every later command
accepts either the id or the URL.

### 2. Load the video to "know" it
Run `yt-tutor digest <id> --md` and read the result. This is the full timestamped
transcript plus a per-section frame index — reading it is how the video becomes known.
For a quick orientation, run `yt-tutor summary <id>`. For very long videos that exceed
context, skip the full digest and use search/ask (step 4) instead.

### 3. Choose how to engage (ask once the digest is loaded)

Ask the user, as a **single-select** question, how they want to use the video. Both
options happen right here — neither hands off anywhere:

- **Ask about it** (default) — get answers to any question with `mm:ss` citations, pulling
  frames as needed. Best for exploring, summarizing, spot questions.
- **Be taught it** — build short, cited lessons from the video and work through them with
  the user (step 6). Best when the goal is to genuinely learn the material.

Honor the answer. Default to answering questions, and offer to teach the moment the
conversation shifts from "tell me X" to wanting to actually learn the topic. A quick
question must never require committing to a course of lessons.

### 4. Answer questions — always cite timestamps
- Spoken content: `yt-tutor ask <id> "<question>" --json` returns the most relevant
  timestamped evidence, each labeled speech and/or visual. Answer using only that
  evidence and cite the mm:ss timestamps.
- Keyword lookup: `yt-tutor search <id> "<terms>"`.
- Visual questions ("what's on the slide at 3:15?"): run `yt-tutor frames <id> --at 3:15`,
  **read that image file yourself**, and answer from what you see.
- Always state whether each point came from speech, visuals, or both. Cite moments as
  clickable links: `https://www.youtube.com/watch?v=<id>&t=<seconds>s`.

### 5. Recording what you see (so visuals enter the digest and search)

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

### 6. Teach the video (native — no hand-off, no workspace)

When the user wants to *learn* the video, teach it yourself, here. The video's digest is
your **single source of truth** — the trusted resource that grounds everything. Never teach
anything the digest does not support; if the video does not cover it, say so. This is the
same teaching method a dedicated teaching skill would use, with the video standing in as the
grounded resource and mm:ss timestamps + keyframes as the citations.

- **Aim at a goal.** Optionally ask, in one line, what the user wants out of the video, and
  aim lessons at that. If they just say "teach me," teach from the video's own structure
  (`summary` / chapters), start where they are, and stay in their zone of proximal
  development — challenged just enough. Do not force a planning ritual; keep it seamless.
- **One lesson, one idea.** A lesson teaches a single, tightly-scoped concept from the video
  and gives a quick, tangible win. Save each as a self-contained, **beautiful** HTML file at
  `data/videos/<id>/lessons/0001-<dash-case-name>.html` (increment the number each lesson).
  Tell the user the exact path and a one-line command to open it.
- **Ground every claim in the video.** Cite the mm:ss moment for each point as a clickable
  link `https://www.youtube.com/watch?v=<id>&t=<seconds>s`, and say whether it came from
  speech, visuals, or both. Citations are what make a lesson trustworthy.
- **Show, do not just tell.** When a point is something shown on screen, embed the **actual
  keyframe** (from `frames --at`): copy the image into an `assets/` folder beside the lesson
  and display it. Show the diagram or slide; never replace it with prose.
- **Be dense.** A lesson is a real lesson — several grounded sections — not a one-paragraph
  stub. Compress, but teach the thing fully.
- **Close the loop.** End each lesson with 2–5 quick check questions (in the page and/or
  asked here in chat) so the user gets immediate feedback. Remind them you are their teacher
  and can clarify anything.
- **Keep a glossary/reference.** For any topic with its own nomenclature, maintain a
  compressed reference (e.g. `data/videos/<id>/lessons/glossary.html`) and adhere to it
  across lessons. References get revisited; lessons rarely do.
- **Verify before they see it.** Run the one-pass check below on every lesson before showing
  it. A lesson with an unverified citation is not ready.

## Verify every claim against the source (do this before the learner sees anything)

This is the cardinal rule: never assert anything the video does not contain, and never cite a
timestamp you have not checked. Citations drift by seconds, so checking is not optional.

**Verify a whole lesson in one pass.** After writing a lesson (or before giving a multi-claim
answer), run:

```
yt-tutor verify <id> --lesson <path-to-lesson-file>
```

It lists every timestamp the lesson cites, with the exact words spoken at that moment and the
nearest keyframe file to open. Go straight down the report and, for each entry, confirm the
lesson's claim matches the words there; for a visual claim, open the listed keyframe and look.
A number or term you assert must appear at the time you cite, not merely nearby. Move the
timestamp, fix the wording, or drop the claim for anything that does not ground. Do this
before the learner sees the lesson.

**Ad-hoc single check** (one claim, no file): `yt-tutor transcript <id> --at <ts>` for a
spoken claim, or `yt-tutor frames <id> --at <ts>` then read the image for a visual one.

If a claim cannot be grounded in the transcript or a frame, do not make it. Say what is missing.

## Answer style

Cite timestamps and name the source, e.g.: "At 3:12 the speaker explains self-attention
(speech); the slide around 3:15 shows a query/key/value diagram (visual) — so it's
supported by both."

## Command reference

See [references/cli.md](references/cli.md) for the full command list, JSON output shapes,
and tuning options (keyframe threshold, vision providers, whisper). An optional `resource`
command can export a video into a separate `teach` workspace for power users who run one;
it is not part of this skill's flow — teaching here is native and needs no such workspace.
