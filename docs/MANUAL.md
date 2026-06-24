# yt-tutor — Manual & Tuning Guide

Everything `yt-tutor` does is controllable. This page explains each knob, what it
trades off, and how to set it. **Every setting can be changed three ways** (later
wins): a baked-in default → an environment variable (or `.env`) → a CLI flag.

---

## What costs money and what doesn't

| Stage | Cost |
|---|---|
| Metadata, captions, frame extraction, dedup, chunking | **Free** — local tools only |
| **Transcription** | **Always free.** YouTube captions first; if none, a **local** `faster-whisper` model. yt-tutor never sends audio to a paid transcription API. |
| **Vision (per-keyframe analysis)** | **The only paid step, and it's opt-in** (`--vision`). Uses your chosen provider's API. |

So the default `yt-tutor ingest <url> --no-vision` costs **nothing** and needs **no keys**.

---

## The keyframe threshold — the cost/fidelity dial

Frames are extracted at 1 fps, then collapsed to **keyframes** (frames where the
scene actually changes) using a 64-bit perceptual hash (dHash) and **Hamming
distance**. Only keyframes get the (paid) vision pass.

A 1fps frame becomes a **new keyframe** when it differs from the **last kept**
keyframe by **more than `KEYFRAME_HAMMING_THRESHOLD` bits** (out of 64).

```bash
KEYFRAME_HAMMING_THRESHOLD=10           # in .env / environment
yt-tutor ingest "<url>" --keyframe-threshold 14   # or per-run on the CLI
```

**Default: `10`.** Why 10 (not the ~5 you'll see quoted for "same image"
detection)? That 5 is for finding *exact duplicates*; our goal is the opposite —
*scene-change segmentation* — so we deliberately sit higher to collapse frames that
are merely similar (a talking head where only the mouth moves, compression shimmer,
a slow zoom).

| Content type | Suggested threshold | Why |
|---|---|---|
| Slides / lecture / talking head | **8–12** | Big jumps on slide changes; static otherwise. 10 is ideal. |
| Screencast / coding | **8–12** | Snaps a keyframe as enough of the screen changes. |
| Vlog / interview | **10–14** | Tolerate camera motion without spamming keyframes. |
| Gameplay / action / music video | **14–18** | Near-constant motion; a low threshold makes every second a keyframe (expensive). |

Lower = more keyframes (more vision cost, finer fidelity). Higher = fewer (cheaper,
may miss subtle on-screen changes). Run `yt-tutor estimate "<url>"` to preview how
many keyframes a threshold yields **before** you pay.

> **Why compare to the last *kept* keyframe, not the previous frame?** A slow pan
> changes only a few bits per second — a frame-to-frame test would never trip and
> would treat a continuously drifting shot as one scene forever. Measuring against
> the fixed anchor lets drift accumulate until it crosses the threshold.

---

## All settings

| Setting | Env var | Default | CLI | Notes |
|---|---|---|---|---|
| Data directory | `YT_TUTOR_DATA_DIR` | `./data` | — | Where the DB + frames live. |
| Keyframe threshold | `KEYFRAME_HAMMING_THRESHOLD` | `10` | `--keyframe-threshold` | The dial above. |
| Frames per second | `YT_TUTOR_FPS` | `1` | — | The spec's contract; leave at 1. |
| Max video height | `MAX_VIDEO_HEIGHT` | `720` | — | Higher = more legible slides/OCR, bigger files. |
| Chunk length (s) | `CHUNK_TARGET_SECONDS` | `20` | — | Stays inside the 15–30s band. |
| Vision on by default | `VISION_ENABLED` | `false` | `--vision` / `--no-vision` | Flags always win. |
| Vision provider | `VISION_PROVIDER` | `anthropic` | — | `anthropic` \| `openai` \| `gemini` \| `ollama`. |
| Whisper model | `WHISPER_MODEL` | `base` | — | `tiny`…`large-v3`. Bigger = better + slower. |
| Whisper device | `WHISPER_DEVICE` | `cpu` | — | `cpu` \| `cuda`. |

API keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`) are only read
when the vision pass is on. See `.env.example`.

---

## Resumability

Each stage (`metadata → transcript → frames → vision → chunks → summary`) records
completion in the `ingest_state` table. Re-running `ingest`:

- **skips** any stage already done,
- **never re-pays** for keyframes already analyzed,
- **resumes** a crashed ingest from the last completed step.

Force a clean re-run of all stages with `--force`. Check progress anytime with
`yt-tutor status <id>`.

---

## Transcription detail

1. **YouTube captions** (human-authored preferred, auto-generated fallback) — free.
2. If a video has **no captions**, and you installed the extra
   (`pip install "yt-tutor[whisper]"`), a **local** `faster-whisper` model
   transcribes the audio — free, offline, CPU-capable.
3. With neither, yt-tutor tells you plainly and continues (frames are still useful).

The transcript `source` is recorded per segment (`youtube_captions` or `whisper`)
so answers can say where the words came from.

---

## Verifying claims and lessons

Teaching from a video is only trustworthy if every citation is checked, and citations drift by
seconds. Three commands ground a claim against the source:

- `yt-tutor transcript <id> --at <ts>` — the words spoken around a moment (spoken claims).
- `yt-tutor frames <id> --at <ts>` — the keyframe image to read (visual claims).
- `yt-tutor verify <id> --lesson <file>` — **one pass** over a whole lesson: every cited timestamp
  with its transcript window and nearest keyframe. Confirm each claim; fix the timestamp or drop it.

The skill (`SKILL.md`) makes `verify --lesson` a mandatory step before a learner sees a lesson.

## Agent-provided vision vs the headless `--vision` pass

By default the agent running the skill is the vision system: it reads keyframes itself (free) and
records what it sees with `set-vision`, then `rechunk` folds those notes into the digest and search.
The paid `--vision` pass (provider set by `VISION_PROVIDER`) only exists for headless runs where no
vision-capable agent is present. `keyframes --by-salience` ranks frames by an edge-density content
score so the richest frames are described first and near-blank transitions are skipped.
