"""Tests to ensure GeoJSON output always uses [longitude, latitude] coordinate order
per RFC 7946, regardless of input format or --legacy flag.

RFC 7946 Section 3.1.1:
  "A position is an array of numbers. There MUST be two or more elements.
   The first two elements are longitude and latitude..."

RFC 7946 Appendix A:
  "Point coordinates are in x, y order (easting, northing for projected
   coordinates, longitude, and latitude for geographic coordinates)"
"""

import json
import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.helpfunctions import (
    format_extent_output,
    create_geojson_feature_collection,
)
from help_functions_test import tolerance

# Known test files with well-known coordinates:
# Muenster, Germany: lat ~51.95, lon ~7.62
# The longitude values (7.x) are much smaller than the latitude values (51.x),
# making it easy to detect if the axes are swapped.
MUENSTER_GEOJSON = "tests/testdata/geojson/muenster_ring_zeit.geojson"
# GeoTIFF with projected CRS (EPSG:25832) that must be reprojected to WGS84
# Located in Germany: lat ~50-52, lon ~5-9
GEOTIFF = "tests/testdata/tif/wf_100m_klas.tif"
# CSV with lat/lon columns in Netherlands: lat ~51-53, lon ~4-6
CSV_NL = "tests/testdata/csv/cities_NL.csv"


def _extract_geojson_coords(geojson_fc):
    """Extract coordinates from a GeoJSON FeatureCollection's first feature geometry."""
    features = geojson_fc.get("features", [])
    assert len(features) > 0, "FeatureCollection should have at least one feature"
    geom = features[0]["geometry"]
    if geom["type"] == "Polygon":
        return geom["coordinates"][0]  # outer ring
    elif geom["type"] == "Point":
        return [geom["coordinates"]]
    else:
        pytest.fail(f"Unexpected geometry type: {geom['type']}")


def _assert_geojson_lonlat_order(coords, description=""):
    """Assert that GeoJSON coordinates are in [lon, lat] order.

    For European test data (Germany, Netherlands), longitude is in range ~4-10
    and latitude is in range ~50-54. If the coordinates are swapped, the first
    element would be ~50 instead of ~4-10.
    """
    for i, coord in enumerate(coords):
        lon, lat = coord[0], coord[1]
        # Longitude for European test data should be roughly 4-10
        assert 3 < lon < 11, (
            f"{description} coord[{i}]: expected longitude (3-11) as first element, "
            f"got {lon}. Coordinates may be in wrong [lat, lon] order."
        )
        # Latitude for European test data should be roughly 50-54
        assert 49 < lat < 55, (
            f"{description} coord[{i}]: expected latitude (49-55) as second element, "
            f"got {lat}. Coordinates may be in wrong [lat, lon] order."
        )


class TestRFC7946CoordinateOrder:
    """Verify GeoJSON output always uses [longitude, latitude] per RFC 7946."""

    def test_geojson_input_produces_lonlat_output(self):
        """GeoJSON input -> GeoJSON output should maintain [lon, lat] order."""
        result = geoextent.fromFile(MUENSTER_GEOJSON, bbox=True)
        geojson_output = format_extent_output(
            result, "geojson", extraction_metadata={}, native_order=True
        )
        assert geojson_output["type"] == "FeatureCollection"
        coords = _extract_geojson_coords(geojson_output)
        _assert_geojson_lonlat_order(coords, "GeoJSON input")

    def test_geotiff_input_produces_lonlat_output(self):
        """Projected GeoTIFF -> GeoJSON output should use [lon, lat] order."""
        result = geoextent.fromFile(GEOTIFF, bbox=True)
        geojson_output = format_extent_output(
            result, "geojson", extraction_metadata={}, native_order=True
        )
        assert geojson_output["type"] == "FeatureCollection"
        coords = _extract_geojson_coords(geojson_output)
        _assert_geojson_lonlat_order(coords, "GeoTIFF input")

    def test_csv_input_produces_lonlat_output(self):
        """CSV with lat/lon columns -> GeoJSON output should use [lon, lat] order."""
        result = geoextent.fromFile(CSV_NL, bbox=True)
        geojson_output = format_extent_output(
            result, "geojson", extraction_metadata={}, native_order=True
        )
        assert geojson_output["type"] == "FeatureCollection"
        coords = _extract_geojson_coords(geojson_output)
        _assert_geojson_lonlat_order(coords, "CSV input")

    def test_directory_input_produces_lonlat_output(self):
        """Directory extraction -> GeoJSON output should use [lon, lat] order."""
        result = geoextent.fromDirectory(
            "tests/testdata/folders/folder_one_file", bbox=True, show_progress=False
        )
        geojson_output = format_extent_output(
            result, "geojson", extraction_metadata={}, native_order=True
        )
        assert geojson_output["type"] == "FeatureCollection"
        coords = _extract_geojson_coords(geojson_output)
        _assert_geojson_lonlat_order(coords, "Directory input")

    def test_legacy_flag_still_produces_lonlat_geojson(self):
        """With legacy=True, GeoJSON output should STILL use [lon, lat] per RFC 7946."""
        result = geoextent.fromFile(MUENSTER_GEOJSON, bbox=True, legacy=True)
        # legacy=True means data is already in [lon, lat] internal order (no swap applied)
        # So native_order=False (data is not in native [lat, lon] order)
        geojson_output = format_extent_output(
            result, "geojson", extraction_metadata={}, native_order=False
        )
        assert geojson_output["type"] == "FeatureCollection"
        coords = _extract_geojson_coords(geojson_output)
        _assert_geojson_lonlat_order(coords, "Legacy mode GeoJSON input")

    def test_legacy_flag_geotiff_still_produces_lonlat_geojson(self):
        """With legacy=True, GeoTIFF -> GeoJSON should STILL use [lon, lat]."""
        result = geoextent.fromFile(GEOTIFF, bbox=True, legacy=True)
        geojson_output = format_extent_output(
            result, "geojson", extraction_metadata={}, native_order=False
        )
        assert geojson_output["type"] == "FeatureCollection"
        coords = _extract_geojson_coords(geojson_output)
        _assert_geojson_lonlat_order(coords, "Legacy mode GeoTIFF input")


