"""
Tests for custom CRS handling in geoextent.

This module tests the ability to handle files with custom Coordinate Reference Systems
that don't have standard EPSG codes. These CRS definitions use WKT (Well-Known Text)
format for transformation instead of EPSG codes.
"""

import geoextent.lib.extent as geoextent
from help_functions_test import tolerance
import pytest


class TestCustomCRSHandling:
    """Test handling of custom (non-EPSG) Coordinate Reference Systems"""

    def test_geopackage_with_custom_crs(self):
        """Test GeoPackage with Irish Grid projection (custom datum)

        Test data source:
        - Original: https://zenodo.org/records/13993331 (file: All_Ireland_1885.gpkg)
        - DOI: https://doi.org/10.5281/zenodo.13993331
        - License: CC-BY-4.0
        - Modified: Single feature extracted from original dataset (100 features)
          using: ogr2ogr -f GPKG reduced.gpkg original.gpkg -sql "SELECT * FROM All_Ireland_1885 LIMIT 1"

        Dataset description:
        Uses Transverse Mercator projection with Modified Airy spheroid,
        which cannot be auto-identified to an EPSG code but can be transformed
        using its WKT definition.

        Expected behavior: Should successfully extract bbox by using WKT-based
        transformation to WGS84.
        """
        result = geoextent.fromFile(
            "tests/testdata/geopackage/custom_crs.gpkg", bbox=True
        )

        assert "bbox" in result
        assert "crs" in result

        # Verify bbox is in reasonable range for Northern Ireland
        # Single feature covers a small area in Northern Ireland
        bbox = result["bbox"]
        assert bbox[0] == pytest.approx(54.56439223609256, abs=tolerance)
        assert bbox[1] == pytest.approx(-5.936181762169785, abs=tolerance)
        assert bbox[2] == pytest.approx(54.589879115587856, abs=tolerance)
        assert bbox[3] == pytest.approx(-5.887083505972233, abs=tolerance)

        # Verify transformation to WGS84 was successful
        assert result["crs"] == "4326"

    def test_custom_crs_handler_recognition(self):
        """Test that custom CRS files are handled by handleVector"""
        result = geoextent.fromFile(
            "tests/testdata/geopackage/custom_crs.gpkg", bbox=True
        )
        assert "geoextent_handler" in result
        assert result["geoextent_handler"] == "handleVector"

    def test_custom_crs_format_recognition(self):
        """Test that GeoPackage format is correctly identified"""
        result = geoextent.fromFile(
            "tests/testdata/geopackage/custom_crs.gpkg", bbox=True
        )
        assert "format" in result
        assert result["format"] == "gpkg"


class TestWKTTransformation:
    """Test WKT-based coordinate transformation"""

    def test_wkt_transformation_accuracy(self):
        """Verify that WKT-based transformation produces accurate results

        This test ensures that using WKT definition for transformation
        produces the same results as would be expected from a proper
        EPSG-based transformation.
        """
        result = geoextent.fromFile(
            "tests/testdata/geopackage/custom_crs.gpkg", bbox=True
        )

        # The bbox should be transformed to WGS84
        assert result["crs"] == "4326"

        # Coordinates should be in valid latitude/longitude ranges
        bbox = result["bbox"]
        assert -90 <= bbox[0] <= 90  # min latitude
        assert -180 <= bbox[1] <= 180  # min longitude
        assert -90 <= bbox[2] <= 90  # max latitude
        assert -180 <= bbox[3] <= 180  # max longitude

        # Min should be less than max
        assert bbox[0] < bbox[2]  # min_lat < max_lat
        assert bbox[1] < bbox[3]  # min_lon < max_lon

    def test_convex_hull_with_custom_crs(self):
        """Verify that convex hull extraction works with WKT-based CRS

        This test ensures that convex hull calculation and transformation
        work correctly when using WKT definitions instead of EPSG codes.
        """
        result = geoextent.fromFile(
            "tests/testdata/geopackage/custom_crs.gpkg", bbox=True, convex_hull=True
        )

        # Should have convex hull flag
        assert "convex_hull" in result
        assert result["convex_hull"] is True

        # The coordinates should be transformed to WGS84
        assert result["crs"] == "4326"

        # The bbox field should contain convex hull coordinates
        bbox = result["bbox"]
        assert isinstance(bbox, list)
        assert len(bbox) > 4  # Convex hull has more than 4 points (unlike bbox)

        # All coordinates should be in valid ranges
        for coord in bbox:
            assert isinstance(coord, list)
            assert len(coord) == 2
            lon, lat = coord
            assert -180 <= lon <= 180
            assert -90 <= lat <= 90
