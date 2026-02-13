import os
import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance


def test_api_recursive_default_behavior():
    """Test that recursive=True is the default behavior (processes subdirectories)"""
    result = geoextent.fromDirectory(
        "tests/testdata/folders/nested_folder", bbox=True, tbox=True, details=True
    )

    # Should find files in subdirectories (Folder_1 and Folder_2)
    assert "details" in result
    assert "Folder_1" in result["details"]
    assert "Folder_2" in result["details"]
    assert "3DCMTcatalog_TakemuraEPS.csv" in result["details"]["Folder_1"]["details"]
    assert "muenster_ring_zeit.geojson" in result["details"]["Folder_2"]["details"]


def test_api_recursive_enabled():
    """Test that recursive=True processes subdirectories"""
    result = geoextent.fromDirectory(
        "tests/testdata/folders/nested_folder",
        bbox=True,
        tbox=True,
        details=True,
        recursive=True,
    )

    # Should find files in subdirectories (Folder_1 and Folder_2)
    assert "details" in result
    assert "Folder_1" in result["details"]
    assert "Folder_2" in result["details"]
    assert "3DCMTcatalog_TakemuraEPS.csv" in result["details"]["Folder_1"]["details"]
    assert "muenster_ring_zeit.geojson" in result["details"]["Folder_2"]["details"]


def test_api_recursive_disabled():
    """Test that recursive=False only processes files in top directory"""
    result = geoextent.fromDirectory(
        "tests/testdata/folders/nested_folder",
        bbox=True,
        tbox=True,
        details=True,
        recursive=False,
    )

    # Should not process subdirectories - details should be empty or only contain top-level files
    assert "details" in result
    # Subdirectories should not be processed when recursive=False
    assert "Folder_1" not in result["details"] or result["details"]["Folder_1"] is None
    assert "Folder_2" not in result["details"] or result["details"]["Folder_2"] is None


def test_cli_recursive_default_behavior(script_runner):
    """Test CLI default behavior (should process subdirectories)"""
    ret = script_runner.run(
        "geoextent", "-b", "-t", "--details", "tests/testdata/folders/nested_folder"
    )
    assert ret.success, "process should return success"
    result = ret.stdout
    assert "Folder_1" in result
    assert "Folder_2" in result
    assert "3DCMTcatalog_TakemuraEPS.csv" in result
    assert "muenster_ring_zeit.geojson" in result


