"""Tests for geoextent.lib.export — join_files functionality."""

import csv
import datetime
import json
import os

import pytest
from osgeo import ogr

from geoextent.lib.export import (
    _is_summary_feature,
    _read_exported_features,
    export_results,
    join_files,
)

# ---------------------------------------------------------------------------
# Helpers — create synthetic export files with known data
# ---------------------------------------------------------------------------


def _make_multi_output():
    """Return a multi-file extraction result with 2 individual files + summary."""
    return {
        "format": "folder",
        "bbox": [0.0, 40.0, 8.0, 52.0],
        "tbox": ["2018-11-14", "2019-06-01"],
        "crs": "4326",
        "details": {
            "file_a.geojson": {
                "format": "geojson",
                "geoextent_handler": "handle_vector",
                "bbox": [7.0, 51.0, 8.0, 52.0],
                "tbox": ["2018-11-14", "2018-11-14"],
                "crs": "4326",
            },
            "file_b.geojson": {
                "format": "geojson",
                "geoextent_handler": "handle_vector",
                "bbox": [0.0, 40.0, 3.0, 42.0],
                "tbox": ["2019-06-01", "2019-06-01"],
                "crs": "4326",
            },
        },
    }


def _make_summary_only_output():
    """Return a single-file result that looks like a summary (for edge case testing)."""
    return {
        "format": "folder",
        "bbox": [7.0, 51.0, 8.0, 52.0],
        "tbox": ["2020-01-01", "2020-12-31"],
        "crs": "4326",
        "details": {},
    }


def _write_export(tmp_path, filename, output=None):
    """Write a synthetic export file and return its path."""
    if output is None:
        output = _make_multi_output()
    path = str(tmp_path / filename)
    export_results(output, path, inputs=["testdir"], version="0.9.0")
    return path


# ---------------------------------------------------------------------------
# _is_summary_feature
# ---------------------------------------------------------------------------


class TestIsSummaryFeature:
    def test_summary_with_version(self):
        assert _is_summary_feature({"handler": "geoextent:0.9.0"}) is True

    def test_summary_without_version(self):
        assert _is_summary_feature({"handler": "geoextent"}) is True

    def test_normal_handler(self):
        assert _is_summary_feature({"handler": "handle_vector"}) is False

    def test_none_handler(self):
        assert _is_summary_feature({"handler": None}) is False

    def test_empty_handler(self):
        assert _is_summary_feature({"handler": ""}) is False


# ---------------------------------------------------------------------------
# Reader round-trip tests
# ---------------------------------------------------------------------------


class TestReadExportedFeatures:
    def test_read_gpkg(self, tmp_path):
        path = _write_export(tmp_path, "export.gpkg")
        features = _read_exported_features(path)
        # 2 individual + 1 summary = 3
        assert len(features) == 3
        assert features[0]["filename"] == "file_a.geojson"
        assert features[0]["handler"] == "handle_vector"

    def test_read_geojson(self, tmp_path):
        path = _write_export(tmp_path, "export.geojson")
        features = _read_exported_features(path)
        assert len(features) == 3
        assert features[1]["filename"] == "file_b.geojson"

    def test_read_csv(self, tmp_path):
        path = _write_export(tmp_path, "export.csv")
        features = _read_exported_features(path)
        assert len(features) == 3

    def test_temporal_preserved_gpkg(self, tmp_path):
        path = _write_export(tmp_path, "export.gpkg")
        features = _read_exported_features(path)
        assert features[0]["tbox_start"] == datetime.date(2018, 11, 14)
        assert features[0]["tbox_end"] == datetime.date(2018, 11, 14)

    def test_temporal_preserved_geojson(self, tmp_path):
        path = _write_export(tmp_path, "export.geojson")
        features = _read_exported_features(path)
        assert features[0]["tbox_start"] == datetime.date(2018, 11, 14)

    def test_temporal_preserved_csv(self, tmp_path):
        path = _write_export(tmp_path, "export.csv")
        features = _read_exported_features(path)
        assert features[0]["tbox_start"] == datetime.date(2018, 11, 14)

    def test_geometry_preserved_gpkg(self, tmp_path):
        path = _write_export(tmp_path, "export.gpkg")
        features = _read_exported_features(path)
        geom = features[0]["geometry"]
        assert geom is not None
        assert geom.GetGeometryName() == "POLYGON"
        env = geom.GetEnvelope()  # (minX, maxX, minY, maxY)
        assert env == pytest.approx((7.0, 8.0, 51.0, 52.0))

    def test_geometry_preserved_geojson(self, tmp_path):
        path = _write_export(tmp_path, "export.geojson")
        features = _read_exported_features(path)
        geom = features[0]["geometry"]
        assert geom is not None
        assert geom.GetGeometryName() == "POLYGON"

    def test_geometry_preserved_csv_wkt(self, tmp_path):
        path = str(tmp_path / "export.csv")
        export_results(
            _make_multi_output(),
            path,
            inputs=["testdir"],
            version="0.9.0",
            geometry_format="wkt",
        )
        features = _read_exported_features(path)
        geom = features[0]["geometry"]
        assert geom is not None
        assert geom.GetGeometryName() == "POLYGON"

    def test_geometry_preserved_csv_wkb(self, tmp_path):
        path = str(tmp_path / "export.csv")
        export_results(
            _make_multi_output(),
            path,
            inputs=["testdir"],
            version="0.9.0",
            geometry_format="wkb",
        )
        features = _read_exported_features(path)
        geom = features[0]["geometry"]
        assert geom is not None
        assert geom.GetGeometryName() == "POLYGON"


