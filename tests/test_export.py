"""Tests for geoextent.lib.export — file export functionality."""

import csv
import datetime
import json
import os

import pytest
from osgeo import ogr

from geoextent.lib.export import (
    _detect_output_format,
    _bbox_or_hull_to_geometry,
    _parse_tbox,
    _build_features,
    export_results,
    export_to_file,
)

# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------


class TestDetectOutputFormat:
    def test_gpkg(self):
        assert _detect_output_format("result.gpkg") == "GPKG"

    def test_geojson(self):
        assert _detect_output_format("result.geojson") == "GeoJSON"

    def test_json(self):
        assert _detect_output_format("result.json") == "GeoJSON"

    def test_csv(self):
        assert _detect_output_format("result.csv") == "CSV"

    def test_unknown_fallback(self):
        with pytest.warns(UserWarning, match="falling back to GeoPackage"):
            assert _detect_output_format("result.xyz") == "GPKG"


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


class TestBboxOrHullToGeometry:
    def test_simple_bbox(self):
        result = {"bbox": [7.0, 51.0, 8.0, 52.0]}
        geom = _bbox_or_hull_to_geometry(result)
        assert geom is not None
        assert geom.GetGeometryName() == "POLYGON"
        env = geom.GetEnvelope()  # (minX, maxX, minY, maxY)
        assert env == pytest.approx((7.0, 8.0, 51.0, 52.0))

    def test_coordinate_array(self):
        result = {
            "bbox": [[7.0, 51.0], [8.0, 51.5], [7.5, 52.0]],
            "convex_hull": True,
        }
        geom = _bbox_or_hull_to_geometry(result)
        assert geom is not None
        assert geom.GetGeometryName() == "POLYGON"

    def test_geojson_polygon_dict(self):
        result = {
            "bbox": {
                "type": "Polygon",
                "coordinates": [
                    [[7.0, 51.0], [8.0, 51.0], [8.0, 52.0], [7.0, 52.0], [7.0, 51.0]]
                ],
            }
        }
        geom = _bbox_or_hull_to_geometry(result)
        assert geom is not None
        assert geom.GetGeometryName() == "POLYGON"

    def test_none_bbox(self):
        assert _bbox_or_hull_to_geometry({"bbox": None}) is None
        assert _bbox_or_hull_to_geometry({}) is None

    def test_empty_list(self):
        assert _bbox_or_hull_to_geometry({"bbox": []}) is None


# ---------------------------------------------------------------------------
# Temporal helpers
# ---------------------------------------------------------------------------


class TestParseTbox:
    def test_date_strings(self):
        start, end = _parse_tbox(["2020-01-15", "2020-12-31"])
        assert start == datetime.date(2020, 1, 15)
        assert end == datetime.date(2020, 12, 31)

    def test_iso8601_strings(self):
        start, end = _parse_tbox(["2020-01-15T10:30:00Z", "2020-12-31T23:59:59Z"])
        assert start == datetime.date(2020, 1, 15)
        assert end == datetime.date(2020, 12, 31)

    def test_none(self):
        assert _parse_tbox(None) == (None, None)

    def test_empty_list(self):
        assert _parse_tbox([]) == (None, None)


# ---------------------------------------------------------------------------
# Synthetic output dicts for testing
# ---------------------------------------------------------------------------


def _single_file_output():
    return {
        "format": "geojson",
        "geoextent_handler": "handle_vector",
        "bbox": [7.601680, 51.949220, 7.647256, 51.974624],
        "tbox": ["2018-11-14", "2018-11-14"],
        "crs": "4326",
    }


def _multi_file_output():
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


def _convex_hull_output():
    return {
        "format": "geojson",
        "geoextent_handler": "handle_vector",
        "bbox": [[7.0, 51.0], [8.0, 51.5], [7.5, 52.0]],
        "convex_hull": True,
        "crs": "4326",
    }


