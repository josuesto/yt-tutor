import json

from yt_tutor.db import visual_texts_for_frame


def test_display_is_concise_index_includes_ocr_and_notable():
    row = {
        "scene_description": "a dense bullet slide titled Q3 What info will I need",
        "screen_or_slide_summary": "lists the fields a CFP submission asks for",
        "visible_text": json.dumps(["Talk Title", "Talk Abstract", "accessibility requirements", "github repos"]),
        "notable_details_json": json.dumps(["Talk Title is bold"]),
        "vision_summary": "ignored when scene present",
    }
    display, index = visual_texts_for_frame(row)
    # display = the concise scene line, not the OCR dump
    assert display == "a dense bullet slide titled Q3 What info will I need"
    assert "accessibility requirements" not in display
    # index = searchable, carrying the on-screen words and notable details
    assert "accessibility requirements" in index
    assert "github repos" in index
    assert "Talk Title is bold" in index


def test_falls_back_and_tolerates_missing_or_null_fields():
    # only a vision_summary present (e.g. a headless --vision frame); no crash
    row = {"scene_description": None, "screen_or_slide_summary": None,
           "visible_text": None, "notable_details_json": None, "vision_summary": "a closing slide"}
    display, index = visual_texts_for_frame(row)
    assert display == "a closing slide"
    assert index == "a closing slide"


def test_bad_json_does_not_raise():
    row = {"scene_description": "x", "screen_or_slide_summary": "",
           "visible_text": "{not valid json", "notable_details_json": None, "vision_summary": None}
    display, index = visual_texts_for_frame(row)
    assert display == "x"
    assert index == "x"