# ---------------------------------------------------------------------------
# join_files unit tests
# ---------------------------------------------------------------------------


class TestJoinFiles:
    def test_join_two_gpkg(self, tmp_path):
        a = _write_export(tmp_path, "a.gpkg")
        b = _write_export(tmp_path, "b.gpkg")
        out = str(tmp_path / "joined.gpkg")
        join_files([a, b], out)

        ds = ogr.Open(out)
        lyr = ds.GetLayerByName("files")
        # Each input has 2 individual + 1 summary; summaries dropped -> 2 * 2 = 4
        assert lyr.GetFeatureCount() == 4
        # Verify no summary features
        for feat in lyr:
            handler = feat["handler"]
            assert not handler.startswith("geoextent:")
            assert handler != "geoextent"
        ds = None

    def test_join_two_geojson(self, tmp_path):
        a = _write_export(tmp_path, "a.geojson")
        b = _write_export(tmp_path, "b.geojson")
        out = str(tmp_path / "joined.geojson")
        join_files([a, b], out)

        with open(out) as fh:
            fc = json.load(fh)
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 4
        for feat in fc["features"]:
            handler = feat["properties"]["handler"]
            assert not handler.startswith("geoextent:")

    def test_join_mixed_formats(self, tmp_path):
        """GPKG + GeoJSON -> CSV works."""
        a = _write_export(tmp_path, "a.gpkg")
        b = _write_export(tmp_path, "b.geojson")
        out = str(tmp_path / "joined.csv")
        join_files([a, b], out)

        with open(out, newline="") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 4

    def test_join_csv_to_gpkg(self, tmp_path):
        """CSV + CSV -> GPKG works."""
        a = _write_export(tmp_path, "a.csv")
        b = _write_export(tmp_path, "b.csv")
        out = str(tmp_path / "joined.gpkg")
        join_files([a, b], out)

        ds = ogr.Open(out)
        lyr = ds.GetLayerByName("files")
        assert lyr.GetFeatureCount() == 4
        ds = None

    def test_summary_exclusion(self, tmp_path):
        """Summary features (handler starts with 'geoextent:') are dropped."""
        path = _write_export(tmp_path, "export.gpkg")
        features_before = _read_exported_features(path)
        summary_count = sum(1 for f in features_before if _is_summary_feature(f))
        assert summary_count == 1  # Our test data has 1 summary

        out = str(tmp_path / "joined.gpkg")
        join_files([path], out)

        ds = ogr.Open(out)
        lyr = ds.GetLayerByName("files")
        assert lyr.GetFeatureCount() == 2  # Only individual features
        ds = None

    def test_empty_after_filter(self, tmp_path):
        """All-summary input produces empty output (0 features)."""
        # Create a GPKG with only a summary feature
        out_src = _make_summary_only_output()
        # The summary-only output will just have the summary row
        src = str(tmp_path / "summary_only.gpkg")
        export_results(out_src, src, inputs=["testdir"], version="0.9.0")

        out = str(tmp_path / "joined.gpkg")
        join_files([src], out)

        ds = ogr.Open(out)
        lyr = ds.GetLayerByName("files")
        assert lyr.GetFeatureCount() == 0
        ds = None

    def test_geometry_preserved_in_join(self, tmp_path):
        """Geometry survives the read -> filter -> write round-trip."""
        a = _write_export(tmp_path, "a.gpkg")
        out = str(tmp_path / "joined.gpkg")
        join_files([a], out)

        ds = ogr.Open(out)
        lyr = ds.GetLayerByName("files")
        feat = lyr.GetNextFeature()
        geom = feat.GetGeometryRef()
        assert geom is not None
        env = geom.GetEnvelope()
        assert env == pytest.approx((7.0, 8.0, 51.0, 52.0))
        ds = None

    def test_temporal_preserved_in_join(self, tmp_path):
        """Date fields survive the round-trip."""
        a = _write_export(tmp_path, "a.gpkg")
        out = str(tmp_path / "joined.geojson")
        join_files([a], out)

        with open(out) as fh:
            fc = json.load(fh)
        props = fc["features"][0]["properties"]
        assert props["tbox_start"] == "2018-11-14"
        assert props["tbox_end"] == "2018-11-14"

    def test_single_input_file(self, tmp_path):
        """A single input file works correctly."""
        a = _write_export(tmp_path, "a.geojson")
        out = str(tmp_path / "joined.geojson")
        join_files([a], out)

        with open(out) as fh:
            fc = json.load(fh)
        assert len(fc["features"]) == 2  # 2 individual, 1 summary dropped


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestCLIJoin:
    def test_basic_join(self, script_runner, tmp_path):
        """geoextent --join --output merged.gpkg file1.gpkg file2.gpkg"""
        a = _write_export(tmp_path, "a.gpkg")
        b = _write_export(tmp_path, "b.gpkg")
        out = str(tmp_path / "merged.gpkg")

        ret = script_runner.run(["geoextent", "--join", "--output", out, a, b])
        assert ret.success, f"stderr: {ret.stderr}"
        assert os.path.exists(out)

        ds = ogr.Open(out)
        lyr = ds.GetLayerByName("files")
        assert lyr.GetFeatureCount() == 4
        ds = None

    def test_join_without_output_errors(self, script_runner, tmp_path):
        """--join without --output should produce an error."""
        a = _write_export(tmp_path, "a.gpkg")

        ret = script_runner.run(["geoextent", "--join", a])
        assert not ret.success
        assert "output" in ret.stderr.lower() or "error" in ret.stderr.lower()

    def test_join_without_bt_flags(self, script_runner, tmp_path):
        """--join should work without -b or -t flags."""
        a = _write_export(tmp_path, "a.gpkg")
        b = _write_export(tmp_path, "b.gpkg")
        out = str(tmp_path / "merged.geojson")

        ret = script_runner.run(["geoextent", "--join", "--output", out, a, b])
        assert ret.success, f"stderr: {ret.stderr}"
        assert os.path.exists(out)

    def test_join_cross_format(self, script_runner, tmp_path):
        """Join GPKG + GeoJSON -> CSV."""
        a = _write_export(tmp_path, "a.gpkg")
        b = _write_export(tmp_path, "b.geojson")
        out = str(tmp_path / "merged.csv")

        ret = script_runner.run(["geoextent", "--join", "--output", out, a, b])
        assert ret.success, f"stderr: {ret.stderr}"
        assert os.path.exists(out)

        with open(out, newline="") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 4

    def test_join_with_quiet(self, script_runner, tmp_path):
        """--join --quiet should still create the file."""
        a = _write_export(tmp_path, "a.gpkg")
        out = str(tmp_path / "merged.gpkg")

        ret = script_runner.run(["geoextent", "--join", "--quiet", "--output", out, a])
        assert ret.success, f"stderr: {ret.stderr}"
        assert os.path.exists(out)
