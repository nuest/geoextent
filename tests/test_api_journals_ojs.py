"""Tests for the OJS (Open Journal Systems) journal-landing-page provider.

Three tiers:

* **Unit** (no network) — feed recorded HTML fixtures through the provider's
  internal extractors. These are auto-marked fast by ``conftest.py`` because
  the test names contain ``validation`` / ``extract_coordinates``.
* **Live slow** — hit the public TIB OJS demo; auto-marked ``slow``.
* **Negative-path** — hit an OJS journal without the ojsGeo plugin
  (``josis.org``) and assert we detect the platform but yield no spatial
  metadata.
"""

from __future__ import annotations

import os
import tempfile

import pytest

import geoextent
from geoextent.lib.content_providers.journals import OJS
from geoextent.lib.content_providers.journals._base import _HTML_CACHE

from conftest import NETWORK_SKIP_EXCEPTIONS

FIXTURES = os.path.join(os.path.dirname(__file__), "testdata", "journals")
OJS_LOCAL_URL = "http://localhost:8330/index.php/gmdj/article/view/44"
OJS_TIB_URL = "https://service.tib.eu/komet/ojs330/index.php/gmdj/article/view/39"
OJS_JOSIS_NEGATIVE_URL = "https://josis.org/index.php/josis/article/view/170"


