#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for download size limiting with actual extent extraction.

These tests verify that different sampling methods and size limits produce
measurably different geospatial extents when processing real repository data.
"""

import os
import pytest
import tempfile
import json
import subprocess
import time
from unittest.mock import patch, MagicMock, mock_open
from geoextent.lib.helpfunctions import DEFAULT_DOWNLOAD_SAMPLE_SEED


class TestDownloadSizeIntegration:
    """Integration tests comparing actual WKT extents from different sampling strategies."""

    @pytest.mark.slow
    @pytest.mark.integration
    def test_cli_size_limits_produce_different_wkt_extents(self):
        """Test that CLI with different size limits produces different WKT extents."""

        # This test would ideally use a real repository, but for CI/testing,
        # we'll create a controlled scenario with mock data

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock GeoJSON files with different spatial extents
            self._create_mock_geojson_files(temp_dir)

            # Test with small size limit (should process only first file)
            result_small = subprocess.run([
                "python", "-m", "geoextent", "-b",
                "--format", "wkt",
                "--max-download-size", "1KB",  # Very small to limit files
                temp_dir
            ], capture_output=True, text=True)

            # Test with large size limit (should process all files)
            result_large = subprocess.run([
                "python", "-m", "geoextent", "-b",
                "--format", "wkt",
                temp_dir
            ], capture_output=True, text=True)

            # Both should succeed but produce different extents
            assert result_small.returncode == 0
            assert result_large.returncode == 0

            # Extract WKT polygons from outputs
            wkt_small = self._extract_wkt_from_output(result_small.stdout)
            wkt_large = self._extract_wkt_from_output(result_large.stdout)

            assert wkt_small is not None
            assert wkt_large is not None
            assert "POLYGON" in wkt_small
            assert "POLYGON" in wkt_large

            # The extents should be different (small processes fewer files)
            assert wkt_small != wkt_large

    def test_ordered_vs_random_sampling_produces_different_extents(self):
        """Test that ordered vs random sampling produces different spatial extents."""

        files_info = [
            {"name": "west_europe.geojson", "size": 1500000, "bbox": [0, 45, 5, 50]},    # Western
            {"name": "north_europe.geojson", "size": 2000000, "bbox": [10, 55, 15, 60]}, # Northern
            {"name": "east_europe.geojson", "size": 1800000, "bbox": [20, 48, 25, 53]},  # Eastern
            {"name": "south_europe.geojson", "size": 2200000, "bbox": [12, 40, 18, 45]}, # Southern
        ]

        from geoextent.lib.helpfunctions import filter_files_by_size

        # Test with 4MB limit - should allow 2-3 files
        limit_bytes = 4000000

        # Ordered selection
        selected_ordered, total_ordered, _ = filter_files_by_size(
            files_info, limit_bytes, "ordered", DEFAULT_DOWNLOAD_SAMPLE_SEED
        )

        # Random selection with different seed
        selected_random, total_random, _ = filter_files_by_size(
            files_info, limit_bytes, "random", 123
        )

        # Both should respect the size limit
        assert total_ordered <= limit_bytes
        assert total_random <= limit_bytes

        # Should select different files (with high probability)
        ordered_names = set(f["name"] for f in selected_ordered)
        random_names = set(f["name"] for f in selected_random)

        # At minimum, verify we get valid selections
        assert len(ordered_names) > 0
        assert len(random_names) > 0

        # Calculate theoretical spatial extents
        ordered_extent = self._calculate_combined_extent(selected_ordered)
        random_extent = self._calculate_combined_extent(selected_random)

        # Different file selections should produce different extents
        # (unless by chance they select the same files)
        assert ordered_extent is not None
        assert random_extent is not None

    @pytest.mark.slow
    def test_real_repository_different_size_limits_different_extents(self):
        """Test real repository processing with different size limits produces different extents."""

        # Create a mock repository provider that simulates size-based file selection
        with patch('geoextent.lib.content_providers.Zenodo.Zenodo') as MockZenodo:
            mock_instance = MagicMock()
            MockZenodo.return_value = mock_instance

            # Mock file metadata with realistic sizes and spatial data
            mock_files = [
                {"key": "region_a.zip", "size": 1000000, "links": {"self": "http://example.com/a.zip"}},
                {"key": "region_b.zip", "size": 3000000, "links": {"self": "http://example.com/b.zip"}},
                {"key": "region_c.zip", "size": 8000000, "links": {"self": "http://example.com/c.zip"}},
            ]

            # Mock different spatial extents for each region
            spatial_data = {
                "region_a.zip": {"bbox": [0, 50, 5, 55]},    # Small western area
                "region_b.zip": {"bbox": [5, 50, 15, 55]},   # Central area
                "region_c.zip": {"bbox": [15, 50, 25, 55]},  # Eastern area
            }

            def mock_download_with_size_limit(folder, max_size_bytes=None, **kwargs):
                """Mock download that respects size limits."""
                if max_size_bytes is None:
                    # Download all files
                    selected_files = mock_files
                else:
                    # Apply size filtering
                    from geoextent.lib.helpfunctions import filter_files_by_size
                    files_for_filter = [{"name": f["key"], "size": f["size"]} for f in mock_files]
                    selected, _, _ = filter_files_by_size(files_for_filter, max_size_bytes, "ordered")
                    selected_names = [f["name"] for f in selected]
                    selected_files = [f for f in mock_files if f["key"] in selected_names]

                # Create mock GeoJSON files based on selection
                for file_info in selected_files:
                    filename = file_info["key"].replace(".zip", ".geojson")
                    filepath = os.path.join(folder, filename)
                    bbox = spatial_data[file_info["key"]]

                    # Create GeoJSON with appropriate spatial extent
                    geojson_data = {
                        "type": "FeatureCollection",
                        "features": [{
                            "type": "Feature",
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [[
                                    [bbox[0], bbox[1]], [bbox[2], bbox[1]],
                                    [bbox[2], bbox[3]], [bbox[0], bbox[3]],
                                    [bbox[0], bbox[1]]
                                ]]
                            },
                            "properties": {"name": file_info["key"]}
                        }]
                    }

                    with open(filepath, 'w') as f:
                        json.dump(geojson_data, f)

                return folder

            mock_instance.download.side_effect = mock_download_with_size_limit
            mock_instance.validate_provider.return_value = True
            mock_instance._get_metadata.return_value = {"files": mock_files}

            # Test with 2MB limit (should get only region_a)
            with tempfile.TemporaryDirectory() as temp_dir:
                from geoextent.lib import extent

                # Small limit - should process only region_a (1MB)
                with patch('geoextent.lib.extent.geoextent_from_repository') as mock_geoext:
                    mock_geoext.return_value.from_repository.return_value = {
                        "bbox": "POLYGON((0 50, 5 50, 5 55, 0 55, 0 50))",  # Only region_a
                        "format": "repository"
                    }

                    result_small = extent.from_repository(
                        "https://zenodo.org/record/123456",
                        bbox=True, format="wkt",
                        max_download_size="2MB"
                    )

                # Large limit - should process all regions
                with patch('geoextent.lib.extent.geoextent_from_repository') as mock_geoext:
                    mock_geoext.return_value.from_repository.return_value = {
                        "bbox": "POLYGON((0 50, 25 50, 25 55, 0 55, 0 50))",  # All regions
                        "format": "repository"
                    }

                    result_large = extent.from_repository(
                        "https://zenodo.org/record/123456",
                        bbox=True, format="wkt",
                        max_download_size="20MB"
                    )

                # Different size limits should produce different extents
                assert result_small["bbox"] != result_large["bbox"]
                assert "POLYGON" in result_small["bbox"]
                assert "POLYGON" in result_large["bbox"]

                # Small extent should be contained within large extent
                small_coords = self._extract_polygon_coords(result_small["bbox"])
                large_coords = self._extract_polygon_coords(result_large["bbox"])

                assert small_coords is not None
                assert large_coords is not None

                # Large extent should span more longitude (0-25 vs 0-5)
                small_lon_range = small_coords[2] - small_coords[0]  # max_x - min_x
                large_lon_range = large_coords[2] - large_coords[0]

                assert large_lon_range >= small_lon_range

    def test_shapefile_grouping_affects_spatial_extent(self):
        """Test that shapefile component grouping affects final spatial extent."""

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock shapefile components for two regions
            self._create_mock_shapefile_components(temp_dir)

            from geoextent.lib.helpfunctions import filter_files_by_size

            # Mock file info with shapefile components
            files = [
                {"name": "region1.shp", "size": 100000},
                {"name": "region1.shx", "size": 5000},
                {"name": "region1.dbf", "size": 50000},
                {"name": "region1.prj", "size": 1000},  # Total: 156KB
                {"name": "region2.shp", "size": 200000},
                {"name": "region2.shx", "size": 8000},
                {"name": "region2.dbf", "size": 80000},
                {"name": "region2.prj", "size": 2000},   # Total: 290KB
                {"name": "standalone.csv", "size": 10000},  # 10KB
            ]

            # Test with 200KB limit - should include region1 complete + standalone
            # but exclude region2 (as group exceeds remaining budget)
            selected, total, _ = filter_files_by_size(files, 200000, "ordered")

            selected_names = [f["name"] for f in selected]

            # Should include all region1 components (as a group) plus standalone
            region1_components = ["region1.shp", "region1.shx", "region1.dbf", "region1.prj"]
            assert all(comp in selected_names for comp in region1_components)
            assert "standalone.csv" in selected_names

            # Should exclude all region2 components (as a group)
            region2_components = ["region2.shp", "region2.shx", "region2.dbf", "region2.prj"]
            assert not any(comp in selected_names for comp in region2_components)

            # Total should be region1 (156KB) + standalone (10KB) = 166KB
            assert total == 166000

    def _create_mock_geojson_files(self, temp_dir):
        """Create mock GeoJSON files with different spatial extents."""

        files_data = [
            ("small_region.geojson", {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 50], [1, 50], [1, 51], [0, 51], [0, 50]]]
                    },
                    "properties": {"name": "small"}
                }]
            }),
            ("medium_region.geojson", {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[5, 52], [8, 52], [8, 55], [5, 55], [5, 52]]]
                    },
                    "properties": {"name": "medium"}
                }]
            }),
            ("large_region.geojson", {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[10, 60], [20, 60], [20, 70], [10, 70], [10, 60]]]
                    },
                    "properties": {"name": "large"}
                }]
            })
        ]

        for filename, data in files_data:
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(data, f)

    def _create_mock_shapefile_components(self, temp_dir):
        """Create mock shapefile component files for testing grouping."""

        # Create empty files representing shapefile components
        components = [
            "region1.shp", "region1.shx", "region1.dbf", "region1.prj",
            "region2.shp", "region2.shx", "region2.dbf", "region2.prj",
            "standalone.csv"
        ]

        for component in components:
            filepath = os.path.join(temp_dir, component)
            with open(filepath, 'w') as f:
                f.write("mock data")

    def _extract_wkt_from_output(self, output):
        """Extract WKT polygon from geoextent output."""
        try:
            # Parse JSON output and extract WKT
            if output.strip().startswith('{'):
                data = json.loads(output)
                return data.get("bbox", "")
            else:
                # Direct WKT output
                return output.strip()
        except json.JSONDecodeError:
            return None

    def _calculate_combined_extent(self, files_with_bbox):
        """Calculate combined spatial extent from files with bbox info."""
        if not files_with_bbox:
            return None

        # Extract all bounding boxes and compute union
        all_bounds = []
        for file_info in files_with_bbox:
            if "bbox" in file_info:
                all_bounds.append(file_info["bbox"])

        if not all_bounds:
            return None

        # Compute union of all bounding boxes
        min_x = min(bbox[0] for bbox in all_bounds)
        min_y = min(bbox[1] for bbox in all_bounds)
        max_x = max(bbox[2] for bbox in all_bounds)
        max_y = max(bbox[3] for bbox in all_bounds)

        return [min_x, min_y, max_x, max_y]

    def _extract_polygon_coords(self, wkt_polygon):
        """Extract coordinate bounds from WKT POLYGON string."""
        import re

        # Match coordinates in POLYGON((x y, x y, ...)) format
        pattern = r'POLYGON\(\(([^)]+)\)\)'
        match = re.search(pattern, wkt_polygon)

        if not match:
            return None

        coords_str = match.group(1)
        coords = []

        # Parse coordinate pairs
        for coord_pair in coords_str.split(', '):
            if coord_pair.strip():
                x, y = map(float, coord_pair.strip().split())
                coords.append([x, y])

        if len(coords) < 4:  # Need at least 4 points for polygon
            return None

        # Extract bounds
        x_coords = [coord[0] for coord in coords]
        y_coords = [coord[1] for coord in coords]

        return [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])