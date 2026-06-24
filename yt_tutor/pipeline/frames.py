"""Stage 3: extract 1fps frames and dedupe to keyframes.

Download one capped-resolution copy of the video (reused later for whisper audio),
extract a frame per second with ffmpeg, then collapse near-identical frames so the
(paid, opt-in) vision pass only runs on frames where the scene actually changes.

The keyframe decision is the tool's cost/fidelity dial — see `is_new_keyframe`
and docs/MANUAL.md."""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image

from .. import config, errors, util

_VIDEO_EXTS = (".mp4", ".mkv", ".webm", ".mov")


# --- perceptual hashing ----------------------------------------------------

def dhash(path, hash_size: int = 8) -> int:
    """64-bit difference hash: compares each pixel to its right neighbour on a
    (hash_size+1 x hash_size) grayscale thumbnail. Robust to brightness/scale,
    sensitive to structure — ideal for spotting scene changes."""
    img = Image.open(path).convert("L").resize((hash_size + 1, hash_size))
    px = img.load()
    bits = 0
    idx = 0
    for y in range(hash_size):
        for x in range(hash_size):
            bits |= (1 if px[x, y] < px[x + 1, y] else 0) << idx
            idx += 1
    return bits


def hamming(a: int, b: int) -> int:
    """Number of differing bits between two hashes (0-64)."""
    return bin(a ^ b).count("1")


def is_new_keyframe(prev_hash, curr_hash, threshold: int) -> bool:
    """Does `curr` open a new scene versus the last KEPT keyframe (`prev`)?

    `prev_hash` is the anchor — the hash of the most recent frame we decided to
    keep — or None for the very first frame (always kept). A frame is a new
    keyframe when it differs from the anchor by MORE than `threshold` bits.

    Comparing against the kept anchor (not the immediately previous frame) means
    slow drift (a gentle pan/zoom) still accumulates until it crosses the
    threshold, instead of sneaking under a frame-to-frame test forever.

    Tuning (`threshold`, default 10 of 64): lower => more keyframes (more vision
    cost, finer fidelity); higher => fewer (cheaper, may miss subtle changes).
    ~6-12 suits talks/slides; raise to ~14-18 for high-motion video. See MANUAL.md.
    """
    if prev_hash is None:
        return True
    return hamming(prev_hash, curr_hash) > threshold


# --- download + extract ----------------------------------------------------

def download_source(info: dict, video_id: str, max_height: int | None = None) -> Path:
    """Download one muxed, height-capped copy of the video (idempotent)."""
    import yt_dlp

    max_height = max_height or config.max_video_height()
    vdir = config.video_dir(video_id)
    vdir.mkdir(parents=True, exist_ok=True)

    existing = [p for p in vdir.glob("source.*") if p.suffix.lower() in _VIDEO_EXTS]
    if existing:
        return existing[0]

    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "format": f"best[height<={max_height}]/bestvideo[height<={max_height}]+bestaudio/best",
        "outtmpl": str(vdir / "source.%(ext)s"),
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([info.get("webpage_url")])

    found = [p for p in vdir.glob("source.*") if p.suffix.lower() in _VIDEO_EXTS]
    if not found:
        raise errors.YtTutorError("Failed to download the video for frame extraction.")
    return found[0]


def extract_frames(source_path: Path, video_id: str, fps: int = 1):
    """ffmpeg fps=N -> frames/frame_000001.jpg ... Returns [(index, ts_seconds, path)].
    Idempotent: if frames already exist on disk, reuse them."""
    util.require("ffmpeg", "Install it from https://ffmpeg.org/download.html and re-run.")
    fdir = config.frames_dir(video_id)
    fdir.mkdir(parents=True, exist_ok=True)

    existing = sorted(fdir.glob("frame_*.jpg"))
    if not existing:
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", str(source_path), "-vf", f"fps={fps}", "-q:v", "3",
            str(fdir / "frame_%06d.jpg"),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise errors.YtTutorError(
                f"ffmpeg frame extraction failed: {proc.stderr.strip()[:300]}")
        existing = sorted(fdir.glob("frame_*.jpg"))

    frames = []
    for p in existing:
        index = int(p.stem.split("_")[1])
        frames.append((index, index - 1, p))  # frame i (1-based) ~ second i-1
    return frames


def dedup_frames(frames, threshold: int):
    """Tag each (index, ts, path) as keyframe or duplicate, anchored on the last
    kept keyframe. Returns row dicts ready for db.insert_frames (video_id unset)."""
    rows = []
    anchor_hash = None
    anchor_ts = None
    for _index, ts, path in frames:
        try:
            h = dhash(path)
        except Exception:
            h = None  # unreadable frame -> be safe and treat it as a keyframe
        keyframe = True if h is None else is_new_keyframe(anchor_hash, h, threshold)
        if keyframe:
            if h is not None:
                anchor_hash = h
            anchor_ts = ts
            duplicate_of = None
        else:
            duplicate_of = anchor_ts
        rows.append({
            "video_id": None,
            "timestamp_seconds": ts,
            "file_path": str(path),
            "phash": format(h, "016x") if h is not None else None,
            "is_keyframe": 1 if keyframe else 0,
            "duplicate_of": duplicate_of,
        })
    return rows


def process_frames(info: dict, video_id: str, *, threshold: int, fps: int = 1,
                   max_height: int | None = None):
    """Full stage: download -> extract -> dedupe. Returns (rows, source_path)."""
    source = download_source(info, video_id, max_height)
    frames = extract_frames(source, video_id, fps)
    rows = dedup_frames(frames, threshold)
    for r in rows:
        r["video_id"] = video_id
    return rows, source
