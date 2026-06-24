# yt-tutor CLI reference

All commands accept a YouTube **id or URL**. Data lives under `./data` (override with
`YT_TUTOR_DATA_DIR`). Tuning knobs are documented in [docs/MANUAL.md](../docs/MANUAL.md).

## Commands

### `ingest "<url>" [options]`
Download, transcribe (captions → free local whisper), extract 1-fps frames, dedupe to
keyframes, chunk, and store. Resumable; re-running continues from the last completed step.
- `--no-vision` — transcript + frames only (free, default-friendly).
- `--vision` — also run the per-keyframe vision pass (**costs money**, needs a provider key).
- `--teach` — after ingesting, register the video in the current `teach` workspace's `RESOURCES.md`.
- `--force` — re-run completed steps.
- `--keyframe-threshold N` — dedup sensitivity (default 10; higher = fewer keyframes).

### `digest <id|url> [--md | --json]`
Emit the full timestamped transcript + per-section frame index. `--md` (default) also
saves `data/videos/<id>/digest.md`. This is the payload to read to "know" the video.

### `summary <id|url>`
Print a free structural overview (stats, chapters, timeline outline). Built on demand.

### `search <id|url> "<terms>" [--json] [--top-k N]`
FTS5 keyword retrieval over chunks, ranked by relevance, with highlighted snippets.

### `ask <id|url> "<question>" [--json] [--top-k N]`
Return the most relevant timestamped evidence for a question, each labeled `speech`
and/or `visual` with frame paths. The engine returns evidence; the agent composes the
cited answer. `--json` gives a structured object (`{question, evidence: [...]}`).

### `frames <id|url> --at <ts> [--window SEC]`
Resolve a timestamp (`3:15`, `1:02:03`, or seconds) to keyframe image path(s). Duplicate
frames resolve to the keyframe that represents their scene. Read the image for visual detail.

### `resource <id|url> [--workspace DIR]`
Register the video as a `## Knowledge` entry in `<workspace>/RESOURCES.md` (default: cwd),
for the `teach` skill. Idempotent.

### `status <id>` · `list` · `estimate <url>`
Ingest progress for a video · all ingested videos · (Phase 6) preview vision-pass cost.

## JSON output (for agents)

`digest --json`, `search --json`, and `ask --json` emit structured JSON to stdout so a
calling agent can consume evidence without scraping text. `ask --json` shape:

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