class TestCoordinateOrderConsistency:
    """Verify that plain bbox coordinate order is consistent across input formats,
    following EPSG:4326 native convention [minlat, minlon, maxlat, maxlon]."""

    def test_bbox_order_geojson_input(self):
        """GeoJSON bbox should be [minlat, minlon, maxlat, maxlon]."""
        result = geoextent.fromFile(MUENSTER_GEOJSON, bbox=True)
        bbox = result["bbox"]
        # Muenster: lat ~51.95, lon ~7.62
        # bbox[0] = minlat, bbox[1] = minlon, bbox[2] = maxlat, bbox[3] = maxlon
        assert 51 < bbox[0] < 52, f"bbox[0] should be latitude (~51.9), got {bbox[0]}"
        assert 7 < bbox[1] < 8, f"bbox[1] should be longitude (~7.6), got {bbox[1]}"
        assert 51 < bbox[2] < 52, f"bbox[2] should be latitude (~51.9), got {bbox[2]}"
        assert 7 < bbox[3] < 8, f"bbox[3] should be longitude (~7.6), got {bbox[3]}"

    def test_bbox_order_geotiff_input(self):
        """GeoTIFF bbox should be [minlat, minlon, maxlat, maxlon]."""
        result = geoextent.fromFile(GEOTIFF, bbox=True)
        bbox = result["bbox"]
        # Germany GeoTIFF: lat ~50-52, lon ~5-9
        assert 49 < bbox[0] < 53, f"bbox[0] should be latitude (~50.3), got {bbox[0]}"
        assert 5 < bbox[1] < 10, f"bbox[1] should be longitude (~5.9), got {bbox[1]}"
        assert 49 < bbox[2] < 53, f"bbox[2] should be latitude (~52.5), got {bbox[2]}"
        assert 5 < bbox[3] < 10, f"bbox[3] should be longitude (~9.4), got {bbox[3]}"

    def test_bbox_order_csv_input(self):
        """CSV bbox should be [minlat, minlon, maxlat, maxlon]."""
        result = geoextent.fromFile(CSV_NL, bbox=True)
        bbox = result["bbox"]
        # Netherlands: lat ~51-53, lon ~4-6
        assert 50 < bbox[0] < 54, f"bbox[0] should be latitude (~51.4), got {bbox[0]}"
        assert 3 < bbox[1] < 7, f"bbox[1] should be longitude (~4.3), got {bbox[1]}"
        assert 50 < bbox[2] < 54, f"bbox[2] should be latitude (~53.2), got {bbox[2]}"
        assert 3 < bbox[3] < 7, f"bbox[3] should be longitude (~6.5), got {bbox[3]}"

    def test_bbox_order_consistent_across_formats(self):
        """All formats should produce bbox with the same [minlat, minlon, maxlat, maxlon] convention."""
        geojson_result = geoextent.fromFile(MUENSTER_GEOJSON, bbox=True)
        geotiff_result = geoextent.fromFile(GEOTIFF, bbox=True)
        csv_result = geoextent.fromFile(CSV_NL, bbox=True)

        for name, result in [
            ("GeoJSON", geojson_result),
            ("GeoTIFF", geotiff_result),
            ("CSV", csv_result),
        ]:
            bbox = result["bbox"]
            # For all European test data: bbox[0] (minlat) > bbox[1] (minlon)
            # because European latitudes (50-54) > European longitudes (4-10)
            assert bbox[0] > bbox[1], (
                f"{name}: bbox[0] ({bbox[0]}) should be > bbox[1] ({bbox[1]}) "
                f"for European data (lat > lon), suggesting [lat, lon] order"
            )
            assert bbox[2] > bbox[3], (
                f"{name}: bbox[2] ({bbox[2]}) should be > bbox[3] ({bbox[3]}) "
                f"for European data (lat > lon), suggesting [lat, lon] order"
            )
