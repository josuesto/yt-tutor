# yt-tutor — Handoff

**Status:** shipped and public, ongoing. 2026-06-24.
**Repo:** local `C:\Users\fonox\yt-tutor`, public `https://github.com/josuesto/yt-tutor` (`main`, in sync).
39 tests passing, ruff clean. MIT. git identity local: Josue Soto / josuesto@icloud.com.

## What it is

A local Python CLI plus an installable Claude Code skill. Given a YouTube URL it ingests the video
into a local, timestamped knowledge store that combines the spoken transcript with what is shown on
screen, so the agent running the skill can be taught the video and teach it back, citing `mm:ss` and
distinguishing speech from visuals. Think NotebookLM for one video, as a tool any coding agent drives.

## Core principle: dumb engine, smart agent

The Python engine never calls an LLM on the default path. It uses only local, deterministic tools
(`yt-dlp`, `ffmpeg`, `faster-whisper`, SQLite, Pillow). The intelligence (teaching, answering, vision)
is the agent running the skill, which the user already pays for via Claude Code or Cursor. So the
default path is free and needs no API key, and the tool is portable across agents.

## How to run

```
pip install -e .                      # core; add [whisper] / [anthropic] / [all] for extras
$env:YT_TUTOR_DATA_DIR = "<repo>\data"   # where the db + frames live (PowerShell)
yt-tutor ingest "<youtube-url>" --no-vision
yt-tutor digest <id> --md
```
Note: on this machine `python` on PATH points at a Hermes agent venv; use **`py`** for the system
Python that has pytest/ruff/yt-tutor installed (`py -m pytest`, `py -m ruff check .`). The `yt-tutor`
console script works regardless.

## Architecture

- `yt_tutor/pipeline/` — `metadata` (yt-dlp), `captions` (VTT parse), `audio`+`transcribe`
  (faster-whisper fallback), `frames` (ffmpeg 1fps + dHash keyframe dedup + edge-density salience),
  `chunks` (15-30s merge, edges clamped to 0 and duration), `vision` (opt-in headless pass),
  `summary`, `runner` (resumable per-step ledger).
- `yt_tutor/qa/` — `digest` (the load-the-video artifact), `search` (FTS5), `ask` (timestamped evidence).
- `yt_tutor/providers/` — vision adapters (`anthropic` default, `openai`/`gemini`/`ollama`), used
  only by the headless `--vision` pass.
- `yt_tutor/` — `db` (SQLite schema + CRUD), `config`, `util`, `errors`, `estimate`, `teach_export`,
  `verify`, `cli`.
- `SKILL.md` (repo root) + `references/cli.md` — the agent-facing skill (install by linking the repo
  into `~/.claude/skills/yt-tutor`).
- `data/` (gitignored) — `watcher.db`, `videos/<id>/frames/frame_000001.jpg`, `digest.md`.

## Vision comes from the agent (the key decision)

The model running the skill is the vision system. For a visual question it reads the keyframe with
`frames --at`. To teach thoroughly it runs `keyframes --pending --by-salience`, reads the content-rich
frames, records what it sees with `set-vision --at <ts> --file <json>`, then `rechunk` folds those
notes into the digest and search. The paid provider `--vision` pass is a headless-only fallback.

## Native teaching (the headline experience) — revised 2026-06-24

Teaching is **native**: hand the skill a YouTube link and it ingests, knows the video, and teaches
it here, with no second skill and no workspace to set up. The talk-vs-`/teach` hand-off was removed.
After the digest loads the skill asks a single-select — *ask about it* (default) vs *be taught it* —
and both happen inside `yt-tutor`. To teach, the agent builds one-idea-each HTML lessons under
`data/videos/<id>/lessons/`, grounded in the digest (the single source of truth), citing every claim
to a clickable `mm:ss` link, embedding the actual keyframes, with check-questions to close the loop —
the `teach` skill's pedagogy folded in, with the video as the grounded resource. Validated end to end
on a 3Blue1Brown lecture.