def _convex_hull_geojson_polygon_output():
    return {
        "format": "geojson",
        "geoextent_handler": "handle_vector",
        "bbox": {
            "type": "Polygon",
            "coordinates": [
                [[7.0, 51.0], [8.0, 51.0], [8.0, 52.0], [7.0, 52.0], [7.0, 51.0]]
            ],
        },
        "convex_hull": True,
        "crs": "4326",
    }


def _no_tbox_output():
    return {
        "format": "geojson",
        "geoextent_handler": "handle_vector",
        "bbox": [7.0, 51.0, 8.0, 52.0],
        "crs": "4326",
    }


# ---------------------------------------------------------------------------
# GPKG writer tests
# ---------------------------------------------------------------------------


class TestWriteGPKG:
    def test_single_file_gpkg(self, tmp_path):
        out = tmp_path / "out.gpkg"
        export_results(
            _single_file_output(), str(out), inputs=["test.geojson"], version="0.9.0"
        )

        ds = ogr.Open(str(out))
        assert ds is not None
        lyr = ds.GetLayerByName("files")
        assert lyr is not None
        assert lyr.GetFeatureCount() == 1
        feat = lyr.GetNextFeature()
        assert feat["filename"] == "test.geojson"
        assert feat["handler"] == "handle_vector"
        assert feat.GetGeometryRef() is not None
        ds = None

    def test_multi_file_gpkg(self, tmp_path):
        out = tmp_path / "out.gpkg"
        export_results(
            _multi_file_output(), str(out), inputs=["mydir"], version="0.9.0"
        )

        ds = ogr.Open(str(out))
        lyr = ds.GetLayerByName("files")
        # 2 files + 1 summary = 3
        assert lyr.GetFeatureCount() == 3
        # Last feature is the summary
        for _ in range(2):
            lyr.GetNextFeature()
        summary = lyr.GetNextFeature()
        assert "geoextent:0.9.0" in summary["handler"]
        ds = None

    def test_temporal_fields_are_date(self, tmp_path):
        out = tmp_path / "out.gpkg"
        export_results(
            _single_file_output(), str(out), inputs=["test.geojson"], version="0.9.0"
        )

        ds = ogr.Open(str(out))
        lyr = ds.GetLayerByName("files")
        defn = lyr.GetLayerDefn()
        ts_idx = defn.GetFieldIndex("tbox_start")
        te_idx = defn.GetFieldIndex("tbox_end")
        assert defn.GetFieldDefn(ts_idx).GetType() == ogr.OFTDate
        assert defn.GetFieldDefn(te_idx).GetType() == ogr.OFTDate

        feat = lyr.GetNextFeature()
        # OGR returns date as [year, month, day, hour, minute, second, tz]
        assert list(feat.GetFieldAsDateTime(ts_idx))[:3] == [2018, 11, 14]
        assert list(feat.GetFieldAsDateTime(te_idx))[:3] == [2018, 11, 14]
        ds = None

    def test_temporal_none(self, tmp_path):
        out = tmp_path / "out.gpkg"
        export_results(
            _no_tbox_output(), str(out), inputs=["test.geojson"], version="0.9.0"
        )

        ds = ogr.Open(str(out))
        lyr = ds.GetLayerByName("files")
        feat = lyr.GetNextFeature()
        defn = lyr.GetLayerDefn()
        ts_idx = defn.GetFieldIndex("tbox_start")
        assert feat.IsFieldNull(ts_idx)
        ds = None

    def test_convex_hull_gpkg(self, tmp_path):
        out = tmp_path / "out.gpkg"
        export_results(
            _convex_hull_output(), str(out), inputs=["test.geojson"], version="0.9.0"
        )

        ds = ogr.Open(str(out))
        lyr = ds.GetLayerByName("files")
        feat = lyr.GetNextFeature()
        geom = feat.GetGeometryRef()
        assert geom is not None
        assert geom.GetGeometryName() == "POLYGON"
        ds = None

    def test_convex_hull_geojson_polygon_dict_gpkg(self, tmp_path):
        out = tmp_path / "out.gpkg"
        export_results(
            _convex_hull_geojson_polygon_output(),
            str(out),
            inputs=["test.geojson"],
            version="0.9.0",
        )

        ds = ogr.Open(str(out))
        lyr = ds.GetLayerByName("files")
        feat = lyr.GetNextFeature()
        geom = feat.GetGeometryRef()
        assert geom is not None
        assert geom.GetGeometryName() == "POLYGON"
        ds = None

    def test_overwrite_existing(self, tmp_path):
        out = tmp_path / "out.gpkg"
        export_results(
            _single_file_output(), str(out), inputs=["a.geojson"], version="0.9.0"
        )
        assert out.exists()
        # Write again — should overwrite
        export_results(
            _single_file_output(), str(out), inputs=["b.geojson"], version="0.9.0"
        )
        ds = ogr.Open(str(out))
        lyr = ds.GetLayerByName("files")
        feat = lyr.GetNextFeature()
        assert feat["filename"] == "b.geojson"
        ds = None


