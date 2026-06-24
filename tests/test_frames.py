from PIL import Image

from yt_tutor.pipeline.frames import dedup_frames, dhash, hamming, is_new_keyframe


def _img(tmp, name, fn):
    p = tmp / name
    im = Image.new("L", (16, 16))
    for y in range(16):
        for x in range(16):
            im.putpixel((x, y), fn(x, y))
    im.save(p)
    return p


def test_hamming():
    assert hamming(0b1010, 0b0011) == 2
    assert hamming(7, 7) == 0


def test_first_frame_is_always_a_keyframe():
    assert is_new_keyframe(None, 123, 10) is True


def test_threshold_is_inclusive_boundary():
    a, b = 0, 0b111111  # differ by 6 bits
    assert is_new_keyframe(a, b, 10) is False  # 6 is NOT > 10
    assert is_new_keyframe(a, b, 6) is False   # 6 is NOT > 6
    assert is_new_keyframe(a, b, 5) is True    # 6 > 5


def test_dhash_identical_is_zero_distance(tmp_path):
    p = _img(tmp_path, "grad.png", lambda x, y: (x * 16) % 256)
    assert hamming(dhash(p), dhash(p)) == 0


def test_dhash_distinguishes_structure(tmp_path):
    horiz = _img(tmp_path, "h.png", lambda x, y: (x * 16) % 256)  # gradient left->right
    vert = _img(tmp_path, "v.png", lambda x, y: (y * 16) % 256)   # gradient top->bottom
    assert hamming(dhash(horiz), dhash(vert)) > 0


def test_dedup_marks_duplicates_against_anchor(tmp_path):
    # frame 0: distinct; frames 1-2: identical to 0; frame 3: distinct again
    a = _img(tmp_path, "a.png", lambda x, y: (x * 16) % 256)
    b = _img(tmp_path, "b.png", lambda x, y: (y * 16) % 256)
    frames = [(1, 0, a), (2, 1, a), (3, 2, a), (4, 3, b)]
    rows = dedup_frames(frames, threshold=10)
    flags = [r["is_keyframe"] for r in rows]
    assert flags == [1, 0, 0, 1]              # only true scene changes are keyframes
    assert rows[1]["duplicate_of"] == 0       # dupes point back to the anchor's ts
    assert rows[2]["duplicate_of"] == 0
    assert rows[3]["duplicate_of"] is None
