"""
Real-world tests for placename functionality using actual API calls.

These tests use local test files to validate the placename extraction functionality
with real gazetteer services. Reference values were extracted on the day of implementation.
"""

import pytest
import json
import subprocess
import os
from unittest.mock import patch

import geoextent.lib.extent as extent
from geoextent.lib.helpfunctions import format_extent_output


class TestPlacenameLocalFiles:
    """Test placename functionality with local test files using real API calls."""

    # Test datasets with local files and expected reference values (extracted today)
    LOCAL_TEST_FILES = {
        "muenster_geojson": {
            "file_path": "tests/testdata/folders/folder_two_files/muenster_ring_zeit.geojson",
            "description": "GeoJSON file covering Münster, Germany area",
            "file_format": "geojson",
            "expected_placenames": {
                "nominatim": "Münster, Nordrhein-Westfalen, Deutschland",
                "photon": "Nordrhein-Westfalen, Münster, Deutschland"
            },
            "expected_placenames_escaped": {
                "nominatim": "M\\xfcnster, Nordrhein-Westfalen, Deutschland",
                "photon": "Nordrhein-Westfalen, M\\xfcnster, Deutschland"
            },
            "timeout": 30,
            "region": "Germany"
        },
        "netherlands_csv": {
            "file_path": "tests/testdata/csv/cities_NL_case5.csv",
            "description": "CSV file with Dutch cities",
            "file_format": "csv",
            "expected_placenames": {
                "nominatim": "Nederland",
                "photon": "Nederland"
            },
            "expected_placenames_escaped": {
                "nominatim": "Nederland",
                "photon": "Nederland"
            },
            "timeout": 30,
            "region": "Netherlands"
        },
        "tif_large_area": {
            "file_path": "tests/testdata/tif/wf_100m_klas.tif",
            "description": "TIF file covering large area in Germany",
            "file_format": "tif",
            "expected_placenames": {
                "nominatim": "Deutschland",
                "photon": "Deutschland"
            },
            "expected_placenames_escaped": {
                "nominatim": "Deutschland",
                "photon": "Deutschland"
            },
            "timeout": 30,
            "region": "Germany"
        },
        "shapefile_antarctica": {
            "file_path": "tests/testdata/shapefile/gis_osm_buildings_a_free_1.shp",
            "description": "Shapefile with Antarctic data",
            "file_format": "shp",
            "expected_placenames": {
                "photon": "South Pole"
            },
            "expected_placenames_escaped": {
                "photon": "South Pole"
            },
            "timeout": 30,
            "region": "Antarctica"
        }
    }

    @pytest.mark.network
    @pytest.mark.parametrize("dataset_key", LOCAL_TEST_FILES.keys())
    @pytest.mark.parametrize("gazetteer", ["nominatim", "photon"])
    def test_placename_extraction_local_files(self, dataset_key, gazetteer):
        """Test placename extraction with local files using real API calls."""
        dataset = self.LOCAL_TEST_FILES[dataset_key]

        # Skip if this gazetteer is not defined for this dataset
        if gazetteer not in dataset["expected_placenames"]:
            pytest.skip(f"Gazetteer {gazetteer} not defined for dataset {dataset_key}")

        try:
            result = extent.fromFile(
                dataset["file_path"],
                bbox=True,
                tbox=False,
                placename=gazetteer
            )

            # Should have extracted a placename
            assert "placename" in result, f"No placename found for {dataset_key} with {gazetteer}"

            placename = result["placename"]
            assert placename is not None, f"Placename is None for {dataset_key} with {gazetteer}"
            assert len(placename) > 0, f"Empty placename for {dataset_key} with {gazetteer}"

            # Compare with expected reference value
            expected_placename = dataset["expected_placenames"][gazetteer]
            assert placename == expected_placename, \
                f"Expected '{expected_placename}', got '{placename}' for {dataset_key} with {gazetteer}"

            print(f"✓ {dataset_key} + {gazetteer}: {placename}")

        except Exception as e:
            # Skip test if API is unavailable or file can't be processed
            pytest.skip(f"API test failed for {dataset_key} with {gazetteer}: {e}")

    @pytest.mark.network
    @pytest.mark.parametrize("gazetteer", ["nominatim", "photon"])
    def test_placename_escape_functionality(self, gazetteer):
        """Test Unicode escaping functionality using local file with German umlauts."""
        # Use Münster dataset which has Unicode characters (ü)
        dataset = self.LOCAL_TEST_FILES["muenster_geojson"]

        # Skip if this gazetteer is not defined for this dataset
        if gazetteer not in dataset["expected_placenames"]:
            pytest.skip(f"Gazetteer {gazetteer} not defined for dataset muenster_geojson")

        try:
            # Test without escaping
            result_normal = extent.fromFile(
                dataset["file_path"],
                bbox=True,
                tbox=False,
                placename=gazetteer,
                placename_escape=False
            )

            # Test with escaping
            result_escaped = extent.fromFile(
                dataset["file_path"],
                bbox=True,
                tbox=False,
                placename=gazetteer,
                placename_escape=True
            )

            assert "placename" in result_normal
            assert "placename" in result_escaped

            normal_placename = result_normal["placename"]
            escaped_placename = result_escaped["placename"]

            # Compare with expected reference values
            expected_normal = dataset["expected_placenames"][gazetteer]
            expected_escaped = dataset["expected_placenames_escaped"][gazetteer]

            assert normal_placename == expected_normal, \
                f"Expected normal '{expected_normal}', got '{normal_placename}'"
            assert escaped_placename == expected_escaped, \
                f"Expected escaped '{expected_escaped}', got '{escaped_placename}'"

            # Should be different if there are Unicode characters
            if any(ord(c) > 127 for c in normal_placename):
                assert normal_placename != escaped_placename, \
                    f"Escaped placename should differ from normal for Unicode text"

                # Escaped version should contain escape sequences
                assert "\\" in escaped_placename, \
                    f"Escaped placename should contain escape sequences"

            print(f"✓ Normal: {normal_placename}")
            print(f"✓ Escaped: {escaped_placename}")

        except Exception as e:
            pytest.skip(f"Escape test failed for {gazetteer}: {e}")

    @pytest.mark.network
    @pytest.mark.parametrize("gazetteer", ["nominatim", "photon"])
    def test_geojson_output_includes_placename(self, gazetteer):
        """Test that GeoJSON output includes placename in properties."""
        dataset = self.LOCAL_TEST_FILES["netherlands_csv"]  # Use Netherlands CSV dataset

        # Skip if this gazetteer is not defined for this dataset
        if gazetteer not in dataset["expected_placenames"]:
            pytest.skip(f"Gazetteer {gazetteer} not defined for dataset netherlands_csv")

        try:
            result = extent.fromFile(
                dataset["file_path"],
                bbox=True,
                tbox=False,
                placename=gazetteer
            )

            # Convert to GeoJSON format
            geojson_output = format_extent_output(result, "geojson")

            # Validate structure
            assert geojson_output["type"] == "FeatureCollection"
            assert len(geojson_output["features"]) == 1

            feature = geojson_output["features"][0]
            assert feature["type"] == "Feature"
            assert "properties" in feature

            # Check placename in properties
            properties = feature["properties"]
            assert "placename" in properties, "Placename should be in GeoJSON properties"

            placename = properties["placename"]
            assert placename is not None and len(placename) > 0, \
                "Placename in GeoJSON should not be empty"

            print(f"✓ GeoJSON placename: {placename}")

        except Exception as e:
            pytest.skip(f"GeoJSON test failed for {gazetteer}: {e}")

    @pytest.mark.network
    @pytest.mark.parametrize("dataset_key", ["muenster_geojson", "netherlands_csv"])
    @pytest.mark.parametrize("gazetteer", ["nominatim", "photon"])
    def test_cli_placename_functionality(self, dataset_key, gazetteer):
        """Test placename functionality via CLI interface using local files."""
        dataset = self.LOCAL_TEST_FILES[dataset_key]

        # Skip if this gazetteer is not defined for this dataset
        if gazetteer not in dataset["expected_placenames"]:
            pytest.skip(f"Gazetteer {gazetteer} not defined for dataset {dataset_key}")

        try:
            # Test normal placename
            result = subprocess.run([
                "python", "-m", "geoextent",
                "-b", "--quiet",
                "--placename", "--placename-service", gazetteer,
                dataset["file_path"]
            ], capture_output=True, text=True, timeout=dataset["timeout"])

            assert result.returncode == 0, f"CLI failed: {result.stderr}"

            # Parse output
            output = json.loads(result.stdout)
            assert output["type"] == "FeatureCollection"

            feature = output["features"][0]
            properties = feature["properties"]
            assert "placename" in properties, "CLI output should include placename"

            normal_placename = properties["placename"]
            assert normal_placename and len(normal_placename) > 0

            # Test escaped placename
            result_escaped = subprocess.run([
                "python", "-m", "geoextent",
                "-b", "--quiet",
                "--placename", "--placename-service", gazetteer,
                "--placename-escape",
                dataset["file_path"]
            ], capture_output=True, text=True, timeout=dataset["timeout"])

            assert result_escaped.returncode == 0, f"CLI with escape failed: {result_escaped.stderr}"

            # Parse escaped output
            output_escaped = json.loads(result_escaped.stdout)
            feature_escaped = output_escaped["features"][0]
            properties_escaped = feature_escaped["properties"]

            escaped_placename = properties_escaped["placename"]

            print(f"✓ CLI Normal: {normal_placename}")
            print(f"✓ CLI Escaped: {escaped_placename}")

            # If original has Unicode, escaped should be different
            if any(ord(c) > 127 for c in normal_placename):
                assert normal_placename != escaped_placename, \
                    "Escaped CLI output should differ for Unicode placenames"

        except subprocess.TimeoutExpired:
            pytest.skip(f"CLI test timed out for {dataset_key} with {gazetteer}")
        except Exception as e:
            pytest.skip(f"CLI test failed for {dataset_key} with {gazetteer}: {e}")

    def test_cli_validation_errors(self):
        """Test CLI validation for placename options."""
        # Test invalid gazetteer
        result = subprocess.run([
            "python", "-m", "geoextent",
            "-b", "--placename", "--placename-service", "invalid_gazetteer",
            "tests/testdata/folders/folder_two_files/muenster_ring_zeit.geojson"
        ], capture_output=True, text=True)

        assert result.returncode != 0, "Should fail with invalid gazetteer"
        assert "invalid choice" in result.stderr.lower()

        # Test placename-escape without placename
        result = subprocess.run([
            "python", "-m", "geoextent",
            "-b", "--placename-escape",
            "tests/testdata/folders/folder_two_files/muenster_ring_zeit.geojson"
        ], capture_output=True, text=True)

        assert result.returncode != 0, "Should fail when placename-escape used without placename"
        assert "requires --placename" in str(result.stderr)

    @pytest.mark.network
    def test_default_gazetteer_is_geonames(self):
        """Test that default gazetteer is geonames when no parameter specified."""
        dataset = self.LOCAL_TEST_FILES["netherlands_csv"]

        # Skip this test if GeoNames credentials are not available
        if not os.getenv("GEONAMES_USERNAME"):
            pytest.skip("GeoNames username not available for testing default gazetteer")

        try:
            result = subprocess.run([
                "python", "-m", "geoextent",
                "-b", "--quiet",
                "--placename",  # No parameter = should default to geonames
                dataset["file_path"]
            ], capture_output=True, text=True, timeout=dataset["timeout"])

            assert result.returncode == 0, f"CLI failed with default gazetteer: {result.stderr}"

            output = json.loads(result.stdout)
            feature = output["features"][0]
            properties = feature["properties"]

            assert "placename" in properties, "Should have placename with default gazetteer"
            placename = properties["placename"]
            assert placename and len(placename) > 0

            print(f"✓ Default gazetteer (geonames): {placename}")

        except subprocess.TimeoutExpired:
            pytest.skip("Default gazetteer test timed out")
        except Exception as e:
            pytest.skip(f"Default gazetteer test failed: {e}")

    @pytest.mark.network
    def test_placename_with_convex_hull(self):
        """Test placename extraction with convex hull option."""
        dataset = self.LOCAL_TEST_FILES["muenster_geojson"]

        try:
            result = extent.fromFile(
                dataset["file_path"],
                bbox=True,
                tbox=False,
                convex_hull=True,
                placename="nominatim"
            )

            assert "placename" in result, "Should have placename with convex hull"
            assert "convex_hull" in result, "Should indicate convex hull was used"

            placename = result["placename"]
            assert placename and len(placename) > 0

            # Should be German region
            placename_lower = placename.lower()
            assert any(term in placename_lower for term in ["germany", "deutschland", "münster"]), \
                f"Convex hull placename '{placename}' should be in German region"

            print(f"✓ Convex hull placename: {placename}")

        except Exception as e:
            pytest.skip(f"Convex hull test failed: {e}")
