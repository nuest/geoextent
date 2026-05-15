"""Boundary-geometry support for the text/NER source (issue #112).

When the place gazetteer returns a polygon for a hit (Nominatim does for
administrative regions), geoextent uses the polygon's envelope for the
spatial extent instead of the centroid point. ``--place-geometry``
controls the policy:

- ``auto`` (default) — use the polygon when present, fall back to point.
- ``boundary`` — same; tests cover the same fixture path here.
- ``point`` — always use the centroid, even when a polygon is available.
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


@pytest.fixture(autouse=True)
def fake_gazetteer(monkeypatch):
    install_fake_gazetteer(monkeypatch)


def _kwargs(**extra):
    base = dict(
        bbox=True,
        text_method="ner",
        ner_gazetteer="nominatim",
        ner_ambiguity="top",
        ner_auto_download=False,
        legacy=True,
    )
    base.update(extra)
    return base


def test_boundary_envelope_used_for_areal_hit():
    """A polygon from the gazetteer drives the bbox, not the centroid."""
    from geoextent.lib import extent

    result = extent.from_text("Field campaign in Saxony", **_kwargs())
    bbox = result["bbox"]
    # Fake Saxony polygon spans [11.87..15.04, 50.17..51.69]
    assert bbox == [11.87, 50.17, 15.04, 51.69]


def test_point_mode_forces_centroid():
    """``--place-geometry point`` ignores the polygon."""
    from geoextent.lib import extent

    result = extent.from_text(
        "Field campaign in Saxony", place_geometry="point", **_kwargs()
    )
    bbox = result["bbox"]
    # Fake Saxony centroid is (51.05, 13.74) → bbox collapses to that point
    assert bbox == [13.74, 51.05, 13.74, 51.05]


def test_point_only_hit_uses_centroid_in_auto():
    """Hits without a boundary still fall back to lat/lon under 'auto'."""
    from geoextent.lib import extent

    result = extent.from_text("Field campaign in Berlin", **_kwargs())
    bbox = result["bbox"]
    # No boundary fixture for Berlin → point envelope (centroid)
    assert bbox == [13.405, 52.52, 13.405, 52.52]


def test_provenance_carries_boundary_when_present():
    from geoextent.lib import extent

    result = extent.from_text("Field campaign in Saxony", **_kwargs())
    rec = next(p for p in result["place_names"] if p["name"].lower() == "saxony")
    assert "boundary" in rec
    assert rec["boundary"]["type"] == "Polygon"


def test_provenance_omits_boundary_for_point_only_hit():
    from geoextent.lib import extent

    result = extent.from_text("Field campaign in Berlin", **_kwargs())
    rec = next(p for p in result["place_names"] if p["name"].lower() == "berlin")
    # Point-only gazetteers (Berlin in the fixture) don't add a 'boundary'
    # field — keeps responses lean and lets consumers distinguish.
    assert "boundary" not in rec


def test_provenance_omits_boundary_when_place_geometry_point():
    """``--place-geometry point`` is an explicit ask for point treatment;
    the provenance should not echo back the full polygon next to the
    centroid (avoids redundant huge payloads). The geocoder still finds
    the boundary, but the response drops it."""
    from geoextent.lib import extent

    result = extent.from_text(
        "Field campaign in Saxony", place_geometry="point", **_kwargs()
    )
    rec = next(p for p in result["place_names"] if p["name"].lower() == "saxony")
    assert (
        "boundary" not in rec
    ), "place_geometry='point' must suppress the boundary polygon in provenance"
    # Centroid still present so the consumer can reconstruct the geometry.
    assert "lat" in rec and "lon" in rec


def test_mixed_boundary_and_point_hits_envelope_union():
    """A polygon + a point hit produce the union envelope."""
    from geoextent.lib import extent

    result = extent.from_text("Field campaigns in Saxony and Berlin", **_kwargs())
    bbox = result["bbox"]
    # Saxony polygon east extends to 15.04, Berlin is at 13.405 (inside),
    # Saxony north reaches 51.69, Berlin is at 52.52 (above Saxony).
    # The union envelope must span both.
    assert bbox[0] <= 11.87  # west: Saxony
    assert bbox[1] <= 50.17  # south: Saxony
    assert bbox[2] >= 15.04  # east: Saxony
    assert bbox[3] >= 52.52  # north: Berlin


def test_cli_place_geometry_point(script_runner):
    import json

    ret = script_runner.run(
        [
            "geoextent",
            "-b",
            "--quiet",
            "--ner-ambiguity",
            "top",
            "--no-auto-download",
            "--legacy",
            "--place-geometry",
            "point",
            "--text",
            "Field campaign in Saxony",
        ]
    )
    assert ret.success, ret.stderr
    payload = json.loads(ret.stdout)
    # GeoJSON FeatureCollection: with point mode, geometry is Point.
    geom = payload["features"][0]["geometry"]
    assert geom["type"] == "Point"


def test_convex_hull_single_polygon():
    """A single polygon hit produces the polygon's convex hull (simplification)."""
    from geoextent.lib import extent

    result = extent.from_text(
        "Field campaign in Saxony",
        convex_hull=True,
        **_kwargs(),
    )
    assert result.get("convex_hull") is True
    hull = result["bbox"]
    # The fake Saxony fixture is a rectangle (already convex), so its hull
    # equals its outer ring (closed) = 5 vertices.
    assert isinstance(hull, list) and isinstance(hull[0], list)
    assert len(hull) == 5
    # First and last vertices must coincide (closed ring).
    assert hull[0] == hull[-1]
    # Every vertex is inside the fixture's lon/lat bounds.
    for lon, lat in hull:
        assert 11.86 <= lon <= 15.05
        assert 50.16 <= lat <= 51.70


