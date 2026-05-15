"""Temporal extraction tests for the text/NER source (issue #112).

Covers DATE/TIME parsing (calendar dates, decades, centuries, ranges) and
named time-period resolution (ICS GTS2020 bundled gazetteer). Signed ISO
year strings (e.g. ``-9750-01-01``) are used for deep-time / pre-CE
mentions so the same path serves both archaeology/geology and CE dates.
"""

import os

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

TEXT_DIR = os.path.join(os.path.dirname(__file__), "testdata", "text")


@pytest.fixture(autouse=True)
def fake_gazetteer(monkeypatch):
    install_fake_gazetteer(monkeypatch)


def _temporal_kwargs(**extra):
    base = dict(
        bbox=False,
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


def test_tbox_iso_date_single_day():
    from geoextent.lib import extent

    result = extent.from_text("On 2024-05-12 the survey ran.", **_temporal_kwargs())
    assert result["tbox"] == ["2024-05-12", "2024-05-12"]


def test_tbox_decade_envelope():
    from geoextent.lib import extent

    result = extent.from_text(
        "The site was first surveyed in the 1990s.", **_temporal_kwargs()
    )
    assert result["tbox"] == ["1990-01-01", "1999-12-31"]


def test_tbox_range_split():
    from geoextent.lib import extent

    result = extent.from_text(
        "Monitoring ran between 2010 and 2015.", **_temporal_kwargs()
    )
    assert result["tbox"] == ["2010-01-01", "2015-12-31"]


def test_tbox_period_holocene():
    from geoextent.lib import extent

    result = extent.from_text(
        "Sediment cores cover the Holocene.", **_temporal_kwargs()
    )
    assert result["tbox"] == ["-9750-01-01", "1950-01-01"]
    rec = next(r for r in result["date_entities"] if r["kind"] == "period")
    assert rec["matched"] is True
    assert rec["gazetteer_id"] == "ics:Holocene"
    assert rec["gazetteer"] == "ics"


def test_tbox_period_pleistocene_caught_by_matcher():
    """spaCy NER misses 'Pleistocene' on en_core_web_sm; the PhraseMatcher
    still catches it via the bundled ICS index."""
    from geoextent.lib import extent

    result = extent.from_text(
        "Pleistocene cores below the modern surface.", **_temporal_kwargs()
    )
    assert "tbox" in result
    assert result["tbox"][1] == "-9750-01-01"  # Pleistocene end


def test_tbox_mixed_period_plus_date():
    from geoextent.lib import extent

    result = extent.from_text(
        "Cores from the Holocene with a re-survey in 2024-05-12.",
        **_temporal_kwargs(),
    )
    assert result["tbox"] == ["-9750-01-01", "2024-05-12"]
    kinds = [r["kind"] for r in result["date_entities"]]
    assert "period" in kinds and "date" in kinds


def test_no_period_resolution_disables_periods():
    from geoextent.lib import extent

    result = extent.from_text(
        "Cores from the Holocene and on 2024-05-12.",
        period_resolution=False,
        **_temporal_kwargs(),
    )
    # Date still parsed; period not resolved.
    period_recs = [r for r in result["date_entities"] if r["kind"] == "period"]
    assert period_recs == []
    assert result["tbox"] == ["2024-05-12", "2024-05-12"]


def test_late_cretaceous_multiword_phrase_match():
    from geoextent.lib import extent

    result = extent.from_text(
        "Late Cretaceous fossils dominate the section.", **_temporal_kwargs()
    )
    assert "tbox" in result
    rec = next(
        r
        for r in result["date_entities"]
        if r["kind"] == "period" and "Late Cretaceous" in r["text"]
    )
    assert rec["matched"] is True


def test_provenance_shape_periods():
    from geoextent.lib import extent

    result = extent.from_text("Mesozoic Era reptiles dominated.", **_temporal_kwargs())
    rec = next(r for r in result["date_entities"] if r["kind"] == "period")
    for key in (
        "text",
        "kind",
        "char_start",
        "char_end",
        "gazetteer",
        "matched",
        "candidate_count",
        "start",
        "end",
        "match_name",
        "gazetteer_id",
        "gazetteer_url",
    ):
        assert key in rec, f"missing key: {key}"


def test_phrasematcher_wins_over_place_overlap():
    """A bundled period name (e.g. 'Cambrian') is treated as a period even
    when spaCy NER might otherwise tag it as a place."""
    from geoextent.lib import extent

    result = extent.from_text(
        "Cambrian fossils are abundant.", **_temporal_kwargs(bbox=True)
    )
    assert "bbox" not in result
    rec = next(r for r in result["date_entities"] if r["kind"] == "period")
    assert rec["matched"] is True
    assert rec["gazetteer_id"] == "ics:Cambrian"


def test_signed_iso_tbox_merge_round_trip():
    """Multi-file directory with deep-time + CE dates merges via signed-ISO."""
    from geoextent.lib import extent

    result = extent.from_directory(
        TEXT_DIR,
        bbox=False,
        tbox=True,
        details=True,
        text_method="ner",
        ner_gazetteer="geonames",
        ner_ambiguity="top",
        ner_auto_download=False,
        period_ambiguity="top",
        legacy=True,
    )
    assert "tbox" in result
    # geo_periods.txt has Mesozoic Era → start at -251,900,050; the
    # merged tbox must reach that deep.
    assert result["tbox"][0].startswith("-")
    # CE end should be at least 2015 (from temporal.txt).
    assert result["tbox"][1] >= "2015-01-01"
