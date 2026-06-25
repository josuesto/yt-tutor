# yt-tutor CLI reference

All commands accept a YouTube **id or URL**. Data lives under `./data` (override with
`YT_TUTOR_DATA_DIR`). Tuning knobs are documented in [docs/MANUAL.md](../docs/MANUAL.md).

## Ingest

### `ingest "<url>" [options]`
Download, transcribe (captions, then free local whisper), extract 1-fps frames, dedupe to
keyframes, chunk, and store. Resumable; re-running continues from the last completed step.
- `--no-vision` — transcript + frames only (free; the agent provides vision later). The default-friendly path.
- `--vision` — also run a **headless** per-keyframe vision pass (**costs money**, needs a provider key). Only for runs with no vision-capable agent present.
- `--teach` — after ingesting, register the video in the current `teach` workspace's `RESOURCES.md`.
- `--force` — re-run completed steps.
- `--keyframe-threshold N` — dedup sensitivity (default 10; higher = fewer keyframes).

## Read the video (what an agent loads to "know" it)

### `digest <id|url> [--md | --json]`
The full timestamped transcript + per-section frame index. `--md` (default) also saves
`data/videos/<id>/digest.md`. Read this to know the whole video.

### `summary <id|url>`
A free structural overview (stats, chapters, timeline outline). Built on demand.

### `search <id|url> "<terms>" [--json] [--top-k N]`
FTS5 keyword retrieval over chunks, ranked, with highlighted snippets. The long-video fallback.

### `ask <id|url> "<question>" [--json] [--top-k N]`
The most relevant timestamped evidence for a question, each labeled `speech` and/or `visual`
with frame paths. The engine returns evidence; the agent composes the cited answer.

### `frames <id|url> --at <ts> [--window SEC]`
Resolve a timestamp (`3:15`, `1:02:03`, or seconds) to keyframe image path(s) to **read**.
Duplicate frames resolve to the keyframe that represents their scene.

### `transcript <id|url> --at <ts> [--window SEC] [--json]`
Print the spoken transcript around a timestamp. The verification primitive for **spoken** claims
(the counterpart of `frames --at` for visual claims).

## Agent-provided vision (the default vision path)

The agent running the skill is the vision system: it reads keyframes itself and records what it sees.

### `keyframes <id|url> [--pending] [--by-salience] [--json]`
List the keyframes worth looking at. `--pending` = not yet described. `--by-salience` = richest
content first (each frame has a content score; near-blank transitions sink to the bottom).

### `set-vision <id|url> --at <ts> [--file <json>]`
Record the agent's own analysis of a keyframe: read the image, then store a JSON object with
`scene_description`, `visible_text[]`, `objects[]`, `people`, `screen_or_slide_summary`,
`notable_details[]`. Reads `--file` or stdin.

### `rechunk <id|url>`
Rebuild chunks so recorded visuals flow into the digest and search.

## Verify before teaching (the trust gate)

### `verify <id|url> [--lesson <file>] [--at <ts> …] [--window SEC] [--json]`
One pass: for every timestamp a lesson cites (or each `--at`), print the words spoken there and the
nearest keyframe to open. Go down the report, confirm each claim against the source, and fix the
timestamp or drop the claim for anything that does not ground.

## Optional: export to an external teach workspace

Teaching is native to this tool (see `SKILL.md`), so you do not need this. It exists only for
power users who run a separate `teach` skill and want the video registered there too.

### `resource <id|url> [--workspace DIR]`
Register the video as a `## Knowledge` entry in `<workspace>/RESOURCES.md` (default: cwd) for an
external `teach` skill. Idempotent. (`ingest --teach` runs this automatically after ingesting.)

## Library and cost

### `status <id>` · `list` · `estimate <url>`
Ingest progress for a video · all ingested videos · preview the (optional, headless) vision-pass cost.

## JSON output (for agents)

`digest`, `search`, `ask`, `keyframes`, `transcript`, and `verify` all accept `--json` and emit a
structured object to stdout, so a calling agent consumes the data without scraping text. `ask --json`:

```json
{
  "video_id": "…", "title": "…", "question": "…",
  "evidence": [
    {"start_seconds": 192, "timestamp": "3:12",
     "transcript_text": "…", "visual_summary": null,
     "frame_paths": ["…/frame_000193.jpg"],
     "has_speech": true, "has_visual": true}
  ]
}
```
