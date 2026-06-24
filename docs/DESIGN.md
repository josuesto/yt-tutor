# yt-tutor — Design Spec

**Status:** approved (brainstorm → build)
**Date:** 2026-06-24

## 1. Problem & goal

Given a YouTube URL, ingest the video into a local, queryable, **timestamped** knowledge
store that combines **spoken transcript** and **visual content** (frames), so that an AI
agent can be "taught" the video and then teach it back to the user — citing `mm:ss`
timestamps and stating whether each point came from **speech, visuals, or both**.

It is a **CLI tool + an agent skill**, not a web app. The CLI is a deterministic ingestion
engine; the intelligence (teaching, Q&A) lives in whatever agent runs it (Claude Code,
Cursor Composer, etc.).

## 2. Core design principle: dumb engine, smart agent

The Python engine does **no LLM reasoning on the default path**. It downloads, transcribes,
extracts frames, dedupes, chunks, and stores — all with local/deterministic tools
(`yt-dlp`, `ffmpeg`, `faster-whisper`, SQLite, Pillow). The *teaching* is done by the
consuming agent reading the engine's output.

Consequences:
- The default path needs **no API key** and costs nothing beyond local compute.
- The engine is **portable** across any agent that can run a CLI.
- The one paid step — per-frame vision analysis — is **opt-in** (`--vision`) and configurable.

## 3. Locked decisions

| Area | Decision | Rationale |
|---|---|---|
| Language | **Python 3.10+** | `yt-dlp` is importable as a library; whisper/vision ecosystem is Python. |
| Frames | Extract **1 fps**; run vision only on **perceptual-hash keyframes** (scene shifts); near-duplicate seconds reuse the keyframe's summary. | Meets the "1 record per second" timeline while keeping vision cost sane (~80–250 calls for a 20-min talk vs ~1,200). |
| Vision timing | **Eager** at ingest, on each keyframe; provider-configurable; `--no-vision` for a free transcript-only run. | Matches "vision fires when the scene shifts"; makes the digest genuinely multimodal. |
| Transcription | **Captions first** (yt-dlp); **faster-whisper** as an optional, recommended fallback. | Most videos have captions; whisper rarely runs, so it stays an opt-in extra. |
| Default model | **Anthropic Claude** (Haiku-class for vision), behind an adapter; OpenAI/Gemini/Ollama swappable by env. | User's stated preference; adapter keeps it provider-agnostic for publishing. |
| Q&A / teaching | **Hand off to the user's `teach` skill** by registering the video as a trusted **resource**; ship a standalone teaching `SKILL.md` for users without `teach`. | "Teaching method = the skill we have." |
| Long-video Q&A | Full digest loaded into context when it fits; **SQLite FTS5** retrieval fallback for very long videos. | NotebookLM-style "knows the whole video"; degrades gracefully. |

## 4. Architecture

Two artifacts in one repo:

### 4a. `yt_tutor` — the engine (Python CLI)

```
yt_tutor/
  cli.py            # argparse entry: ingest · digest · summary · frames · search · ask · resource · status · list · estimate
  config.py         # env loading, provider selection, deterministic paths
  db.py             # SQLite schema + CRUD (the store)
  pipeline/
    metadata.py     # yt-dlp -> title, channel, duration, description, chapters
    captions.py     # yt-dlp subtitle fetch + parse -> transcript segments
    audio.py        # yt-dlp audio-only download (whisper input)
    transcribe.py   # faster-whisper fallback -> transcript segments
    frames.py       # ffmpeg 1fps extraction + perceptual-hash keyframe dedup
    vision.py       # per-keyframe structured JSON via a provider (eager, opt-in)
    chunks.py       # merge transcript + frame summaries into 15-30s chunks
    summary.py      # detailed multimodal video summary
    runner.py       # orchestrates stages; resumable; tracks per-step state
  providers/
    __init__.py     # registry: get_vision_provider() from env
    base.py         # VisionProvider interface (analyze_keyframe -> FrameAnalysis)
    anthropic.py    # default (tool-use forces the frame JSON schema; prompt caching)
    openai.py  gemini.py  ollama.py
  qa/
    digest.py       # build the timestamped multimodal digest (md/json)
    search.py       # FTS5 retrieval over chunks (long-video fallback)
    ask.py          # retrieve + return evidence (--json) or synthesize
  teach_export.py   # register a video as a Knowledge resource in a `teach` workspace
```

### 4b. `SKILL.md` — the teaching skill (agent-facing)

Documents, for any agent: on a URL → `ingest`; to teach → load the `digest`, teach in the
learning style citing `mm:ss`, label speech vs visual, pull keyframes via `frames --at`
for visual questions, `search` for long videos. When a `teach` workspace is present, run
`resource` to register the video and hand off to `/teach`.

## 5. The `teach` skill seam (key integration)

The user's `~/.claude/skills/teach` workspace grounds all lessons in `RESOURCES.md` and
forbids parametric guessing. `yt-tutor` feeds that contract:

