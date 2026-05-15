"""Tests for ``geoextent.lib.annotate`` rendering (issue #112).

Covers both library-level rendering (``render_annotated_text``) and the
CLI ``--annotate {auto,ansi,brackets,off}`` flag. The library tests don't
need spaCy or a gazetteer — they construct minimal result dicts directly,
so they run even when the NER pipeline is unavailable.
"""

import json
import re

import pytest


from geoextent.lib.annotate import (
    DEFAULT_CLASSES,
    parse_classes,
    render_annotated_text,
    resolve_mode,
)


def _result(text, *, places=(), dates=()):
    place_names = [
        {
            "name": p["name"],
            "char_start": p["char_start"],
            "char_end": p["char_end"],
            "matched": p.get("matched", True),
        }
        for p in places
    ]
    date_entities = [
        {
            "text": d["text"],
            "kind": d.get("kind", "date"),
            "char_start": d["char_start"],
            "char_end": d["char_end"],
            "matched": d.get("matched", True),
        }
        for d in dates
    ]
    return {
        "source_text": text,
        "source_offset_unit": "python_codepoint",
        "source_normalisation": "nfc",
        "place_names": place_names,
        "date_entities": date_entities,
    }


def test_brackets_basic():
    text = "Cores in Berlin span the Holocene; resurvey on 2024-05-12."
    res = _result(
        text,
        places=[{"name": "Berlin", "char_start": 9, "char_end": 15}],
        dates=[
            {"text": "Holocene", "kind": "period", "char_start": 25, "char_end": 33},
            {"text": "2024-05-12", "kind": "date", "char_start": 47, "char_end": 57},
        ],
    )
    assert text[9:15] == "Berlin"
    out = render_annotated_text(res, mode="brackets")
    assert "[[Berlin|place]]" in out
    assert "[[Holocene|period]]" in out
    assert "[[2024-05-12|date]]" in out


def test_ansi_basic():
    text = "Berlin in 1990."
    res = _result(
        text,
        places=[{"name": "Berlin", "char_start": 0, "char_end": 6}],
        dates=[{"text": "1990", "char_start": 10, "char_end": 14}],
    )
    out = render_annotated_text(res, mode="ansi")
    # Must contain SGR open + reset around each match. Cyan default for place,
    # yellow for date.
    assert "\x1b[1;36m" in out and "\x1b[1;33m" in out
    assert out.count("\x1b[0m") == 2


def test_off_returns_none():
    res = _result(
        "Berlin in 1990.", places=[{"name": "Berlin", "char_start": 0, "char_end": 6}]
    )
    assert render_annotated_text(res, mode="off") is None


def test_unknown_mode_raises():
    res = _result("Berlin", places=[{"name": "Berlin", "char_start": 0, "char_end": 6}])
    with pytest.raises(ValueError):
        render_annotated_text(res, mode="bogus")


def test_overlap_long_wins():
    text = "Late Cretaceous fossils are common."
    res = _result(
        text,
        # Simulate two overlapping period matches: "Late Cretaceous" (longer)
        # and "Cretaceous" (subset). Only the longer one must be rendered.
        dates=[
            {"text": "Cretaceous", "kind": "period", "char_start": 5, "char_end": 15},
            {
                "text": "Late Cretaceous",
                "kind": "period",
                "char_start": 0,
                "char_end": 15,
            },
        ],
    )
    out = render_annotated_text(res, mode="brackets")
    assert out.count("[[Late Cretaceous|period]]") == 1
    assert "[[Cretaceous|period]]" not in out  # subset dropped


def test_no_source_text_returns_none():
    res = {"place_names": [], "date_entities": []}
    assert render_annotated_text(res, mode="brackets") is None


def test_classes_override_via_parse_classes():
    mapping = parse_classes("place=red,date=green,period=blue")
    assert mapping["place"] == "red"
    assert mapping["date"] == "green"
    assert mapping["period"] == "blue"


def test_parse_classes_empty_returns_defaults():
    assert parse_classes(None) == DEFAULT_CLASSES
    assert parse_classes("") == DEFAULT_CLASSES