**Optional export (off the default path):** for users who run a separate `teach` skill,
`yt-tutor ingest "<url>" --teach` (or `resource <id>`) still writes a `## Knowledge` entry into that
workspace's `RESOURCES.md`. Tested (`test_teach_export.py`) but not required.

## Verification (mandatory trust gate)

Citations drift, so every claim is checked against the source before a learner sees it:
`transcript --at` (spoken), `frames --at` (visual), and `verify <id> --lesson <file>` which checks
every timestamp a lesson cites in one pass. SKILL.md makes `verify --lesson` mandatory. It caught
three real citation drifts in one drafted lesson.

## Commands

ingest · digest · summary · search · ask · frames · transcript · keyframes · set-vision · rechunk ·
verify · resource · status · list · estimate. Full reference: `references/cli.md`. Tuning knobs:
`docs/MANUAL.md`.

## What is validated

Free path end to end on a music video (60 captions, 213 frames → 186 keyframes, 10 chunks) and a
19-min lecture (286 captions, 1120 frames → 128 keyframes / 89% dedup, 50 chunks; 720p reads dense
math). Local whisper (tiny) produced 25 segments. Agent vision recorded by hand made visuals
searchable. Teach loop produced a dense grounded lesson with embedded frames. `verify` grounded all
8 lesson citations in one pass. `--vision` with no key degrades gracefully (unit-tested with a fake
provider; live paid call not exercised by design).

## Known limitations and deferred (v2)

- Web UI + clickable player, embeddings/hybrid retrieval, playlists, multi-video knowledge base.
- Salience is coarse on sparse white-on-black math (a sort hint, never a filter).
- Multi-hour lectures overflow the full digest (search fallback covers it).
- Description blob is noisy for some channels.
- Gemini/Ollama vision adapters are written but experimental; live paid vision untested.

## Native teaching validated on a slide deck (2026-06-24)

Ran the full native flow end to end on a CNCF lightning talk, "FAQs for CFPs" (`jCz9QPrJ6Eo`, 5:12,
real text slides). Findings:
- **Dedup on static slides:** 312 frames -> 27 keyframes (91%). Captions free (no whisper).
- **Bug found + fixed:** `rechunk`/runner folded only `scene_description` into the searchable
  `embedding_text`, so a slide's OCR'd bullets (`visible_text`) were not searchable. Fixed with
  `db.visual_texts_for_frame` (display vs index split); slide-only phrases now hit. Commit `1dc02ec`.
- **Lesson:** built `data/videos/jCz9QPrJ6Eo/lessons/0001-writing-a-cfp-that-gets-you-on-stage.html`
  (857 words, 4 sections, 4 embedded real slides, 17 cited clickable `mm:ss` links, check questions +
  practice). `verify --lesson` grounded all 17 in one pass; caught one phrasing drift (fixed) and
  flagged the footer's `(5:12)` duration as a phantom citation (regex can't tell duration from a cite;
  errs safe). DOM-checked: all four slides decode to 640x360.
- **Salience note:** scores are flat on text slides (0.04-0.066), so chapters guide frame choice, not
  salience. Consistent with "sort hint, never a filter."

## Resume here (next options)

1. Make agent-vision recording a smoother single step (read + set-vision in one flow).
2. Polish for a wider audience: trim noisy channel-description text out of the digest, add a
   `yt-tutor clean <id>` command to remove a video's `data/` files.
3. Consider teaching `Lesson 2` from the same talk (nerves, rejection, after acceptance) to exercise
   multi-lesson progression + a shared glossary.html.

## Sanity check (confirm it still works)

```
cd <repo>; py -m pytest -q            # 39 passing
$env:YT_TUTOR_DATA_DIR="<repo>\data"
yt-tutor ingest "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --no-vision
yt-tutor digest dQw4w9WgXcQ --md | Select-Object -First 6
```