# ---------------------------------------------------------------------------
# GeoJSON writer tests
# ---------------------------------------------------------------------------


class TestWriteGeoJSON:
    def test_single_file_geojson(self, tmp_path):
        out = tmp_path / "out.geojson"
        export_results(
            _single_file_output(), str(out), inputs=["test.geojson"], version="0.9.0"
        )

        with open(str(out)) as fh:
            fc = json.load(fh)
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 1
        feat = fc["features"][0]
        assert feat["type"] == "Feature"
        assert feat["geometry"]["type"] == "Polygon"
        assert feat["properties"]["filename"] == "test.geojson"
        # Coordinates should be in [lon, lat] order
        coords = feat["geometry"]["coordinates"][0]
        # All lons should be ~7.6, all lats ~51.9
        for coord in coords:
            assert 7.0 <= coord[0] <= 8.0
            assert 51.0 <= coord[1] <= 52.0

    def test_multi_file_geojson(self, tmp_path):
        out = tmp_path / "out.geojson"
        export_results(
            _multi_file_output(), str(out), inputs=["mydir"], version="0.9.0"
        )

        with open(str(out)) as fh:
            fc = json.load(fh)
        assert len(fc["features"]) == 3  # 2 files + 1 summary

    def test_temporal_as_iso_strings(self, tmp_path):
        out = tmp_path / "out.geojson"
        export_results(
            _single_file_output(), str(out), inputs=["test.geojson"], version="0.9.0"
        )

        with open(str(out)) as fh:
            fc = json.load(fh)
        props = fc["features"][0]["properties"]
        assert props["tbox_start"] == "2018-11-14"
        assert props["tbox_end"] == "2018-11-14"

    def test_temporal_none_geojson(self, tmp_path):
        out = tmp_path / "out.geojson"
        export_results(
            _no_tbox_output(), str(out), inputs=["test.geojson"], version="0.9.0"
        )

        with open(str(out)) as fh:
            fc = json.load(fh)
        props = fc["features"][0]["properties"]
        assert props["tbox_start"] is None
        assert props["tbox_end"] is None


# ---------------------------------------------------------------------------
# CSV writer tests
# ---------------------------------------------------------------------------