def test_classes_used_in_render():
    text = "Berlin."
    res = _result(text, places=[{"name": "Berlin", "char_start": 0, "char_end": 6}])
    out = render_annotated_text(res, mode="ansi", classes={"place": "red"})
    # red = SGR 31
    assert "\x1b[1;31m" in out


def test_resolve_mode_auto_with_tty(monkeypatch):
    class _FakeTTY:
        def isatty(self):
            return True

    assert resolve_mode("auto", stream=_FakeTTY()) == "ansi"


def test_resolve_mode_auto_without_tty():
    class _NotTTY:
        def isatty(self):
            return False

    assert resolve_mode("auto", stream=_NotTTY()) == "brackets"


def test_offsets_outside_bounds_skipped():
    text = "Berlin."
    res = _result(
        text,
        places=[
            {"name": "Berlin", "char_start": 0, "char_end": 6},
            {"name": "Berlin", "char_start": 100, "char_end": 200},  # bogus
        ],
    )
    out = render_annotated_text(res, mode="brackets")
    # Renders the valid one, silently drops the bogus one.
    assert "[[Berlin|place]]" in out
    assert out.count("[[Berlin|place]]") == 1


# -----------------------------------------------------------------------------
# CLI integration (only runs when spaCy is available).
# -----------------------------------------------------------------------------

spacy = pytest.importorskip("spacy")
from _text_ner_helpers import install_fake_gazetteer  # noqa: E402


def _model_available(name="en_core_web_sm"):
    try:
        spacy.load(name)
        return True
    except Exception:
        return False


cli_pytestmark = pytest.mark.skipif(
    not _model_available(), reason="spaCy model en_core_web_sm not installed"
)


@pytest.fixture()
def fake_gazetteer(monkeypatch):
    install_fake_gazetteer(monkeypatch)


@cli_pytestmark
def test_cli_annotate_brackets(script_runner, fake_gazetteer):
    ret = script_runner.run(
        [
            "geoextent",
            "-b",
            "--quiet",
            "--text-method",
            "ner",
            "--ner-ambiguity",
            "top",
            "--no-auto-download",
            "--legacy",
            "--annotate",
            "brackets",
            "--text",
            "Berlin and the Holocene.",
        ]
    )
    assert ret.success, ret.stderr
    # JSON line first, annotated source after a header.
    assert "---annotated source (brackets)---" in ret.stdout
    annotated = ret.stdout.split("---annotated source (brackets)---", 1)[1].strip()
    assert "[[Berlin|place]]" in annotated
    assert "[[Holocene|period]]" in annotated


@cli_pytestmark
def test_cli_annotate_off(script_runner, fake_gazetteer):
    ret = script_runner.run(
        [
            "geoextent",
            "-b",
            "--quiet",
            "--text-method",
            "ner",
            "--ner-ambiguity",
            "top",
            "--no-auto-download",
            "--legacy",
            "--annotate",
            "off",
            "--text",
            "Berlin.",
        ]
    )
    assert ret.success
    assert "---annotated source" not in ret.stdout


@cli_pytestmark
def test_cli_annotate_ansi_classes(script_runner, fake_gazetteer):
    ret = script_runner.run(
        [
            "geoextent",
            "-b",
            "--quiet",
            "--text-method",
            "ner",
            "--ner-ambiguity",
            "top",
            "--no-auto-download",
            "--legacy",
            "--annotate",
            "ansi",
            "--annotate-classes",
            "place=red",
            "--text",
            "Berlin.",
        ]
    )
    assert ret.success
    assert "\x1b[1;31m" in ret.stdout  # red, per the override


@cli_pytestmark
def test_cli_no_source_text(script_runner, fake_gazetteer):
    ret = script_runner.run(
        [
            "geoextent",
            "-b",
            "--quiet",
            "--text-method",
            "ner",
            "--ner-ambiguity",
            "top",
            "--no-auto-download",
            "--legacy",
            "--no-source-text",
            "--annotate",
            "off",
            "--text",
            "Berlin.",
        ]
    )
    assert ret.success
    payload = json.loads(ret.stdout)
    feature_props = payload["features"][0]["properties"]
    assert "source_text" not in feature_props
