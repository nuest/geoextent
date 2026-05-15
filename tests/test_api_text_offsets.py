"""Offset and source_text contract tests (issue #112).

Each match in ``place_names`` and ``date_entities`` carries
``char_start``/``char_end`` indices into the NFC-normalised ``source_text``.
These tests pin the contract:

- Slicing ``source_text[char_start:char_end]`` reproduces the surface form.
- The pipeline normalises input to NFC even if the caller supplied NFD.
- BOMs are stripped before offsets are computed.
- Overlapping matches favour the longer span (period beats overlapping place).
"""

import unicodedata

import pytest

spacy = pytest.importorskip("spacy")

from _text_ner_helpers import install_fake_gazetteer  # noqa: E402


def _model_available(name="en_core_web_sm"):
    try:
        spacy.load(name)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _model_available(), reason="spaCy model en_core_web_sm not installed"
)


@pytest.fixture(autouse=True)
def fake_gazetteer(monkeypatch):
    install_fake_gazetteer(monkeypatch)


def _kwargs(**extra):
    base = dict(
        bbox=True,
        tbox=True,
        text_method="ner",
        ner_gazetteer="geonames",
        ner_ambiguity="top",
        ner_auto_download=False,
        period_ambiguity="top",
        legacy=True,
    )
    base.update(extra)
    return base


def test_offsets_round_trip_to_surface_form():
    from geoextent.lib import extent

    text = "Sediment cores in Berlin span the Holocene; resurvey on 2024-05-12."
    res = extent.from_text(text, **_kwargs())
    assert res["source_text"] == text
    for rec in res["place_names"]:
        s, e = rec["char_start"], rec["char_end"]
        assert text[s:e] == rec["name"]
    for rec in res["date_entities"]:
        s, e = rec["char_start"], rec["char_end"]
        assert text[s:e] == rec["text"]


def test_source_offset_unit_and_normalisation_declared():
    from geoextent.lib import extent

    res = extent.from_text("Berlin in 1990.", **_kwargs())
    assert res["source_offset_unit"] == "python_codepoint"
    assert res["source_normalisation"] == "nfc"


def test_nfd_input_normalised_to_nfc():
    """An NFD-composed input (combining diacritic) round-trips after NFC."""
    from geoextent.lib import extent

    nfd = unicodedata.normalize("NFD", "München in 1990.")
    assert nfd != unicodedata.normalize("NFC", nfd), "fixture must differ across forms"
    res = extent.from_text(nfd, **_kwargs())
    assert unicodedata.is_normalized("NFC", res["source_text"])
    # Slicing the echoed source by the offsets must reproduce the surface.
    for rec in res["place_names"] + res["date_entities"]:
        surface = res["source_text"][rec["char_start"] : rec["char_end"]]
        expected = rec.get("name") or rec.get("text")
        assert surface == expected


def test_bom_stripped_from_source_text():
    from geoextent.lib import extent

    text_with_bom = "﻿Berlin in 1990."
    res = extent.from_text(text_with_bom, **_kwargs())
    assert not res["source_text"].startswith("﻿")
    for rec in res["place_names"]:
        surface = res["source_text"][rec["char_start"] : rec["char_end"]]
        assert surface == rec["name"]


def test_no_source_text_opts_out_of_echo():
    from geoextent.lib import extent

    res = extent.from_text("Berlin in 1990.", include_source_text=False, **_kwargs())
    assert "source_text" not in res
    assert "source_offset_unit" not in res
    # Provenance offsets are still emitted, just into a source the caller must keep.
    assert res["place_names"][0]["char_start"] >= 0


def test_phrasematcher_overlap_drops_overlapped_place():
    """When a period match overlaps a place-class entity, the place is dropped."""
    from geoextent.lib import extent

    # 'Cambrian' is an ICS period; spaCy may tag it as a place. The
    # PhraseMatcher wins and the place entry must not appear.
    res = extent.from_text("Cambrian fossils are abundant.", **_kwargs())
    place_names = res.get("place_names", [])
    assert all(p.get("name", "").lower() != "cambrian" for p in place_names)


def test_multiple_periods_distinct_offsets():
    from geoextent.lib import extent

    text = "The Holocene contains the Pleistocene-Holocene transition."
    res = extent.from_text(text, **_kwargs())
    period_recs = [r for r in res["date_entities"] if r["kind"] == "period"]
    offsets = sorted((r["char_start"], r["char_end"]) for r in period_recs)
    # Each unique span appears exactly once; no zero-width or overlapping
    # ranges leak through (PhraseMatcher long-wins resolves these).
    assert len(offsets) == len(set(offsets))
    for s, e in offsets:
        assert e > s
