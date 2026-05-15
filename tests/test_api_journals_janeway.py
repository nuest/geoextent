"""Tests for the Janeway journal-landing-page provider.

Fixture used: ``janeway_full.html`` captured from the local Janeway demo
(``http://localhost:8000/dqj/article/id/251/``). The article has the full
suite of meta-tag encodings emitted by the ``janeway_geometadata`` plugin —
DC.SpatialCoverage (WKT + GeoJSON), DC.box, ISO 19139, JSON-LD
ScholarlyArticle with ``spatialCoverage`` Place, and a geo+json
``<link rel="alternate">``.
"""

from __future__ import annotations

import os

import pytest

import geoextent
from geoextent.lib.content_providers.journals import Janeway
from geoextent.lib.content_providers.journals._base import _HTML_CACHE

from conftest import NETWORK_SKIP_EXCEPTIONS

FIXTURES = os.path.join(os.path.dirname(__file__), "testdata", "journals")
JANEWAY_LOCAL_URL = "http://localhost:8000/dqj/article/id/251/"


def _load_fixture(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(autouse=True)
def _clear_html_cache():
    _HTML_CACHE.clear()
    yield
    _HTML_CACHE.clear()


# ---------------------------------------------------------------------------
# Fast unit tests (no network)
# ---------------------------------------------------------------------------


def test_janeway_url_validation_geo_json_link():
    """A geo+json alternate link is a strong positive."""
    html = (
        "<html><head>"
        '<link rel="alternate" type="application/geo+json" '
        'href="/plugins/geometadata/download/article/1/geojson/" />'
        "</head><body/></html>"
    )
    provider = Janeway()
    assert provider._is_my_platform(html, "http://example.org/x/article/id/1/") is True


def test_janeway_url_validation_static_path_heuristic():
    """Static asset path plus /article/id/ URL pattern is also accepted."""
    html = "<html><head><link rel='stylesheet' href='/static/geometadata/css/x.css' /></head><body/></html>"
    url = "http://example.org/journalcode/article/id/42/"
    provider = Janeway()
    assert provider._is_my_platform(html, url) is True


def test_janeway_extract_coordinates_full_fixture():
    """Janeway article 251 emits a Laos polygon via both WKT and GeoJSON.

    Expected bbox follows the fixture's POLYGON((100.1 13.9, 107.7 13.9,
    107.7 22.5, 100.1 22.5, 100.1 13.9)). Source must be JSON-LD or
    DC.SpatialCoverage:geojson (not DC.box) per the richer-geometry-first
    priority.
    """
    _HTML_CACHE[JANEWAY_LOCAL_URL] = _load_fixture("janeway_full.html")
    provider = Janeway()
    provider.reference = JANEWAY_LOCAL_URL
    provider._article_url = JANEWAY_LOCAL_URL

    record = provider._extract()

    assert record["bbox"] is not None
    w, s, e, n = record["bbox"]
    assert w == pytest.approx(100.1, abs=0.01)
    assert s == pytest.approx(13.9, abs=0.01)
    assert e == pytest.approx(107.7, abs=0.01)
    assert n == pytest.approx(22.5, abs=0.01)

    # Must come from a polygon-carrying source, never the bbox-only fallbacks.
    assert record["source_spatial"] in {
        "jsonld",
        "alternate-link",
        "dc.spatialcoverage:geojson",
        "dc.spatialcoverage:wkt",
    }

    # ``temporal_periods`` is empty on this fixture and DC.temporal /
    # DC.PeriodOfTime are absent — so there is no research-period source.
    # The publication date (``DC.Date.issued``) is NOT an allowed fallback,
    # so tbox stays None.
    assert record["tbox"] is None


def test_iso19139_parser_is_namespace_prefix_agnostic():
    """The ISO 19139 parser must look up elements by *local* name, not by
    literal prefix. Same content, different prefixes → identical bbox.
    """
    from geoextent.lib.content_providers.journals._meta import parse_iso19139_bbox

    canonical = (
        "<gmd:EX_GeographicBoundingBox>"
        "<gmd:westBoundLongitude><gco:Decimal>100.1</gco:Decimal></gmd:westBoundLongitude>"
        "<gmd:eastBoundLongitude><gco:Decimal>107.7</gco:Decimal></gmd:eastBoundLongitude>"
        "<gmd:southBoundLatitude><gco:Decimal>13.9</gco:Decimal></gmd:southBoundLatitude>"
        "<gmd:northBoundLatitude><gco:Decimal>22.5</gco:Decimal></gmd:northBoundLatitude>"
        "</gmd:EX_GeographicBoundingBox>"
    )
    renamed = canonical.replace("gmd:", "ns0:").replace("gco:", "ns1:")
    no_prefix = canonical.replace("gmd:", "").replace("gco:", "")

    expected = [100.1, 13.9, 107.7, 22.5]
    assert parse_iso19139_bbox(canonical) == expected
    assert parse_iso19139_bbox(renamed) == expected
    assert parse_iso19139_bbox(no_prefix) == expected


def test_iso19139_parser_handles_html_escaped_input():
    """The ISO 19139 snippet arrives HTML-escaped from the meta tag's
    ``content`` attribute; the parser must un-escape before reading XML.
    """
    from html import escape

    from geoextent.lib.content_providers.journals._meta import parse_iso19139_bbox

    canonical = (
        "<gmd:EX_GeographicBoundingBox>"
        "<gmd:westBoundLongitude><gco:Decimal>-180</gco:Decimal></gmd:westBoundLongitude>"
        "<gmd:eastBoundLongitude><gco:Decimal>180</gco:Decimal></gmd:eastBoundLongitude>"
        "<gmd:southBoundLatitude><gco:Decimal>-90</gco:Decimal></gmd:southBoundLatitude>"
        "<gmd:northBoundLatitude><gco:Decimal>90</gco:Decimal></gmd:northBoundLatitude>"
        "</gmd:EX_GeographicBoundingBox>"
    )
    assert parse_iso19139_bbox(escape(canonical)) == [-180.0, -90.0, 180.0, 90.0]


def test_janeway_provider_info():
    info = Janeway.provider_info()
    assert info["name"] == "Janeway"
    assert any("article/id" in ex for ex in info["examples"])


# ---------------------------------------------------------------------------
# Live test (auto-marked slow). Skipped when the local Janeway dev server is
# not reachable — there is no public Janeway+plugin instance to point at.
# ---------------------------------------------------------------------------


def test_janeway_metadata_only_extraction_local_demo():
    try:
        result = geoextent.from_remote(
            JANEWAY_LOCAL_URL, bbox=True, tbox=True, metadata_first=True
        )
    except NETWORK_SKIP_EXCEPTIONS as exc:
        pytest.skip(
            f"network failure / Janeway dev server unreachable at {JANEWAY_LOCAL_URL}: {exc}"
        )
    except Exception as exc:
        msg = str(exc).lower()
        # When the local Janeway dev server is not running, ``from_remote``
        # cycles through every provider, none claim the URL, and the call
        # finally raises one of these wrappers — all of which mean
        # "unreachable / no provider", not "regression".
        if (
            "can not handle" in msg
            or "connection" in msg
            or "refused" in msg
            or "failed to extract" in msg
        ):
            pytest.skip(f"Janeway dev server not running: {exc}")
        raise

    assert isinstance(result, dict)
    bbox = result.get("bbox")
    assert bbox is not None
    # bbox is returned in EPSG:4326 native [lat, lon] order at the public API.
    minlat, minlon, maxlat, maxlon = bbox
    assert minlat == pytest.approx(13.9, abs=0.05)
    assert maxlat == pytest.approx(22.5, abs=0.05)
    assert minlon == pytest.approx(100.1, abs=0.05)
    assert maxlon == pytest.approx(107.7, abs=0.05)
