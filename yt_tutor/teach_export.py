"""Bridge to the `teach` skill.

The `teach` skill grounds every lesson in trusted sources listed in `RESOURCES.md`
and forbids parametric guessing. This module registers an ingested video as a
`## Knowledge` resource in the current teach workspace, pointing at the saved
digest — so `/teach` can build mission-grounded lessons that cite the video's
real mm:ss timestamps. yt-tutor acquires the knowledge; `teach` does the pedagogy.
"""

from __future__ import annotations

from pathlib import Path

from . import config, db

KNOWLEDGE_HEADER = "## Knowledge"


def register_resource(conn, video_id, *, workspace=None, digest_path=None):
    """Append (or no-op if already present) a Knowledge entry for the video in
    `<workspace>/RESOURCES.md`, following the teach skill's RESOURCES format.

    Returns (resources_path, added: bool). Existing content is preserved."""
    v = db.get_video(conn, video_id)
    if v is None:
        raise KeyError(video_id)

    workspace = Path(workspace) if workspace else Path.cwd()
    resources = workspace / "RESOURCES.md"
    _total, keys = db.count_frames(conn, video_id)
    nseg = db.count_segments(conn, video_id)
    digest = digest_path or config.digest_path(video_id)
    url = v["youtube_url"]
    title = v["title"] or video_id
    channel = v["channel"] or "unknown"

    entry = (
        f"- [Video: {title} - {channel}]({url})\n"
        f"  Timestamped transcript ({nseg} segments) + {keys} visual keyframes, ingested by "
        f"yt-tutor. Local digest: {digest}. Use for: anything covered in this video; "
        f"cite mm:ss timestamps and note speech vs on-screen visuals."
    )

    text = resources.read_text(encoding="utf-8") if resources.exists() else ""
    if url in text:
        return resources, False

    if KNOWLEDGE_HEADER not in text:
        text = "# Resources\n\n## Knowledge\n" if not text.strip() \
            else text.rstrip() + "\n\n## Knowledge\n"

    # Insert the entry directly under the Knowledge header.
    out, inserted = [], False
    for line in text.splitlines():
        out.append(line)
        if not inserted and line.strip() == KNOWLEDGE_HEADER:
            out.append(entry)
            inserted = True
    if not inserted:
        out += [KNOWLEDGE_HEADER, entry]

    resources.write_text("\n".join(out) + "\n", encoding="utf-8")
    return resources, True
