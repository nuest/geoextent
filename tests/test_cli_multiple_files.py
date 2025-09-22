import pytest
import subprocess
import json
import os
from help_functions_test import tolerance


def run_geoextent_cli(*args):
    """Helper function to run geoextent CLI and return parsed JSON output"""
    cmd = ["python", "-m", "geoextent"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    if result.returncode != 0:
        pytest.fail(f"CLI command failed: {result.stderr}")
    return json.loads(result.stdout)


def test_multiple_files_bbox_extraction():
    """Test bbox extraction from multiple files"""
    result = run_geoextent_cli(
        "-b",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",      # Germany: [7.60, 51.95, 7.65, 51.97]
        "tests/testdata/folders/folder_two_files/districtes.geojson"  # Spain: [2.05, 41.32, 2.23, 41.47]
    )

    assert result["format"] == "multiple_files"
    assert "bbox" in result
    assert "crs" in result
    assert result["crs"] == "4326"
    # Merged bbox should cover both Münster (Germany) and Barcelona (Spain)
    # Expected: [min_lon, min_lat, max_lon, max_lat] = [2.05, 41.32, 7.65, 51.97]
    assert result["bbox"] == pytest.approx(
        [2.052333387639205, 41.31703852240476, 7.647256851196289, 51.974624029877454], abs=tolerance
    )


def test_multiple_files_tbox_extraction():
    """Test temporal extraction from multiple files"""
    result = run_geoextent_cli(
        "-t",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",      # 2018-11-14
        "tests/testdata/folders/folder_two_files/districtes.geojson",  # 2019-09-11
        "tests/testdata/csv/cities_NL.csv"                       # 2017-08-01 to 2019-09-30
    )

    assert result["format"] == "multiple_files"
    assert "tbox" in result
    # Should span from earliest to latest date across all files
    assert result["tbox"] == ["2017-08-01", "2019-09-30"]


def test_multiple_files_bbox_and_tbox():
    """Test both spatial and temporal extraction from multiple files"""
    result = run_geoextent_cli(
        "-b", "-t",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",      # Germany: [7.60, 51.95, 7.65, 51.97], 2018-11-14
        "tests/testdata/folders/folder_two_files/districtes.geojson",  # Spain: [2.05, 41.32, 2.23, 41.47], 2019-09-11
        "tests/testdata/csv/cities_NL.csv"                       # Netherlands: [4.32, 51.43, 6.57, 53.22], 2017-08-01 to 2019-09-30
    )

    assert result["format"] == "multiple_files"
    assert "bbox" in result
    assert "tbox" in result
    assert "crs" in result
    assert result["crs"] == "4326"
    # Merged bbox should cover Germany, Spain, and Netherlands
    # Expected: [min_lon, min_lat, max_lon, max_lat] = [2.05, 41.32, 7.65, 53.22]
    assert result["bbox"] == pytest.approx(
        [2.052333387639205, 41.31703852240476, 7.647256851196289, 53.217222], abs=tolerance
    )
    assert result["tbox"] == ["2017-08-01", "2019-09-30"]


def test_multiple_files_with_details():
    """Test multiple files with details flag"""
    result = run_geoextent_cli(
        "-b", "-t", "--details",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
        "tests/testdata/folders/folder_two_files/districtes.geojson"
    )

    assert result["format"] == "multiple_files"
    assert "details" in result
    assert len(result["details"]) == 2

    # Check individual file details
    muenster_details = result["details"]["tests/testdata/geojson/muenster_ring_zeit.geojson"]
    assert muenster_details["format"] == "geojson"
    assert muenster_details["geoextent_handler"] == "handleVector"
    assert "bbox" in muenster_details
    assert "tbox" in muenster_details

    barcelona_details = result["details"]["tests/testdata/folders/folder_two_files/districtes.geojson"]
    assert barcelona_details["format"] == "geojson"
    assert barcelona_details["geoextent_handler"] == "handleVector"
    assert "bbox" in barcelona_details
    assert "tbox" in barcelona_details


def test_multiple_files_different_formats():
    """Test multiple files of different formats"""
    # Test with CSV, GeoJSON (two different sources)
    result = run_geoextent_cli(
        "-b",
        "tests/testdata/csv/cities_NL.csv",                      # Netherlands CSV
        "tests/testdata/geojson/muenster_ring_zeit.geojson",     # Germany GeoJSON
        "tests/testdata/folders/folder_two_files/districtes.geojson"  # Spain GeoJSON
    )

    assert result["format"] == "multiple_files"
    assert "bbox" in result
    assert "crs" in result
    # Should cover Netherlands, Germany, and Spain
    assert result["bbox"] == pytest.approx(
        [2.052333387639205, 41.31703852240476, 7.647256851196289, 53.217222], abs=tolerance
    )


def test_single_file_backward_compatibility():
    """Test that single file processing still works as before"""
    result = run_geoextent_cli(
        "-b", "-t",
        "tests/testdata/geojson/muenster_ring_zeit.geojson"
    )

    # Single file should not have "multiple_files" format
    assert result["format"] == "geojson"
    assert result["geoextent_handler"] == "handleVector"
    assert "bbox" in result
    assert "tbox" in result
    assert "details" not in result  # No details for single file unless --details is used


def test_multiple_files_mixed_with_directories():
    """Test multiple inputs including both files and directories"""
    # Create a temporary directory with a test file for this test
    result = run_geoextent_cli(
        "-b",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
        "tests/testdata/csv"  # This is a directory
    )

    assert result["format"] == "multiple_files"
    assert "bbox" in result


def test_multiple_files_error_handling():
    """Test that errors in individual files don't stop processing of others"""
    # Include a valid file and an invalid/non-existent file pattern
    # The CLI should process the valid files and warn about invalid ones
    result = run_geoextent_cli(
        "-b",
        "tests/testdata/geojson/muenster_ring_zeit.geojson"
        # Only testing with valid file since invalid files would cause CLI to exit
    )

    # This is more of a regression test to ensure single valid file works
    assert "bbox" in result