def test_convex_hull_polygon_plus_outside_point():
    """Polygon + a point outside it extends the hull to enclose the point."""
    from geoextent.lib import extent

    result = extent.from_text(
        "Field campaigns in Saxony and Berlin",
        convex_hull=True,
        **_kwargs(),
    )
    hull = result["bbox"]
    assert result.get("convex_hull") is True
    lats = [v[1] for v in hull]
    # Saxony tops out at 51.69 lat; Berlin is at 52.52 — hull must reach Berlin.
    assert max(lats) >= 52.52


def test_convex_hull_two_points():
    """Two points produce a line-segment hull (same behaviour as before)."""
    from geoextent.lib import extent

    result = extent.from_text(
        "Field campaigns in Berlin and Paris",
        convex_hull=True,
        **_kwargs(),
    )
    hull = result["bbox"]
    assert isinstance(hull, list) and isinstance(hull[0], list)
    assert len(hull) == 2  # line segment
    coords = sorted([tuple(v) for v in hull])
    # Berlin and Paris coords from the fixture.
    assert coords == sorted([(13.405, 52.52), (2.3522, 48.8566)])


def test_convex_hull_place_geometry_point_uses_centroids_only():
    """``--place-geometry point`` forces centroid-only hull (skips polygon)."""
    from geoextent.lib import extent

    result = extent.from_text(
        "Field campaigns in Saxony and Berlin",
        convex_hull=True,
        place_geometry="point",
        **_kwargs(),
    )
    hull = result["bbox"]
    # Only two centroids → line segment, not a polygon.
    assert isinstance(hull, list) and isinstance(hull[0], list)
    assert len(hull) == 2


def test_cli_place_geometry_auto_uses_polygon(script_runner):
    import json

    ret = script_runner.run(
        [
            "geoextent",
            "-b",
            "--quiet",
            "--ner-ambiguity",
            "top",
            "--no-auto-download",
            "--legacy",
            "--text",
            "Field campaign in Saxony",
        ]
    )
    assert ret.success, ret.stderr
    payload = json.loads(ret.stdout)
    # With auto + boundary available, the bbox geometry is a Polygon envelope.
    geom = payload["features"][0]["geometry"]
    assert geom["type"] == "Polygon"
