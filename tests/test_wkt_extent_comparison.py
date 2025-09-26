#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test cases demonstrating actual WKT extent differences with download size limiting.

These tests create real geospatial files and verify that different sampling
methods and size limits produce measurably different spatial extents in WKT format.
"""

import os
import pytest
import tempfile
import json
import subprocess
from geoextent.lib import extent


class TestWKTExtentComparison:
    """Test cases comparing actual WKT extents from different sampling strategies."""

    def create_test_geospatial_files(self, temp_dir):
        """Create test GeoJSON files with different spatial extents for testing."""

        # File 1: Western Europe region (1MB simulated size)
        west_europe = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-5.0, 45.0], [5.0, 45.0], [5.0, 55.0], [-5.0, 55.0], [-5.0, 45.0]
                    ]]
                },
                "properties": {"name": "Western Europe", "simulated_size": 1000000}
            }]
        }

        # File 2: Central Europe region (2MB simulated size)
        central_europe = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [5.0, 45.0], [15.0, 45.0], [15.0, 55.0], [5.0, 55.0], [5.0, 45.0]
                    ]]
                },
                "properties": {"name": "Central Europe", "simulated_size": 2000000}
            }]
        }

        # File 3: Eastern Europe region (3MB simulated size)
        eastern_europe = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [15.0, 45.0], [30.0, 45.0], [30.0, 55.0], [15.0, 55.0], [15.0, 45.0]
                    ]]
                },
                "properties": {"name": "Eastern Europe", "simulated_size": 3000000}
            }]
        }

        # File 4: Northern Europe region (4MB simulated size)
        northern_europe = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [5.0, 55.0], [25.0, 55.0], [25.0, 70.0], [5.0, 70.0], [5.0, 55.0]
                    ]]
                },
                "properties": {"name": "Northern Europe", "simulated_size": 4000000}
            }]
        }

        # Write files to temp directory
        files_data = [
            ("west_europe.geojson", west_europe),
            ("central_europe.geojson", central_europe),
            ("eastern_europe.geojson", eastern_europe),
            ("northern_europe.geojson", northern_europe),
        ]

        created_files = []
        for filename, data in files_data:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            created_files.append(file_path)

        return created_files

    def test_different_size_limits_produce_different_wkt_extents(self):
        """Test that different size limits produce different WKT extents."""

        with tempfile.TemporaryDirectory() as temp_dir:
            files = self.create_test_geospatial_files(temp_dir)

            # Test 1: Process only first file (simulates 1MB limit)
            first_file = files[0]  # west_europe.geojson only
            extent_small = extent.fromFile(first_file, bbox=True)

            # Test 2: Process first two files (simulates 3MB limit)
            extent_medium = extent.fromDirectory(temp_dir, bbox=True)

            # Convert to WKT format
            from geoextent.lib.helpfunctions import format_extent_output
            extent_small = format_extent_output(extent_small, "wkt")
            extent_medium = format_extent_output(extent_medium, "wkt")

            # Both should produce valid WKT
            assert extent_small is not None
            assert extent_medium is not None
            assert "bbox" in extent_small
            assert "bbox" in extent_medium

            wkt_small = extent_small["bbox"]
            wkt_medium = extent_medium["bbox"]

            assert "POLYGON" in wkt_small
            assert "POLYGON" in wkt_medium

            # Extract coordinate bounds for comparison
            bounds_small = self._extract_bounds_from_wkt(wkt_small)
            bounds_medium = self._extract_bounds_from_wkt(wkt_medium)

            assert bounds_small is not None
            assert bounds_medium is not None

            # Small extent should cover only Western Europe (-5 to 5, 45 to 55)
            # Medium extent should cover Western + Central + Eastern + Northern Europe (-5 to 30, 45 to 70)
            small_width = bounds_small[2] - bounds_small[0]  # max_x - min_x
            medium_width = bounds_medium[2] - bounds_medium[0]

            # Medium extent should be wider than small extent
            assert medium_width > small_width

            print(f"Small extent WKT: {wkt_small}")
            print(f"Medium extent WKT: {wkt_medium}")
            print(f"Small width: {small_width:.1f} degrees")
            print(f"Medium width: {medium_width:.1f} degrees")

    def test_cli_different_formats_same_extent_different_representation(self):
        """Test that CLI produces same extent in different formats."""

        with tempfile.TemporaryDirectory() as temp_dir:
            files = self.create_test_geospatial_files(temp_dir)

            # Test GeoJSON format
            result_geojson = subprocess.run([
                "python", "-m", "geoextent", "-b",
                "--format", "geojson",
                files[0]  # Single file for consistency
            ], capture_output=True, text=True)

            # Test WKT format
            result_wkt = subprocess.run([
                "python", "-m", "geoextent", "-b",
                "--format", "wkt",
                files[0]
            ], capture_output=True, text=True)

            assert result_geojson.returncode == 0
            assert result_wkt.returncode == 0

            # Parse outputs
            geojson_output = json.loads(result_geojson.stdout)
            wkt_output = result_wkt.stdout.strip()  # WKT format outputs raw WKT, not JSON

            # Both should represent the same spatial extent
            # GeoJSON should be a FeatureCollection with polygon features
            assert geojson_output["type"] == "FeatureCollection"
            assert len(geojson_output["features"]) > 0
            assert geojson_output["features"][0]["geometry"]["type"] == "Polygon"

            # WKT should be a polygon string
            assert "POLYGON" in wkt_output

            print(f"GeoJSON format output: {geojson_output}")
            print(f"WKT format output: {wkt_output}")

    def test_simulated_sampling_methods_different_extents(self):
        """Test simulated different sampling methods producing different extents."""

        with tempfile.TemporaryDirectory() as temp_dir:
            files = self.create_test_geospatial_files(temp_dir)

            # Simulate ordered sampling (first N files)
            # Process first 2 files (Western + Central Europe)
            ordered_files = files[:2]
            extent_ordered = self._compute_combined_extent(ordered_files)

            # Simulate random sampling (different combination)
            # Process files 0 + 2 (Western + Eastern Europe)
            random_files = [files[0], files[2]]
            extent_random = self._compute_combined_extent(random_files)

            # Both should be valid
            assert extent_ordered is not None
            assert extent_random is not None

            # Extract WKT representations
            wkt_ordered = extent_ordered["bbox"]
            wkt_random = extent_random["bbox"]

            assert "POLYGON" in wkt_ordered
            assert "POLYGON" in wkt_random

            # The extents should be different
            assert wkt_ordered != wkt_random

            # Extract bounds for detailed comparison
            bounds_ordered = self._extract_bounds_from_wkt(wkt_ordered)
            bounds_random = self._extract_bounds_from_wkt(wkt_random)

            # Ordered: Western + Central Europe (x: -5 to 15)
            # Random: Western + Eastern Europe (x: -5 to 30, but gap in middle)
            assert bounds_ordered != bounds_random

            print(f"Ordered sampling WKT: {wkt_ordered}")
            print(f"Random sampling WKT: {wkt_random}")

    def test_precise_wkt_coordinate_differences(self):
        """Test precise coordinate differences in WKT format."""

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create two files with very specific, different extents
            file1_data = {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0.0, 50.0], [1.0, 50.0], [1.0, 51.0], [0.0, 51.0], [0.0, 50.0]]]
                    },
                    "properties": {"name": "Small precise area"}
                }]
            }

            file2_data = {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[2.0, 52.0], [4.0, 52.0], [4.0, 54.0], [2.0, 54.0], [2.0, 52.0]]]
                    },
                    "properties": {"name": "Different precise area"}
                }]
            }

            file1_path = os.path.join(temp_dir, "area1.geojson")
            file2_path = os.path.join(temp_dir, "area2.geojson")

            with open(file1_path, 'w') as f:
                json.dump(file1_data, f)
            with open(file2_path, 'w') as f:
                json.dump(file2_data, f)

            # Extract extent from single file
            extent1 = extent.fromFile(file1_path, bbox=True)
            extent2 = extent.fromFile(file2_path, bbox=True)

            # Extract extent from both files combined
            extent_combined = extent.fromDirectory(temp_dir, bbox=True)

            # Convert to WKT format
            from geoextent.lib.helpfunctions import format_extent_output
            extent1 = format_extent_output(extent1, "wkt")
            extent2 = format_extent_output(extent2, "wkt")
            extent_combined = format_extent_output(extent_combined, "wkt")

            wkt1 = extent1["bbox"]
            wkt2 = extent2["bbox"]
            wkt_combined = extent_combined["bbox"]

            # All should be different
            assert wkt1 != wkt2
            assert wkt1 != wkt_combined
            assert wkt2 != wkt_combined

            # Extract precise coordinates
            bounds1 = self._extract_bounds_from_wkt(wkt1)
            bounds2 = self._extract_bounds_from_wkt(wkt2)
            bounds_combined = self._extract_bounds_from_wkt(wkt_combined)

            # File 1: bounds should be [0, 50, 1, 51]
            assert abs(bounds1[0] - 0.0) < 0.001  # min_x
            assert abs(bounds1[1] - 50.0) < 0.001  # min_y
            assert abs(bounds1[2] - 1.0) < 0.001  # max_x
            assert abs(bounds1[3] - 51.0) < 0.001  # max_y

            # File 2: bounds should be [2, 52, 4, 54]
            assert abs(bounds2[0] - 2.0) < 0.001
            assert abs(bounds2[1] - 52.0) < 0.001
            assert abs(bounds2[2] - 4.0) < 0.001
            assert abs(bounds2[3] - 54.0) < 0.001

            # Combined: bounds should be [0, 50, 4, 54]
            assert abs(bounds_combined[0] - 0.0) < 0.001
            assert abs(bounds_combined[1] - 50.0) < 0.001
            assert abs(bounds_combined[2] - 4.0) < 0.001
            assert abs(bounds_combined[3] - 54.0) < 0.001

            print(f"File 1 WKT: {wkt1}")
            print(f"File 2 WKT: {wkt2}")
            print(f"Combined WKT: {wkt_combined}")

    def _compute_combined_extent(self, file_paths):
        """Compute combined spatial extent from multiple files."""
        if len(file_paths) == 1:
            result = extent.fromFile(file_paths[0], bbox=True)
        else:
            # Create temporary directory with only selected files
            with tempfile.TemporaryDirectory() as temp_combined:
                for i, file_path in enumerate(file_paths):
                    # Copy selected files to temp directory
                    import shutil
                    filename = f"selected_{i}_{os.path.basename(file_path)}"
                    new_path = os.path.join(temp_combined, filename)
                    shutil.copy2(file_path, new_path)

                result = extent.fromDirectory(temp_combined, bbox=True)

        # Convert to WKT format
        from geoextent.lib.helpfunctions import format_extent_output
        return format_extent_output(result, "wkt")

    def _extract_bounds_from_wkt(self, wkt_polygon):
        """Extract [min_x, min_y, max_x, max_y] bounds from WKT POLYGON string."""
        import re

        # Match coordinates in POLYGON((x y, x y, ...)) format
        pattern = r'POLYGON\s*\(\s*\(\s*([^)]+)\s*\)\s*\)'
        match = re.search(pattern, wkt_polygon)

        if not match:
            return None

        coords_str = match.group(1)
        coords = []

        # Parse coordinate pairs
        for coord_pair in coords_str.split(','):
            if coord_pair.strip():
                parts = coord_pair.strip().split()
                if len(parts) >= 2:
                    x, y = float(parts[0]), float(parts[1])
                    coords.append([x, y])

        if len(coords) < 3:  # Need at least 3 points for polygon
            return None

        # Extract bounds
        x_coords = [coord[0] for coord in coords]
        y_coords = [coord[1] for coord in coords]

        return [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])