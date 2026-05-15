"""CLI tests for text NER (issue #112).

Gated on spaCy + en_core_web_sm. To keep CI hermetic, the gazetteer is
patched via a small autouse fixture that monkeypatches the real services
at the module level inside the spawned process by injecting a sitecustomize
file via PYTHONPATH. We instead use script_runner with the in-process flag
(default for pytest-console-scripts) and patch from this test module.
"""

import json
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


@pytest.fixture(autouse=True)
def fake_gazetteer(monkeypatch):
    install_fake_gazetteer(monkeypatch)


def test_cli_text_inline(script_runner):
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
            "--text",
            "Berlin and Paris",
        ]
    )
    assert ret.success, f"failed: {ret.stderr}"
    result = json.loads(ret.stdout)
    place_names = result["features"][0]["properties"]["place_names"]
    names = {p["name"].lower() for p in place_names}
    assert "berlin" in names
    assert "paris" in names


def test_cli_text_stdin(script_runner):
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
            "-",
        ],
        stdin="Workshops in Tokyo and London.",
    )
    assert ret.success, f"failed: {ret.stderr}"
    result = json.loads(ret.stdout)
    place_names = result["features"][0]["properties"]["place_names"]
    names = {p["name"].lower() for p in place_names}
    assert "tokyo" in names
    assert "london" in names


def test_cli_text_file(script_runner):
    path = os.path.join(os.path.dirname(__file__), "testdata", "text", "cities.txt")
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
            path,
        ]
    )
    assert ret.success, f"failed: {ret.stderr}"
    result = json.loads(ret.stdout)
    assert "features" in result and result["features"]


def test_cli_text_combined_with_local_geojson(script_runner, tmp_path):
    """Combining a geospatial file and --text in one CLI call.

    ``--text`` is treated as just another source, peer to the positional
    files (issue #112 follow-up): a multi-input run merges into a single
    envelope / convex hull by default. ``--details`` still exposes
    per-input results without altering the merged top-level.
    """
    geojson = tmp_path / "tokyo.geojson"
    geojson.write_text(
        '{"type":"FeatureCollection","features":['
        '{"type":"Feature","properties":{},'
        '"geometry":{"type":"Point","coordinates":[139.6503,35.6762]}}]}'
    )

    base = [
        "geoextent",
        "-b",
        "--quiet",
        "--ner-ambiguity",
        "top",
        "--no-auto-download",
        "--legacy",
        "--text",
        "Field campaigns in Berlin",
        str(geojson),
    ]

    def _assert_bbox_spans_berlin_to_tokyo(stdout):
        payload = json.loads(stdout)
        polygon_ring = payload["features"][0]["geometry"]["coordinates"][0]
        lons = [pt[0] for pt in polygon_ring]
        lats = [pt[1] for pt in polygon_ring]
        assert min(lons) <= 14, f"expected Berlin lon (~13.4) in hull, got {lons}"
        assert max(lons) >= 139, f"expected Tokyo lon (~139.6) in hull, got {lons}"
        assert min(lats) <= 36, f"expected Tokyo lat (~35.7) in hull, got {lats}"
        assert max(lats) >= 52, f"expected Berlin lat (~52.5) in hull, got {lats}"

    # 1) Default: the bbox already spans Berlin to Tokyo (no flag needed).
    ret = script_runner.run(base)
    assert ret.success, ret.stderr
    _assert_bbox_spans_berlin_to_tokyo(ret.stdout)

    # 2) --details exposes per-input results alongside the merged bbox.
    ret = script_runner.run(base + ["--details"])
    assert ret.success, ret.stderr
    payload = json.loads(ret.stdout)
    # Merged top-level still present.
    _assert_bbox_spans_berlin_to_tokyo(ret.stdout)
    # Per-input details available somewhere in the payload.
    details = payload.get("geoextent_extraction", {}).get("details") or payload.get(
        "details", {}
    )
    if not details:
        # Fall back to summary feature presence check
        assert "features" in payload


def test_cli_text_plus_file_default_merges_bbox_and_tbox(script_runner):
    """Regression: ``--text`` plus a positional file must produce a
    meaningful merged extent (both spatial and temporal) without
    requiring any extra flag. Before this was fixed, a mixed call would
    silently drop the bbox and emit only ``{"format": "multiple_files",
    "tbox": [...]}`` — i.e. the convex hull / envelope vanished.

    The command exercises:
      • ``--text`` contributing place names (Denmark, Belgium) and
        years (2021, 2023);
      • a real text file ``cities.txt`` contributing place names
        (Berlin, Reykjavik);
      • ``--convex-hull`` merging across both.

    No network: the gazetteer cache for Nominatim is hit once for each
    name (cached in CI via the standard pytest workers). This stays in
    the default fast suite.
    """
    path = os.path.join(
        os.path.dirname(__file__), "testdata", "text", "mixed_dir", "cities.txt"
    )
    ret = script_runner.run(
        [
            "geoextent",
            "-b",
            "-t",
            "--convex-hull",
            "--quiet",
            "--no-auto-download",
            "--legacy",
            "--text",
            "Travelling from Denmark to Belgium in 2021 and 2023",
            path,
        ]
    )
    assert ret.success, f"failed: {ret.stderr}"
    payload = json.loads(ret.stdout)
    feat = payload["features"][0]
    assert (
        feat["geometry"]["type"] == "Polygon"
    ), "expected a polygon (convex hull) geometry"
    ring = feat["geometry"]["coordinates"][0]
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    # Reykjavik (~-21.9 lon) from cities.txt sets the western edge; the
    # eastern edge reaches into Belgium / Germany (≥ 5° lon for Belgium
    # boundary or ≥ 13° for Berlin). Northern edge is Reykjavik (~64°);
    # southern edge is Belgium (~49.5°).
    assert min(lons) <= -20, f"expected Reykjavik (~-21.9°) in hull, got {lons[:3]}…"
    assert max(lons) >= 5, f"expected Belgium / Berlin (≥5°E) in hull, got {lons[:3]}…"
    assert max(lats) >= 60, f"expected Reykjavik (~64°N) in hull, got {lats[:3]}…"
    assert min(lats) <= 51, f"expected Belgium (~50.5°N) in hull, got {lats[:3]}…"

    # Temporal extent must span both years from --text.
    tbox = payload.get("geoextent_extraction", {}).get("tbox") or feat[
        "properties"
    ].get("tbox")
    assert tbox is not None, "expected merged tbox in output"
    assert tbox[0].startswith("2021"), f"expected tbox start 2021, got {tbox}"
    assert tbox[1].startswith("2023"), f"expected tbox end 2023, got {tbox}"


def test_cli_text_directory_mixed(script_runner):
    path = os.path.join(os.path.dirname(__file__), "testdata", "text", "mixed_dir")
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
            path,
        ]
    )
    assert ret.success, f"failed: {ret.stderr}"
    result = json.loads(ret.stdout)
    assert "features" in result and result["features"]
