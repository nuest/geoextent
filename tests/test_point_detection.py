import json
import tempfile
import os
import pytest
from unittest.mock import patch
import logging

from geoextent.lib.extent import fromRemote
from geoextent.lib.helpfunctions import (
    is_geometry_a_point,
    create_geojson_feature_collection,
    format_extent_output,
)
from geojson_validator import validate_structure


class TestPointDetection:
    """Test point geometry detection functionality"""

    def test_is_geometry_a_point_bounding_box(self):
        """Test point detection for regular bounding box format"""
        # Point case: all coordinates are the same
        bbox_point = [76.5, -21.5, 76.5, -21.5]
        is_point, coords = is_geometry_a_point(bbox_point, is_convex_hull=False)
        assert is_point is True
        assert coords == [76.5, -21.5]

        # Non-point case: different coordinates
        bbox_rect = [76.5, -21.5, 77.0, -21.0]
        is_point, coords = is_geometry_a_point(bbox_rect, is_convex_hull=False)
        assert is_point is False
        assert coords is None

        # Nearly point case: within tolerance
        bbox_near_point = [76.5, -21.5, 76.5000001, -21.5000001]
        is_point, coords = is_geometry_a_point(
            bbox_near_point, is_convex_hull=False, tolerance=1e-5
        )
        assert is_point is True
        assert coords == [76.5, -21.5]

    def test_is_geometry_a_point_convex_hull(self):
        """Test point detection for convex hull coordinates format"""
        # Point case: all coordinates are the same
        convex_hull_point = [[76.5, -21.5], [76.5, -21.5], [76.5, -21.5]]
        is_point, coords = is_geometry_a_point(convex_hull_point, is_convex_hull=True)
        assert is_point is True
        assert coords == [76.5, -21.5]

        # Non-point case: different coordinates
        convex_hull_polygon = [
            [76.5, -21.5],
            [76.5, -21.0],
            [77.0, -21.0],
            [77.0, -21.5],
            [76.5, -21.5],
        ]
        is_point, coords = is_geometry_a_point(convex_hull_polygon, is_convex_hull=True)
        assert is_point is False
        assert coords is None

    def test_is_geometry_a_point_geojson_polygon(self):
        """Test point detection for GeoJSON polygon format"""
        # Point case: all coordinates are the same
        geojson_point = {
            "type": "Polygon",
            "coordinates": [
                [
                    [76.5, -21.5],
                    [76.5, -21.5],
                    [76.5, -21.5],
                    [76.5, -21.5],
                    [76.5, -21.5],
                ]
            ],
        }
        is_point, coords = is_geometry_a_point(geojson_point, is_convex_hull=False)
        assert is_point is True
        assert coords == [76.5, -21.5]

        # Non-point case: actual polygon
        geojson_polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [76.5, -21.5],
                    [76.5, -21.0],
                    [77.0, -21.0],
                    [77.0, -21.5],
                    [76.5, -21.5],
                ]
            ],
        }
        is_point, coords = is_geometry_a_point(geojson_polygon, is_convex_hull=False)
        assert is_point is False
        assert coords is None

    def test_create_geojson_feature_collection_point_detection(self):
        """Test that create_geojson_feature_collection creates Point geometries for point data"""
        # Test bounding box point detection
        extent_output_bbox = {
            "bbox": [76.5, -21.5, 76.5, -21.5],
            "crs": "4326",
            "format": "remote",
        }

        with patch("geoextent.lib.helpfunctions.logger") as mock_logger:
            result = create_geojson_feature_collection(
                extent_output_bbox, extraction_metadata={}
            )

            # Check that warning was logged
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "single point" in warning_call
            assert "bounding box" in warning_call

            # Check the result
            assert result["type"] == "FeatureCollection"
            assert len(result["features"]) == 1

            feature = result["features"][0]
            assert feature["type"] == "Feature"
            assert feature["geometry"]["type"] == "Point"
            assert feature["geometry"]["coordinates"] == [76.5, -21.5]
            assert result["geoextent_extraction"]["extent_type"] == "point"

    def test_create_geojson_feature_collection_convex_hull_point_detection(self):
        """Test that create_geojson_feature_collection creates Point geometries for convex hull point data"""
        extent_output_convex = {
            "bbox": [[76.5, -21.5], [76.5, -21.5], [76.5, -21.5]],
            "crs": "4326",
            "format": "remote",
            "convex_hull": True,
        }

        with patch("geoextent.lib.helpfunctions.logger") as mock_logger:
            result = create_geojson_feature_collection(
                extent_output_convex, extraction_metadata={}
            )

            # Check that warning was logged
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "single point" in warning_call
            assert "convex hull" in warning_call

            # Check the result
            feature = result["features"][0]
            assert feature["geometry"]["type"] == "Point"
            assert feature["geometry"]["coordinates"] == [76.5, -21.5]
            assert result["geoextent_extraction"]["extent_type"] == "point"


