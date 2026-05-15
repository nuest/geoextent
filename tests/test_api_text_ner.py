"""Tests for text NER extraction (issue #112).

These tests are gated on spaCy + the small English model being available.
A FakeGazetteer is monkey-patched in to keep the tests deterministic and
network-free.
"""

import os

import pytest

spacy = pytest.importorskip("spacy")

from _text_ner_helpers import install_fake_gazetteer


def _model_available(name="en_core_web_sm"):
    try:
        spacy.load(name)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _model_available(),
    reason="spaCy model en_core_web_sm not installed",
)


TEXT_DIR = os.path.join(os.path.dirname(__file__), "testdata", "text")


@pytest.fixture(autouse=True)
def fake_gazetteer(monkeypatch):
    """Replace .geocode on every gazetteer service so no network is hit."""
    install_fake_gazetteer(monkeypatch)


def _make_kwargs(**extra):
    base = dict(
        bbox=True,
        text_method="ner",
        ner_gazetteer="geonames",
        ner_ambiguity="top",  # keep top hit for deterministic assertions
        ner_auto_download=False,
        legacy=True,  # use [lon, lat] order to make assertions easier
    )
    base.update(extra)
    return base


def test_from_text_inline_cities():
    from geoextent.lib import extent

    result = extent.from_text("Berlin, Paris, Tokyo", **_make_kwargs())
    assert result is not None
    assert "bbox" in result
    minlon, minlat, maxlon, maxlat = result["bbox"]
    # Tokyo east of Paris east of Berlin etc.
    assert minlon < 5 and maxlon > 130
    place_names = [p["name"].lower() for p in result["place_names"]]
    assert "berlin" in place_names
    assert "paris" in place_names
    assert "tokyo" in place_names
    for rec in result["place_names"]:
        if rec["name"].lower() in ("berlin", "paris", "tokyo"):
            assert rec["matched"] is True
            assert rec["gazetteer_id"].startswith("fake:")
            assert rec["gazetteer"] == "geonames"


def test_from_text_no_places_returns_no_bbox():
    from geoextent.lib import extent

    text = "This is plain prose with no geographic references."
    result = extent.from_text(text, **_make_kwargs())
    assert result is not None
    assert "bbox" not in result
    assert result["place_names"] == []


def test_from_file_text_routing():
    from geoextent.lib import extent

    path = os.path.join(TEXT_DIR, "cities.txt")
    result = extent.from_file(path, **_make_kwargs())
    assert result is not None
    assert result["geoextent_handler"] == "handle_text"
    assert "bbox" in result
    assert any(p["matched"] for p in result["place_names"])


def test_from_file_text_disabled_without_text_method():
    """Without --text-method, .txt files are not handled by handle_text."""
    from geoextent.lib import extent

    path = os.path.join(TEXT_DIR, "cities.txt")
    result = extent.from_file(path, bbox=True, tbox=False, legacy=True)
    # The CSV handler may still match the file (producing no coordinates),
    # but handle_text must not be invoked.
    if result is not None:
        assert result.get("geoextent_handler") != "handle_text"
        assert "bbox" not in result


def test_from_directory_text_files():
    from geoextent.lib import extent

    result = extent.from_directory(
        TEXT_DIR,
        bbox=True,
        details=True,
        **{
            "text_method": "ner",
            "ner_gazetteer": "geonames",
            "ner_ambiguity": "top",
            "ner_auto_download": False,
            "legacy": True,
        },
    )
    assert result is not None
    # Multiple files contributed; merge yields a wide envelope across cities.
    assert "bbox" in result
    minlon, minlat, maxlon, maxlat = result["bbox"]
    # Spans at least Germany ↔ Tokyo
    assert maxlon - minlon > 100


def test_ner_ambiguity_drop():
    from geoextent.lib import extent

    result = extent.from_text(
        "We met in Berlin and in Springfield to plan the experiment.",
        **_make_kwargs(ner_ambiguity="drop"),
    )
    # Berlin matches, Springfield is ambiguous → dropped
    matched = [p for p in result["place_names"] if p["matched"]]
    dropped = [p for p in result["place_names"] if not p["matched"]]
    matched_names = {p["name"].lower() for p in matched}
    dropped_names = {p["name"].lower() for p in dropped}
    assert "berlin" in matched_names
    assert "springfield" in dropped_names


