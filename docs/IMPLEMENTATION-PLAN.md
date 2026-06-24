# yt-tutor — Implementation Plan

Phased build. Each phase ends in a **runnable, committed** state. Tests are written
alongside (TDD where logic is non-trivial). Phases gate on their acceptance check.

---

## Phase 0 — Scaffold + plan  ✅ (this phase)
- [x] Repo + git init
- [x] `pyproject.toml`, `.gitignore`, `.env.example`
- [x] `docs/DESIGN.md`, `docs/IMPLEMENTATION-PLAN.md`
- [x] `yt_tutor/` package skeleton (`__init__`, `config`, `db`, `cli`)
- [x] SQLite schema (`db.py`) + a smoke test
- [x] Initial commit

**Acceptance:** `python -c "import yt_tutor"` works; `yt-tutor --help` lists commands;
`yt-tutor` creates the DB schema on first run.

---

## Phase 1 — Ingestion core (transcript-only, no vision)
Deterministic, resumable spine. No model calls.
- [x] `pipeline/metadata.py` — `yt-dlp` extract_info → videos row (title, channel, duration, description, chapters).
- [x] `pipeline/captions.py` — fetch + parse subtitles → `transcript_segments` (source=youtube_captions).
- [x] `pipeline/frames.py` — `ffmpeg -vf fps=1` → `frame_000001.jpg…`; Pillow dHash; keyframe dedup. **(decided: threshold 10, anchored on last kept keyframe)**
- [x] `pipeline/chunks.py` — merge transcript into 15–30s chunks; `embedding_text`; populate `chunks_fts`. **(decided: accumulate + snap to cue boundary)**
- [x] `pipeline/runner.py` — orchestrate; `ingest_state` ledger; resume; `--force`.
- [x] `cli.py` — wire `ingest`, `status`, `list`.
- [x] Preflight: ffmpeg/yt-dlp presence checks with actionable errors.

**Acceptance:** ✅ `yt-tutor ingest <url> --no-vision` on a captioned video produces a DB with
metadata, transcript segments, 1-fps frame rows (keyframes flagged), and chunks. Re-running
resumes/skips. **Validated on `dQw4w9WgXcQ` → 60 segments, 213 frames / 186 keyframes, 10 chunks.**
Also fixed: UTF-8 console output (Windows cp1252 crash), private/unavailable-video error path.

---

## Phase 2 — Whisper fallback
- [x] `pipeline/audio.py`: reuse the source video via ffmpeg, else download bestaudio with yt-dlp.
- [x] `pipeline/transcribe.py`: `faster-whisper` (CTranslate2, CPU int8) into `transcript_segments` (source=whisper).
- [x] `runner` runs whisper only when captions are absent and the extra is installed; otherwise a clear message.

**Acceptance:** ✅ With `faster-whisper` installed, audio transcribes locally and free.
Validated live: the tiny model produced 25 timestamped segments from the on-disk audio.
Without the extra, a clear non-crashing message.

---

## Phase 3 — Eager keyframe vision (opt-in)
- [x] `providers/base.py` — `VisionProvider.analyze_keyframe(image_path, ts)` + `FRAME_SCHEMA`.
- [x] `providers/anthropic.py` — forced tool-use (Haiku-class `claude-haiku-4-5`) guarantees the frame JSON. (model id + call shape confirmed via `claude-api` skill.)
- [x] `providers/{openai,gemini,ollama}.py` — alternates (OpenAI structured outputs; Gemini/Ollama experimental).
- [x] `providers/__init__.py` — env-driven registry (`get_vision_provider`).
- [x] `pipeline/vision.py` — analyze keyframes; write structured fields; dupes → `reused`; per-frame failure isolation; resumable cache. Visuals aggregate into chunk `visual_summary` + `embedding_text`.
- [x] `cli.py` — `--vision/--no-vision`; honor `VISION_ENABLED`. Vision is non-fatal.

**Acceptance:** ✅ Pipeline unit-tested with a fake provider: analyzes keyframes only, re-run
re-pays nothing, per-frame errors isolate to `failed`, duplicates → `reused`. `--vision` with
no key degrades gracefully (warns + continues). Live paid call needs an API key (not exercised).
5 new tests (30 total).

---

## Phase 4 — Digest + summary + search
- [x] `qa/digest.py` — timestamped multimodal digest (`--md`/`--json`); write `digest.md`.
- [x] `pipeline/summary.py` — free structural overview + tl;dr → `summaries` (agent writes the prose).
- [x] `qa/search.py` — FTS5 query → ranked chunks (+ frame paths, timestamps); LIKE fallback.
- [x] `qa/ask.py` — retrieve + return timestamped evidence labeled speech/visual (`--json`).
- [x] `cli.py` — wire `digest`, `summary`, `search`, `ask`, `frames` (+ `_resolve` id/url).

**Acceptance:** ✅ `digest` emits a clean timestamped doc (saved to `digest.md`); `search "<q>"`
returns bm25-ranked chunks with timestamps; `ask` returns speech/visual-labeled evidence;
`frames --at 1:00` resolves to the representing keyframe. Validated live on `dQw4w9WgXcQ`.

---

## Phase 5 — SKILL.md + teach handoff
- [x] Build `SKILL.md` (root) via the `skill-creator` skill + `references/cli.md` (progressive disclosure).
- [x] `teach_export.py` — append/update a `## Knowledge` entry in workspace `RESOURCES.md`
      (per `RESOURCES-FORMAT.md`) + link the digest; idempotent, preserves existing content.
- [x] `cli.py` — wire `resource` (+ `--workspace`); `ingest --teach` runs ingest + resource.
- [x] Document the `/teach` handoff in `SKILL.md`.

**Acceptance:** ✅ `yt-tutor resource <id>` (and `ingest --teach`) writes a well-formed,
annotated `## Knowledge` entry pointing at the digest; idempotent. Validated live into a
teach workspace. 3 new tests (24 total).

---

## Phase 6 — Estimate, errors, README, test pass
- [x] `cli.py` — `estimate <url>`: duration + dedup heuristic → keyframe range × provider price → cost preview (with a high-motion caveat).
- [x] Harden error paths (private/age-restricted/unavailable + resumable partials). `_friendly` mapping tested.
- [x] Finalize `README.md` (from-source install + skill-install, quickstart, providers, teach integration, troubleshooting).
- [x] `pytest` pass (33) + `ruff` clean; `.gitattributes` normalizes line endings.

**Acceptance:** ✅ All 10 acceptance criteria in `DESIGN.md §10` met. `estimate` previews
$0.03-$0.15 for a 3.5-min video; unavailable videos return a clean message + non-zero exit.