class TestPangaeaDataset918707:
    """Test PANGAEA dataset 918707 which contains point data"""

    def test_pangaea_918707_bounding_box(self):
        """Test extraction of bounding box from PANGAEA dataset 918707 metadata"""
        # This dataset contains a single point location in metadata
        # Use metadata-only mode to avoid downloading actual data files
        result = fromRemote(
            "https://doi.org/10.1594/PANGAEA.918707",
            bbox=True,
            tbox=False,
            convex_hull=False,
            download_data=False,
        )

        assert result is not None
        assert result.get("bbox") is not None

        # The dataset should contain coordinates around Northeast Greenland
        # Reference location extracted today: approximately -21.5°, 76.5°
        bbox = result["bbox"]
        assert isinstance(bbox, list)
        assert len(bbox) == 4

        # Verify the coordinates are in the expected Northeast Greenland region
        minx, miny, maxx, maxy = bbox
        assert abs(minx - 76.5) < 0.1  # Latitude around 76.5°
        assert abs(maxx - 76.5) < 0.1
        assert abs(miny - (-21.5)) < 0.1  # Longitude around -21.5°
        assert abs(maxy - (-21.5)) < 0.1

        # Verify it's actually a point (all coordinates should be nearly the same)
        assert abs(minx - maxx) < 1e-6
        assert abs(miny - maxy) < 1e-6

    def test_pangaea_918707_convex_hull(self):
        """Test extraction of convex hull from PANGAEA dataset 918707 metadata"""
        result = fromRemote(
            "https://doi.org/10.1594/PANGAEA.918707",
            bbox=True,
            tbox=False,
            convex_hull=True,
            download_data=False,
        )

        assert result is not None
        assert result.get("convex_hull") is True

        # Even with convex hull, this should be detected as a point
        # The coordinates might have slight variations due to convex hull processing
        bbox = result.get("bbox")
        assert bbox is not None

        if isinstance(bbox, list) and len(bbox) == 4:
            minx, miny, maxx, maxy = bbox
            # Verify coordinates are in Northeast Greenland region
            assert abs(minx - 76.5) < 0.1
            assert abs(maxx - 76.5) < 0.1
            assert abs(miny - (-21.5)) < 0.1
            assert abs(maxy - (-21.5)) < 0.1

    def test_pangaea_918707_geojson_output_point_geometry(self):
        """Test that PANGAEA 918707 metadata outputs Point geometry in GeoJSON format"""
        result = fromRemote(
            "https://doi.org/10.1594/PANGAEA.918707",
            bbox=True,
            tbox=False,
            convex_hull=False,
            download_data=False,
        )

        # Convert to GeoJSON format - result is in native [lat, lon] order from fromRemote(),
        # so pass native_order=True to swap back to [lon, lat] for RFC 7946 compliance
        geojson_output = format_extent_output(
            result, "geojson", extraction_metadata={}, native_order=True
        )

        # Validate the GeoJSON structure using geojson-validator
        validation_errors = validate_structure(geojson_output)
        assert not validation_errors, f"Invalid GeoJSON structure: {validation_errors}"

        assert geojson_output["type"] == "FeatureCollection"
        assert len(geojson_output["features"]) == 1

        feature = geojson_output["features"][0]
        assert feature["type"] == "Feature"

        # This should be a Point geometry, not a degenerate Polygon
        geometry = feature["geometry"]
        assert geometry["type"] == "Point"

        # Verify coordinates are in Northeast Greenland
        # GeoJSON uses [lon, lat] per RFC 7946
        coords = geometry["coordinates"]
        assert len(coords) == 2
        assert abs(coords[0] - (-21.5)) < 0.1  # Longitude
        assert abs(coords[1] - 76.5) < 0.1  # Latitude

        # Verify extraction metadata indicates it's a point
        assert geojson_output["geoextent_extraction"]["extent_type"] == "point"

    def test_pangaea_918707_convex_hull_geojson_output_point_geometry(self):
        """Test that PANGAEA 918707 metadata with convex hull outputs Point geometry in GeoJSON format"""
        result = fromRemote(
            "https://doi.org/10.1594/PANGAEA.918707",
            bbox=True,
            tbox=False,
            convex_hull=True,
            download_data=False,
        )

        # Convert to GeoJSON format - result is in native [lat, lon] order from fromRemote(),
        # so pass native_order=True to swap back to [lon, lat] for RFC 7946 compliance
        geojson_output = format_extent_output(
            result, "geojson", extraction_metadata={}, native_order=True
        )

        # Validate the GeoJSON structure using geojson-validator
        validation_errors = validate_structure(geojson_output)
        assert not validation_errors, f"Invalid GeoJSON structure: {validation_errors}"

        assert geojson_output["type"] == "FeatureCollection"
        assert len(geojson_output["features"]) == 1

        feature = geojson_output["features"][0]
        assert feature["type"] == "Feature"

        # Even with convex_hull=True, this should be a Point geometry
        geometry = feature["geometry"]
        assert geometry["type"] == "Point"

        # Verify coordinates are in Northeast Greenland region
        # GeoJSON uses [lon, lat] per RFC 7946
        coords = geometry["coordinates"]
        assert len(coords) == 2
        assert abs(coords[0] - (-21.5)) < 0.1  # Longitude
        assert abs(coords[1] - 76.5) < 0.1  # Latitude

        # Extraction metadata should indicate it's a point despite convex hull request
        assert geojson_output["geoextent_extraction"]["extent_type"] == "point"