def test_ner_ambiguity_top():
    from geoextent.lib import extent

    result = extent.from_text(
        "We met in Springfield.",
        **_make_kwargs(ner_ambiguity="top"),
    )
    matched_names = {p["name"].lower() for p in result["place_names"] if p["matched"]}
    assert "springfield" in matched_names


def test_ner_ambiguity_drop_emits_warning(caplog):
    """Dropping an ambiguous mention must log a WARNING hinting at --ner-ambiguity top."""
    import logging

    from geoextent.lib import extent, gazetteer as gaz

    # Reset the per-process de-dup set so the warning fires for this run.
    gaz._reset_ambiguity_warnings()

    caplog.set_level(logging.WARNING, logger="geoextent")
    extent.from_text(
        "We met in Springfield.",
        **_make_kwargs(ner_ambiguity="drop"),
    )
    messages = "\n".join(r.getMessage() for r in caplog.records)
    assert "Springfield" in messages
    # Both the CLI flag and the API kwarg are mentioned, so users learn the fix.
    assert "--ner-ambiguity top" in messages
    assert "ner_ambiguity='top'" in messages


def test_ner_ambiguity_drop_warning_deduplicates(caplog):
    """Repeated ambiguous mentions don't flood the log."""
    import logging

    from geoextent.lib import extent, gazetteer as gaz

    gaz._reset_ambiguity_warnings()
    caplog.set_level(logging.WARNING, logger="geoextent")
    # Same mention twice in one call + a second call must produce one WARNING.
    extent.from_text(
        "Springfield and Springfield met in Springfield.",
        **_make_kwargs(ner_ambiguity="drop"),
    )
    extent.from_text(
        "Another mention of Springfield.",
        **_make_kwargs(ner_ambiguity="drop"),
    )
    warnings = [
        r
        for r in caplog.records
        if r.levelno == logging.WARNING and "Springfield" in r.getMessage()
    ]
    assert len(warnings) == 1


def test_provenance_shape():
    from geoextent.lib import extent

    result = extent.from_text("The team flew from Berlin to Paris.", **_make_kwargs())
    rec = next(p for p in result["place_names"] if p["name"].lower() == "berlin")
    for key in (
        "name",
        "label",
        "char_start",
        "char_end",
        "score",
        "gazetteer",
        "matched",
        "candidate_count",
        "lat",
        "lon",
        "match_name",
        "gazetteer_id",
        "gazetteer_url",
    ):
        assert key in rec, f"missing provenance key: {key}"
    assert rec["label"] in ("LOC", "GPE")
    assert rec["matched"] is True


def test_temporal_from_dates():
    from geoextent.lib import extent

    text = "Field measurements in Berlin on 2024-05-12 and Paris on 14 June 2024."
    result = extent.from_text(text, tbox=True, **_make_kwargs())
    assert "tbox" in result
    start, end = result["tbox"]
    assert start <= "2024-05-12"
    assert end >= "2024-06-14"


def test_text_extensions_have_single_source_of_truth():
    """All three call sites that need the plain-text extension set
    (``is_text_file`` mime guard, ``handle_csv`` deferral rule, and the
    ``features.py`` capability listing under ``--list-features``) must
    import the same constant from ``text_extraction.mime``. Inline
    duplicates have drifted in the past — guard against regression.
    """
    from geoextent.lib.text_extraction.mime import TEXT_EXTENSIONS
    from geoextent.lib import features

    # 1) The canonical set lives in mime.py and is non-empty.
    assert isinstance(TEXT_EXTENSIONS, frozenset)
    assert ".txt" in TEXT_EXTENSIONS and ".md" in TEXT_EXTENSIONS

    # 2) features.py exposes the same set, sorted, in its handler spec.
    spec = features.get_supported_features()
    text_spec = next(
        h for h in spec["file_formats"] if h.get("handler") == "handle_text"
    )
    assert set(text_spec["file_extensions"]) == set(TEXT_EXTENSIONS)

    # 3) handle_csv's deferral rule references the same set. Reading
    #    source is the cleanest way to detect an accidentally re-inlined
    #    duplicate set literal.
    import inspect
    from geoextent.lib import handle_csv

    src = inspect.getsource(handle_csv)
    assert "from .text_extraction.mime import TEXT_EXTENSIONS" in src, (
        "handle_csv must import TEXT_EXTENSIONS from text_extraction.mime "
        "instead of re-inlining the set"
    )
    # No inline {".txt", ".md", ...} literal in handle_csv (catch drift).
    assert '".txt", ".md", ".markdown"' not in src
