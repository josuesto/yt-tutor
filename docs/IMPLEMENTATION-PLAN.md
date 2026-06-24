# yt-tutor — Implementation Plan

Phased build. Each phase ends in a **runnable, committed** state. Tests are written
alongside (TDD where logic is non-trivial). Phases gate on their acceptance check.

---

## Phase 0 — Scaffold + plan  ✅ (this phase)
- [x] Repo + git init
- [x] `pyproject.toml`, `.gitignore`, `.env.example`
- [x] `docs/DESIGN.md`, `docs/IMPLEMENTATION-PLAN.md`
- [ ] `yt_tutor/` package skeleton (`__init__`, `config`, `db`, `cli`)
- [ ] SQLite schema (`db.py`) + a smoke test
- [ ] Initial commit

**Acceptance:** `python -c "import yt_tutor"` works; `yt-tutor --help` lists commands;
`yt-tutor` creates the DB schema on first run.

---

## Phase 1 — Ingestion core (transcript-only, no vision)
Deterministic, resumable spine. No model calls.
- [ ] `pipeline/metadata.py` — `yt-dlp` extract_info → videos row (title, channel, duration, description, chapters).
- [ ] `pipeline/captions.py` — fetch + parse subtitles → `transcript_segments` (source=youtube_captions).
- [ ] `pipeline/frames.py` — `ffmpeg -vf fps=1` → `frame_000001.jpg…`; Pillow dHash; keyframe dedup. **(contribution: `is_new_keyframe`)**
- [ ] `pipeline/chunks.py` — merge transcript into 15–30s chunks; `embedding_text`; populate `chunks_fts`. **(contribution: boundary policy)**
- [ ] `pipeline/runner.py` — orchestrate; `ingest_state` ledger; resume; `--force`.
- [ ] `cli.py` — wire `ingest`, `status`, `list`.
- [ ] Preflight: ffmpeg/yt-dlp presence checks with actionable errors.

**Acceptance:** `yt-tutor ingest <url> --no-vision` on a captioned video produces a DB with
metadata, transcript segments, 1-fps frame rows (keyframes flagged), and chunks. Re-running
resumes/skips. Tested on a short real video.

---

## Phase 2 — Whisper fallback
- [ ] `pipeline/audio.py` — `yt-dlp` bestaudio → `data/videos/{id}/audio.m4a`.
- [ ] `pipeline/transcribe.py` — `faster-whisper` → `transcript_segments` (source=whisper).
- [ ] `runner` routes to whisper only when captions are absent + extra installed; else clear message.

**Acceptance:** a caption-less video transcribes via whisper when `[whisper]` is installed;
without it, a clear, non-crashing message.

---

## Phase 3 — Eager keyframe vision (opt-in)
- [ ] `providers/base.py` — `VisionProvider.analyze_keyframe(image_path, ts) -> FrameAnalysis`.
- [ ] `providers/anthropic.py` — tool-use forces the frame JSON schema; batch; prompt caching. **(consult `claude-api` skill for model id + call shape)**
- [ ] `providers/{openai,gemini,ollama}.py` — alternates.
- [ ] `providers/__init__.py` — env-driven registry.
- [ ] `pipeline/vision.py` — analyze keyframes; write structured fields; dupes → `reused`; retry/backoff; resumable cache.
- [ ] `cli.py` — `--vision/--no-vision`; honor `VISION_ENABLED`.

**Acceptance:** `yt-tutor ingest <url> --vision` populates frame vision fields for keyframes
only; re-run re-pays nothing; a forced API error leaves the ingest resumable.

---

## Phase 4 — Digest + summary + search
- [ ] `qa/digest.py` — timestamped multimodal digest (`--md`/`--json`); write `digest.md`.
- [ ] `pipeline/summary.py` — detailed multimodal summary + tl;dr → `summaries`.
- [ ] `qa/search.py` — FTS5 query → ranked chunks (+ frame paths, timestamps).
- [ ] `qa/ask.py` — retrieve + return evidence (`--json`) or synthesize if a provider is set.
- [ ] `cli.py` — wire `digest`, `summary`, `search`, `ask`, `frames`.

**Acceptance:** `digest` emits a clean timestamped doc; `search "<q>"` returns relevant
chunks with timestamps; `frames --at 3:15` prints the right image path(s).

---

## Phase 5 — SKILL.md + teach handoff
- [ ] Build `SKILL.md` via the `skill-creator` skill (valid Claude Code skill).
- [ ] `teach_export.py` — append/update a `## Knowledge` entry in workspace `RESOURCES.md`
      (per `RESOURCES-FORMAT.md`) + link the digest. **(contribution: annotation line)**
- [ ] `cli.py` — wire `resource`; `ingest --teach` runs ingest + resource.
- [ ] Document the `/teach` handoff in `SKILL.md`.

**Acceptance:** after `ingest --teach`, the workspace `RESOURCES.md` gains a well-formed,
annotated video entry pointing at the digest; `/teach` can ground a lesson on it.

---

## Phase 6 — Estimate, errors, README, test pass
- [ ] `cli.py` — `estimate <url>`: probe duration + dedup ratio heuristic → predicted
      keyframe count × provider price → cost preview.
- [ ] Harden error paths (private/age-restricted/unavailable/partial).
- [ ] Finalize `README.md` (install, quickstart, providers, teach integration, troubleshooting).
- [ ] `pytest` pass; `ruff` clean.

**Acceptance:** all 10 acceptance criteria in `DESIGN.md §10` demonstrably met.
