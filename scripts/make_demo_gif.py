"""Render docs/demo.gif: an animated terminal of a real yt-tutor session.

Deterministic, needs only Pillow (a core dependency), no terminal recorder.
Every line shown is real output from the CNCF sample talk (jCz9QPrJ6Eo).

    python scripts/make_demo_gif.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "docs", "demo.gif"))
S = 18

PAD, LH, ROWS, W, BAR = 22, 26, 22, 980, 30
H = BAR + PAD * 2 + LH * ROWS

BG, BARC = (13, 17, 23), (22, 27, 34)
GREEN, WHITE, DIM = (63, 185, 80), (230, 237, 243), (139, 148, 158)
CYAN, YELLOW = (86, 182, 255), (219, 171, 70)
COLOR = {"cmd": WHITE, "dim": DIM, "ok": GREEN, "ts": CYAN, "hint": YELLOW, "blank": DIM}


def _font(bold=False):
    names = (["consolab.ttf", "DejaVuSansMono-Bold.ttf", "LiberationMono-Bold.ttf"] if bold
             else ["consola.ttf", "DejaVuSansMono.ttf", "Menlo.ttc", "LiberationMono-Regular.ttf"])
    dirs = [r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts",
            "/Library/Fonts", "/System/Library/Fonts", os.path.expanduser("~/.fonts")]
    for d in dirs:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, S)
                except OSError:
                    pass
    try:
        return ImageFont.truetype("DejaVuSansMono.ttf", S)
    except OSError:
        return ImageFont.load_default()


font, fontb = _font(), _font(bold=True)

EVENTS = [
    ("cmd", 'yt-tutor ingest "youtu.be/jCz9QPrJ6Eo" --no-vision'),
    ("dim", "  transcript: 150 caption segments (youtube_captions)"),
    ("dim", "  frames: 312 @1fps -> 27 keyframes (91% deduped)"),
    ("ok",  "  done."),
    ("blank", ""),
    ("cmd", 'yt-tutor ask jCz9QPrJ6Eo "what should my talk be about"'),
    ("ts",  "  [1:49] (speech)"),
    ("dim", "    the best talks are where people talk about something"),
    ("dim", "    they care about ... a failure story, when things go"),
    ("dim", "    wrong, those are the best lessons people want to hear"),
    ("ts",  "  [1:26] (speech+visual)"),
    ("hint", "    shown: Slide 'Q4: What should I talk about?'"),
    ("blank", ""),
    ("cmd", "yt-tutor frames jCz9QPrJ6Eo --at 1:14"),
    ("ts",  "  [1:14] keyframe  data/.../frame_000075.jpg"),
    ("hint", "    the agent opens that image and reads it. no paid call."),
    ("blank", ""),
    ("cmd", 'yt-tutor search jCz9QPrJ6Eo "accessibility requirements"'),
    ("dim", "  [1:06] ...accessibility requirements, github repos, etc."),
    ("hint", "    a slide's own words, searchable. you are the vision."),
]


def render(committed, typing=None):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, BAR], fill=BARC)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([16 + i * 22, 9, 28 + i * 22, 21], fill=c)
    d.text((W // 2 - 34, 6), "yt-tutor", font=font, fill=DIM)
    view = committed + ([("cmd", typing)] if typing is not None else [])
    y = BAR + PAD
    for kind, text in view[-ROWS:]:
        if kind == "cmd":
            d.text((PAD, y), "$ ", font=fontb, fill=GREEN)
            ox = PAD + font.getlength("$ ")
            d.text((ox, y), text, font=font, fill=WHITE)
            if typing is not None and text == typing:
                cx = ox + font.getlength(text)
                d.rectangle([cx + 1, y + 3, cx + 10, y + S + 2], fill=WHITE)
        else:
            d.text((PAD, y), text, font=font, fill=COLOR.get(kind, DIM))
        y += LH
    return img


def main():
    frames, durs, committed = [], [], []

    def snap(dur, typing=None):
        frames.append(render(committed, typing))
        durs.append(dur)

    for kind, text in EVENTS:
        if kind == "cmd":
            for i in range(0, len(text) + 1, 3):
                snap(28, typing=text[:i])
            snap(380, typing=text)
            committed.append(("cmd", text))
        elif kind == "blank":
            committed.append(("blank", ""))
            snap(650)
        else:
            committed.append((kind, text))
            snap(150)
    snap(2800)

    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=durs,
                   loop=0, optimize=True, disposal=2)
    print(f"wrote {OUT}  ({len(frames)} frames, {os.path.getsize(OUT) / 1024:.0f} KB, {W}x{H})")


if __name__ == "__main__":
    main()