class TestWriteCSV:
    def test_multi_file_csv(self, tmp_path):
        out = tmp_path / "out.csv"
        export_results(
            _multi_file_output(), str(out), inputs=["mydir"], version="0.9.0"
        )

        with open(str(out), newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        assert len(rows) == 3
        assert rows[0]["filename"] == "file_a.geojson"
        assert "POLYGON" in rows[0]["geometry"]

    def test_csv_wkb_format(self, tmp_path):
        out = tmp_path / "out.csv"
        export_results(
            _single_file_output(),
            str(out),
            inputs=["test.geojson"],
            version="0.9.0",
            geometry_format="wkb",
        )

        with open(str(out), newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        # WKB is hex-encoded — should start with "01" (little-endian)
        assert rows[0]["geometry"].startswith("01")
        # Should not contain "POLYGON"
        assert "POLYGON" not in rows[0]["geometry"]

    def test_csv_temporal_fields(self, tmp_path):
        out = tmp_path / "out.csv"
        export_results(
            _single_file_output(), str(out), inputs=["test.geojson"], version="0.9.0"
        )

        with open(str(out), newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        assert rows[0]["tbox_start"] == "2018-11-14"
        assert rows[0]["tbox_end"] == "2018-11-14"


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------


class TestPathValidation:
    def test_directory_path_raises(self, tmp_path):
        with pytest.raises(ValueError, match="not a directory"):
            export_results(
                _single_file_output(), str(tmp_path), inputs=["test.geojson"]
            )

    def test_nonexistent_parent_raises(self):
        with pytest.raises(ValueError, match="does not exist"):
            export_results(
                _single_file_output(),
                "/nonexistent/path/out.gpkg",
                inputs=["test.geojson"],
            )


# ---------------------------------------------------------------------------
# Public API (export_to_file)
# ---------------------------------------------------------------------------


class TestExportToFile:
    def test_export_to_file_creates_gpkg(self, tmp_path):
        out = tmp_path / "out.gpkg"
        export_to_file(_single_file_output(), str(out), inputs=["test.geojson"])
        assert out.exists()
        ds = ogr.Open(str(out))
        assert ds is not None
        ds = None


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestCLIExport:
    def test_single_file_output_gpkg(self, script_runner, tmp_path):
        """--output should work with single-file input."""
        out = tmp_path / "single.gpkg"
        ret = script_runner.run(
            [
                "geoextent",
                "-b",
                "-t",
                "--output",
                str(out),
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
            ]
        )
        assert ret.success, f"stderr: {ret.stderr}"
        assert out.exists(), "GPKG should be created for single-file input"

    def test_single_file_output_geojson(self, script_runner, tmp_path):
        """--output with .geojson extension produces valid GeoJSON."""
        out = tmp_path / "single.geojson"
        ret = script_runner.run(
            [
                "geoextent",
                "-b",
                "-t",
                "--output",
                str(out),
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
            ]
        )
        assert ret.success, f"stderr: {ret.stderr}"
        assert out.exists()
        with open(str(out)) as fh:
            fc = json.load(fh)
        assert fc["type"] == "FeatureCollection"

    def test_directory_output_csv(self, script_runner, tmp_path):
        """--output with .csv extension produces CSV with all files."""
        out = tmp_path / "dir.csv"
        ret = script_runner.run(
            [
                "geoextent",
                "-b",
                "-t",
                "--output",
                str(out),
                "tests/testdata/folders/folder_two_files",
            ]
        )
        assert ret.success, f"stderr: {ret.stderr}"
        assert out.exists()
        with open(str(out), newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        # At least 2 files + 1 summary
        assert len(rows) >= 3

    def test_convex_hull_output_gpkg(self, script_runner, tmp_path):
        """--convex-hull --output produces hull geometry in GPKG."""
        out = tmp_path / "hull.gpkg"
        ret = script_runner.run(
            [
                "geoextent",
                "-b",
                "--convex-hull",
                "--output",
                str(out),
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
            ]
        )
        assert ret.success, f"stderr: {ret.stderr}"
        assert out.exists()

    def test_format_wkt_output_gpkg_warns(self, script_runner, tmp_path):
        """--format wkt --output out.gpkg still creates GPKG and warns about ignored format."""
        out = tmp_path / "out.gpkg"
        ret = script_runner.run(
            [
                "geoextent",
                "-b",
                "--format",
                "wkt",
                "--debug",
                "--output",
                str(out),
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
            ]
        )
        assert ret.success, f"stderr: {ret.stderr}"
        assert out.exists(), "GPKG should still be created when --format is mismatched"
        assert "ignored" in ret.stderr.lower()

    def test_quiet_output_gpkg(self, script_runner, tmp_path):
        """--quiet --output should still create the file."""
        out = tmp_path / "quiet.gpkg"
        ret = script_runner.run(
            [
                "geoextent",
                "-b",
                "--quiet",
                "--output",
                str(out),
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
            ]
        )
        assert ret.success, f"stderr: {ret.stderr}"
        assert out.exists()