1. `yt-tutor ingest <url> --teach` ingests the video AND
2. writes a `## Knowledge` bullet into the workspace `RESOURCES.md` (per `RESOURCES-FORMAT.md`):
   `- [Video: {title} — {channel}]({url})` + an annotation (what it covers / when to reach for it)
   + a pointer to the local digest file (`data/videos/{id}/digest.md`).
3. `/teach` then builds mission-grounded lessons from the video, citing `mm:ss` and pulling
   keyframes. `yt-tutor` is the *knowledge* arm; `teach` is the *pedagogy* arm.

The digest is the hand-off interface, so this works whether the agent is `/teach`, Claude
Code, or Cursor Composer.

## 6. Data model (SQLite)

- **videos**(`id` PK = YouTube id, `youtube_url`, `title`, `channel`, `duration_seconds`,
  `description`, `chapters_json`, `created_at`, `status`, `last_step`, `error`)
- **transcript_segments**(`id`, `video_id`, `start_seconds`, `end_seconds`, `text`,
  `source` ∈ {`youtube_captions`, `whisper`})
- **frames**(`id`, `video_id`, `timestamp_seconds`, `file_path`, `phash`, `is_keyframe`,
  `duplicate_of` (ts of the keyframe whose summary it reuses), `vision_status`
  ∈ {`pending`,`done`,`reused`,`skipped`,`failed`}, plus the structured vision fields:
  `scene_description`, `visible_text` (ocr), `detected_objects_json`, `people`,
  `screen_or_slide_summary`, `notable_details_json`, `vision_summary`)
- **chunks**(`id`, `video_id`, `start_seconds`, `end_seconds`, `transcript_text`,
  `visual_summary`, `frame_paths_json`, `embedding_text`)
- **chunks_fts**: FTS5 over `embedding_text` (long-video retrieval)
- **summaries**(`video_id` PK, `tl_dr`, `detailed_md`, `created_at`)
- **ingest_state**(`video_id`, `step`, `status`, `updated_at`) — the resume ledger

Deterministic paths: `data/videos/{video_id}/frames/frame_000001.jpg`,
`data/videos/{video_id}/digest.md`, `data/watcher.db`.

Per-frame vision JSON contract (the shape the provider must return):
```json
{
  "timestamp_seconds": 0,
  "scene_description": "",
  "visible_text": [],
  "objects": [],
  "people": "",
  "screen_or_slide_summary": "",
  "notable_details": []
}
```

## 7. Pipeline & resumability

Stages run in order; each is **idempotent** and writes its completion to `ingest_state`:

`metadata → (captions │ audio→whisper) → frames(1fps) → dedup → vision(keyframes) → chunks → summary`

`runner.py` skips any stage already `done`. Frame vision skips frames that already have a
`vision_status` of `done`/`reused` — so re-runs **never re-pay** the model, and a crash
mid-ingest resumes from the last completed step. `--force` re-runs a stage.

## 8. Error handling

- **ffmpeg/yt-dlp missing** → preflight check with an actionable message.
- **private / age-restricted / unavailable** → catch yt-dlp's error, set `status=failed`
  with a human-readable `error`, exit non-zero.
- **no captions** → fall back to whisper (if installed) else clear "no transcript" guidance.
- **model API failure** → retry with backoff; mark affected frames `failed` and leave the
  ingest resumable (partial results preserved).

## 9. v1 scope vs deferred (v2)

**v1:** ingest, deterministic store, 1fps + keyframe dedup, eager vision (opt-in), chunks,
detailed summary, digest export, FTS5 search, `resource` handoff to `teach`, `SKILL.md`,
cost `estimate`, resumability, README.

**Deferred (v2):** web UI + player, embeddings/hybrid retrieval, OCR-only pre-pass,
Markdown notes export, playlists, multi-video knowledge base, background job queue.

## 10. Acceptance criteria → where met

1. ingest a URL → `ingest` (§4a, §7)
2. metadata + captions/audio + frames → `pipeline/*` (§7)
3. 1 fps extraction → `frames.py` (§3)
4. timestamped transcript segments + frame summaries → `transcript_segments`, `frames` (§6)
5. merged chunks → `chunks.py`, `chunks` (§6)
6. "what is this video about?" → `summary` + `digest` (§4)
7. detailed spoken question → transcript in digest / `search`
8. detailed visual question → `frames --at` + agent vision (§4b)
9. timestamps in answers → enforced by `SKILL.md` (§4b)
10. README with setup/commands/deps → §README

## 11. Learning-mode contribution points

Spots where a human design decision genuinely shapes behavior (to be implemented
collaboratively, not auto-filled):
- **Keyframe threshold** (`frames.is_new_keyframe`): how different must a frame be to count
  as a new scene? Trades vision cost vs. missing on-screen changes.
- **Chunk boundary policy** (`chunks.build_chunks`): fixed 15–30s windows vs. snapping to
  sentence/scene boundaries.
- **Resource annotation** (`teach_export`): what makes a useful "when to reach for it" line.