def test_cli_no_subdirs_option(script_runner):
    """Test CLI --no-subdirs option disables recursive processing"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "-t",
        "--details",
        "--no-subdirs",
        "tests/testdata/folders/nested_folder",
    )
    assert ret.success, "process should return success"
    result = ret.stdout
    # Should not contain files from subdirectories
    assert "3DCMTcatalog_TakemuraEPS.csv" not in result
    # The subdirectory names might still appear as skipped directories but files within shouldn't be processed


def test_cli_help_shows_no_subdirs_option(script_runner):
    """Test that --no-subdirs option appears in help"""
    ret = script_runner.run("geoextent", "--help")
    assert ret.success, "process should return success"
    assert "--no-subdirs" in ret.stdout
    assert "only process files in the top-level directory" in ret.stdout


def test_cli_nested_mixed_recursive_vs_non_recursive(script_runner):
    """Test CLI behavior with nested_mixed folder - recursive vs non-recursive bbox differences"""
    # Test with recursive processing (default)
    ret_recursive = script_runner.run(
        "geoextent", "-b", "--no-progress", "tests/testdata/folders/nested_mixed"
    )
    assert ret_recursive.success, "recursive process should return success"

    # Test with --no-subdirs
    ret_non_recursive = script_runner.run(
        "geoextent",
        "-b",
        "--no-progress",
        "--no-subdirs",
        "tests/testdata/folders/nested_mixed",
    )
    assert ret_non_recursive.success, "non-recursive process should return success"

    import json

    # Parse the JSON outputs
    recursive_result = json.loads(ret_recursive.stdout.strip())
    non_recursive_result = json.loads(ret_non_recursive.stdout.strip())

    # Both should be FeatureCollections with geometry
    assert (
        recursive_result.get("type") == "FeatureCollection"
    ), "Recursive processing should produce a FeatureCollection"
    assert (
        non_recursive_result.get("type") == "FeatureCollection"
    ), "Non-recursive should produce a FeatureCollection"
    assert (
        len(recursive_result["features"]) > 0
    ), "Recursive processing should produce a bbox"
    assert (
        len(non_recursive_result["features"]) > 0
    ), "Non-recursive should still have bbox from top-level file"

    # Extract bounding coordinates from FeatureCollection geometry
    recursive_coords = recursive_result["features"][0]["geometry"]["coordinates"][0]
    non_recursive_coords = non_recursive_result["features"][0]["geometry"][
        "coordinates"
    ][0]

    # Get the x-axis bounds (longitude in GeoJSON [lon, lat] per RFC 7946)
    recursive_min_x = min(coord[0] for coord in recursive_coords)
    recursive_max_x = max(coord[0] for coord in recursive_coords)
    non_recursive_min_x = min(coord[0] for coord in non_recursive_coords)
    non_recursive_max_x = max(coord[0] for coord in non_recursive_coords)

    # Recursive should have larger extent (includes both top-level and subdirectory files)
    assert (
        recursive_max_x > non_recursive_max_x
    ), "Recursive should have larger max longitude"

    # Both should have same minimum (from top-level file)
    assert pytest.approx(recursive_min_x, abs=tolerance) == non_recursive_min_x

    # Verify expected specific values (longitude from GeoJSON [lon, lat] per RFC 7946)
    # Recursive: covers both ausgleichsflaechen_moers.geojson and subdir/muenster_ring_zeit.geojson
    assert pytest.approx(recursive_min_x, abs=tolerance) == 6.59663465544554
    assert pytest.approx(recursive_max_x, abs=tolerance) == 7.647256851196289

    # Non-recursive: covers only ausgleichsflaechen_moers.geojson
    assert pytest.approx(non_recursive_min_x, abs=tolerance) == 6.59663465544554
    assert pytest.approx(non_recursive_max_x, abs=tolerance) == 6.662839251596646


def test_api_bbox_merging_recursive_vs_non_recursive():
    """Test that bbox merging works correctly with and without recursive processing using nested_mixed"""
    # Test with recursive (should merge both top-level and subdirectory file)
    result_recursive = geoextent.fromDirectory(
        "tests/testdata/folders/nested_mixed",
        bbox=True,
        recursive=True,
        show_progress=False,
    )

    # Test without recursive (should only include top-level file)
    result_non_recursive = geoextent.fromDirectory(
        "tests/testdata/folders/nested_mixed",
        bbox=True,
        recursive=False,
        show_progress=False,
    )

    # Both should have bboxes
    assert "bbox" in result_recursive, "Recursive processing should produce a bbox"
    assert (
        "bbox" in result_non_recursive
    ), "Non-recursive should still have bbox from top-level file"

    # Extract bbox coordinates - API returns [minlat, minlon, maxlat, maxlon] (native EPSG:4326 order)
    recursive_bbox = result_recursive["bbox"]
    non_recursive_bbox = result_non_recursive["bbox"]

    # Expected coordinates based on actual file analysis (native EPSG:4326 order):
    # Top-level file (ausgleichsflaechen_moers.geojson): [51.422305272549615, 6.59663465544554, 51.486636388722296, 6.662839251596646]
    # Subdirectory file (muenster_ring_zeit.geojson): [51.94881477206191, 7.6016807556152335, 51.974624029877454, 7.647256851196289]
    # Combined: [51.422305272549615, 6.59663465544554, 51.974624029877454, 7.647256851196289]

    recursive_min_lat, recursive_min_lon, recursive_max_lat, recursive_max_lon = (
        recursive_bbox
    )
    (
        non_recursive_min_lat,
        non_recursive_min_lon,
        non_recursive_max_lat,
        non_recursive_max_lon,
    ) = non_recursive_bbox

    # Verify the recursive extent is larger (includes subdirectory file)
    assert (
        recursive_max_lat > non_recursive_max_lat
    ), "Recursive processing should include larger extent from subdirectory"

    # The min_lat should be the same (both include the top-level file)
    assert pytest.approx(recursive_min_lat, abs=tolerance) == non_recursive_min_lat

    # Specific expected values based on file analysis
    assert pytest.approx(recursive_min_lat, abs=tolerance) == 51.422305272549615
    assert pytest.approx(recursive_max_lat, abs=tolerance) == 51.974624029877454
    assert pytest.approx(non_recursive_min_lat, abs=tolerance) == 51.422305272549615
    assert pytest.approx(non_recursive_max_lat, abs=tolerance) == 51.486636388722296