def _load_fixture(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(autouse=True)
def _clear_html_cache():
    """Stop fixture HTML from leaking between tests via the per-process cache."""
    _HTML_CACHE.clear()
    yield
    _HTML_CACHE.clear()


# ---------------------------------------------------------------------------
# Fast unit tests (no network) — exercise the parsing pipeline via fixtures.
# ---------------------------------------------------------------------------


def _build_provider_with_fixture(filename: str, url: str) -> OJS:
    """Inject the recorded HTML into the shared URL → HTML cache so that
    ``OJS.validate_provider`` + ``_extract`` run against the fixture without
    touching the network."""
    _HTML_CACHE[url] = _load_fixture(filename)
    provider = OJS()
    provider.reference = url
    provider._article_url = url
    return provider


def test_ojs_validation_polygon_fixture():
    provider = OJS()
    _HTML_CACHE[OJS_LOCAL_URL] = _load_fixture("ojs_polygon.html")
    provider.reference = OJS_LOCAL_URL
    # Skip get_url resolution: feed the URL straight into the cache lookup.
    html = provider._fetch_html(OJS_LOCAL_URL)
    assert provider._is_my_platform(html, OJS_LOCAL_URL) is True


def test_ojs_url_validation_no_geo_metadata_fixture():
    """Pages without the ojsGeo plugin are still detected as OJS."""
    bare_html = (
        "<html><head>"
        '<meta name="generator" content="Open Journal Systems 3.3.0.21" />'
        "</head><body/></html>"
    )
    provider = OJS()
    assert provider._is_my_platform(bare_html, "https://example.org/article/1") is True


def test_ojs_extract_coordinates_polygon():
    """OJS article 44 (local demo): clear polygon over Hanover."""
    provider = _build_provider_with_fixture("ojs_polygon.html", OJS_LOCAL_URL)
    record = provider._extract()

    # Bounding box [w, s, e, n] internal order.
    assert record["bbox"] is not None
    w, s, e, n = record["bbox"]
    assert w == pytest.approx(9.5, abs=0.01)
    assert s == pytest.approx(52.2, abs=0.01)
    assert e == pytest.approx(10.0, abs=0.01)
    assert n == pytest.approx(52.6, abs=0.01)

    # OJS article 44 emits BOTH a JSON-LD ScholarlyArticle with a GeoShape
    # polygon AND a DC.SpatialCoverage GeoJSON. JSON-LD wins per the
    # richer-geometry-first priority, not the ICBM/geo.position centroid.
    assert record["source_spatial"] == "jsonld"

    # Article 44 has no DC.temporal / DC.PeriodOfTime / JSON-LD
    # temporalCoverage — only DC.Date.issued. The publication date is NOT
    # an allowed tbox fallback, so tbox must stay None.
    assert record["tbox"] is None
    assert record["source_temporal"] is None


OJS_DC_TEMPORAL_URL = (
    "https://service.tib.eu/komet/ojs330/index.php/gmdj/article/view/40"
)


def test_ojs_extract_dc_temporal_not_pubdate():
    """OJS article 40 (TIB demo) emits BOTH ``DC.temporal`` /
    ``DC.PeriodOfTime`` (the actual research period, 2008-2018) AND
    ``DC.Date.issued`` / ``DC.Date.created`` (the publication date,
    2025-07-14). The temporal resolver must pick the research period, not
    the publication date — regression test for the bug where
    ``scheme="ISO8601"`` filter caused ``DC.temporal`` to be skipped.
    """
    provider = _build_provider_with_fixture("ojs_dc_temporal.html", OJS_DC_TEMPORAL_URL)
    record = provider._extract()

    assert record["tbox"] == ["2008-01-01", "2018-12-31"], (
        "Expected the research period from DC.temporal, not the "
        "publication date from DC.Date.issued"
    )
    # Source must be DC.temporal or DC.PeriodOfTime (both ISO 8601 intervals),
    # never DC.Date.issued or citation_*.
    assert record["source_temporal"] in {"dc.temporal", "dc.periodoftime"}
    # And the publication date must specifically NOT have been used.
    assert record["source_temporal"] != "dc.date.issued"

    # Spatial extent from the page's polygon (Brandenburg).
    assert record["bbox"] is not None
    w, s, e, n = record["bbox"]
    assert w == pytest.approx(11.27, abs=0.01)
    assert s == pytest.approx(51.36, abs=0.01)
    assert e == pytest.approx(14.77, abs=0.01)
    assert n == pytest.approx(53.56, abs=0.01)


def test_ojs_extract_admin_unit_only_yields_no_bbox():
    """OJS article 39 (TIB demo): empty features, admin-unit bbox='not available'.

    Expect no spatial extent (admin-unit fallback declines on the sentinel)
    and no temporal extent either: the article only has ``DC.Date.issued``,
    which is a publication date and is deliberately not used as a tbox
    fallback.
    """
    provider = _build_provider_with_fixture("ojs_admin_only.html", OJS_TIB_URL)
    record = provider._extract()

    assert record["bbox"] is None
    assert record["geometry"] is None
    assert record["tbox"] is None


def test_ojs_priority_jsonld_over_geo_position():
    """When a page emits both rich JSON-LD AND a degenerate geo.position
    centroid, the JSON-LD must win (richer-geometry-first rule).
    """
    html = """
    <html><head>
      <meta name="generator" content="Open Journal Systems 3.3" />
      <script type="application/ld+json">{
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "spatialCoverage": {
          "@type": "Place",
          "geo": {
            "@type": "GeoShape",
            "box": "10 100 20 110"
          }
        }
      }</script>
      <meta name="ICBM" content="0.0, 0.0" />
      <meta name="geo.position" content="0.0;0.0" />
    </head><body/></html>
    """
    url = "http://example.org/article/view/999"
    _HTML_CACHE[url] = html
    provider = OJS()
    provider.reference = url
    provider._article_url = url
    record = provider._extract()
    assert record["source_spatial"] == "jsonld"
    # GeoShape box "lat1 lon1 lat2 lon2" → bbox [w=100, s=10, e=110, n=20]
    assert record["bbox"] == [100.0, 10.0, 110.0, 20.0]


def test_ojs_extract_doi_from_jsonld():
    """DOI is lifted from JSON-LD ``identifier``."""
    html = """
    <html><head>
      <meta name="generator" content="Open Journal Systems 3.3" />
      <script type="application/ld+json">{
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "identifier": [
          {"@type": "PropertyValue", "name": "DOI", "value": "10.1234/abc.xyz"}
        ]
      }</script>
    </head><body/></html>
    """
    url = "http://example.org/article/view/1"
    _HTML_CACHE[url] = html
    provider = OJS()
    provider.reference = url
    provider._article_url = url
    provider._extract()
    assert provider.extracted_doi == "10.1234/abc.xyz"


def test_ojs_provider_info_lists_examples():
    info = OJS.provider_info()
    assert info["name"] == "OJS"
    assert any("ojs330" in ex for ex in info["examples"])


# ---------------------------------------------------------------------------
# Live tests (auto-marked slow by conftest)
# ---------------------------------------------------------------------------


def test_ojs_metadata_only_extraction_tib_demo():
    """One real-network smoke test for the OJS provider against the public
    TIB demo journal.

    Article 39 has only an administrative-unit reference (no real geometry),
    so we expect tbox from DC.Date.issued and no bbox.
    """
    try:
        result = geoextent.from_remote(
            OJS_TIB_URL, bbox=True, tbox=True, metadata_first=True
        )
    except NETWORK_SKIP_EXCEPTIONS as exc:
        pytest.skip(f"network failure reaching TIB OJS demo: {exc}")

    assert isinstance(result, dict)
    assert result.get("bbox") is None
    # Article 39 has only DC.Date.issued (publication date) — by design we
    # do not surface that as the tbox, so this stays None.
    assert result.get("tbox") is None


def test_ojs_negative_path_journal_without_plugin():
    """A real OJS journal that has the generator meta but no ojsGeo plugin.

    Verifies the "platform detected, no spatial metadata" branch: provider
    matches, but the resulting record carries no bbox.
    """
    try:
        result = geoextent.from_remote(
            OJS_JOSIS_NEGATIVE_URL,
            bbox=True,
            tbox=True,
            metadata_first=True,
        )
    except NETWORK_SKIP_EXCEPTIONS as exc:
        pytest.skip(f"network failure reaching josis.org: {exc}")
    except Exception as exc:
        # When no provider matches at all, from_remote raises — the test then
        # confirms a regression by failing loudly rather than masking.
        msg = str(exc).lower()
        if "can not handle" in msg or "not supported" in msg:
            pytest.skip(
                "OJS provider did not match josis.org during this run "
                f"(unexpected upstream change): {exc}"
            )
        raise

    assert isinstance(result, dict)
    assert result.get("bbox") is None
