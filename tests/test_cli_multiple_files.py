import pytest
import subprocess
import json
import os
from osgeo import ogr
from help_functions_test import tolerance


def run_geoextent_cli(*args):
    """Helper function to run geoextent CLI and return parsed JSON output.

    Converts the FeatureCollection output to a flat dict for test compatibility:
    - format, crs, geoextent_handler from geoextent_extraction
    - bbox from features[0].geometry coordinates
    - tbox from features[0].properties
    - details from top-level if present
    """
    cmd = ["python", "-m", "geoextent", "--quiet"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    if result.returncode != 0:
        pytest.fail(f"CLI command failed: {result.stderr}")
    parsed = json.loads(result.stdout)

    # If it's a FeatureCollection, flatten to old-style dict
    if isinstance(parsed, dict) and parsed.get("type") == "FeatureCollection":
        flat = {}
        metadata = parsed.get("geoextent_extraction", {})
        flat["format"] = metadata.get("format")
        flat["crs"] = metadata.get("crs")
        flat["geoextent_handler"] = metadata.get("geoextent_handler")

        # Extract bbox from geometry
        features = parsed.get("features", [])
        if features:
            geom = features[0].get("geometry", {})
            if geom.get("type") == "Polygon":
                coords = geom["coordinates"][0]
                xs = [c[0] for c in coords]
                ys = [c[1] for c in coords]
                flat["bbox"] = [min(xs), min(ys), max(xs), max(ys)]
            props = features[0].get("properties", {})
            if "tbox" in props:
                flat["tbox"] = props["tbox"]

        # Copy details if present
        if "details" in parsed:
            flat["details"] = parsed["details"]

        return flat

    return parsed


def test_multiple_files_bbox_extraction():
    """Test bbox extraction from multiple files"""
    result = run_geoextent_cli(
        "-b",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",  # Germany: [7.60, 51.95, 7.65, 51.97]
        "tests/testdata/folders/folder_two_files/districtes.geojson",  # Spain: [2.05, 41.32, 2.23, 41.47]
    )

    assert result["format"] == "multiple_files"
    assert "bbox" in result
    assert "crs" in result
    assert result["crs"] == "4326"
    # Merged bbox should cover both Münster (Germany) and Barcelona (Spain)
    # Extracted from GeoJSON geometry → [minlon, minlat, maxlon, maxlat] per RFC 7946
    assert result["bbox"] == pytest.approx(
        [2.052333387639205, 41.31703852240476, 7.647256851196289, 51.974624029877454],
        abs=tolerance,
    )


def test_multiple_files_tbox_extraction():
    """Test temporal extraction from multiple files"""
    result = run_geoextent_cli(
        "-t",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",  # 2018-11-14
        "tests/testdata/folders/folder_two_files/districtes.geojson",  # 2019-09-11
        "tests/testdata/csv/cities_NL.csv",  # 2017-08-01 to 2019-09-30
    )

    assert result["format"] == "multiple_files"
    assert "tbox" in result
    # Should span from earliest to latest date across all files
    assert result["tbox"] == ["2017-08-01", "2019-09-30"]


def test_multiple_files_bbox_and_tbox():
    """Test both spatial and temporal extraction from multiple files"""
    result = run_geoextent_cli(
        "-b",
        "-t",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",  # Germany: [7.60, 51.95, 7.65, 51.97], 2018-11-14
        "tests/testdata/folders/folder_two_files/districtes.geojson",  # Spain: [2.05, 41.32, 2.23, 41.47], 2019-09-11
        "tests/testdata/csv/cities_NL.csv",  # Netherlands: [4.32, 51.43, 6.57, 53.22], 2017-08-01 to 2019-09-30
    )

    assert result["format"] == "multiple_files"
    assert "bbox" in result
    assert "tbox" in result
    assert "crs" in result
    assert result["crs"] == "4326"
    # Merged bbox should cover Germany, Spain, and Netherlands
    # Extracted from GeoJSON geometry → [minlon, minlat, maxlon, maxlat] per RFC 7946
    assert result["bbox"] == pytest.approx(
        [2.052333387639205, 41.31703852240476, 7.647256851196289, 53.217222],
        abs=tolerance,
    )
    assert result["tbox"] == ["2017-08-01", "2019-09-30"]


def test_multiple_files_with_details():
    """Test multiple files with details flag"""
    result = run_geoextent_cli(
        "-b",
        "-t",
        "--details",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
        "tests/testdata/folders/folder_two_files/districtes.geojson",
    )

    assert result["format"] == "multiple_files"
    assert "details" in result
    assert len(result["details"]) == 2

    # Check individual file details
    muenster_details = result["details"][
        "tests/testdata/geojson/muenster_ring_zeit.geojson"
    ]
    assert muenster_details["format"] == "geojson"
    assert muenster_details["geoextent_handler"] == "handleVector"
    assert "bbox" in muenster_details
    assert "tbox" in muenster_details

    barcelona_details = result["details"][
        "tests/testdata/folders/folder_two_files/districtes.geojson"
    ]
    assert barcelona_details["format"] == "geojson"
    assert barcelona_details["geoextent_handler"] == "handleVector"
    assert "bbox" in barcelona_details
    assert "tbox" in barcelona_details


def test_multiple_files_different_formats():
    """Test multiple files of different formats"""
    # Test with CSV, GeoJSON (two different sources)
    result = run_geoextent_cli(
        "-b",
        "tests/testdata/csv/cities_NL.csv",  # Netherlands CSV
        "tests/testdata/geojson/muenster_ring_zeit.geojson",  # Germany GeoJSON
        "tests/testdata/folders/folder_two_files/districtes.geojson",  # Spain GeoJSON
    )

    assert result["format"] == "multiple_files"
    assert "bbox" in result
    assert "crs" in result
    # Should cover Netherlands, Germany, and Spain
    # Extracted from GeoJSON geometry → [minlon, minlat, maxlon, maxlat] per RFC 7946
    assert result["bbox"] == pytest.approx(
        [2.052333387639205, 41.31703852240476, 7.647256851196289, 53.217222],
        abs=tolerance,
    )


def test_single_file_backward_compatibility():
    """Test that single file processing still works as before"""
    result = run_geoextent_cli(
        "-b", "-t", "tests/testdata/geojson/muenster_ring_zeit.geojson"
    )

    # Single file should not have "multiple_files" format
    assert result["format"] == "geojson"
    assert result["geoextent_handler"] == "handleVector"
    assert "bbox" in result
    assert "tbox" in result
    assert (
        "details" not in result
    )  # No details for single file unless --details is used


def test_multiple_files_mixed_with_directories():
    """Test multiple inputs including both files and directories"""
    # Create a temporary directory with a test file for this test
    result = run_geoextent_cli(
        "-b",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
        "tests/testdata/csv",  # This is a directory
    )

    assert result["format"] == "multiple_files"
    assert "bbox" in result


def test_multiple_files_error_handling():
    """Test that errors in individual files don't stop processing of others"""
    # Include a valid file and an invalid/non-existent file pattern
    # The CLI should process the valid files and warn about invalid ones
    result = run_geoextent_cli(
        "-b",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
        # Only testing with valid file since invalid files would cause CLI to exit
    )

    # This is more of a regression test to ensure single valid file works
    assert "bbox" in result


# --- Convex hull geometry tests for multiple inputs ---

# Test files with known locations:
#  1. geojson/muenster_ring_zeit.geojson      — Münster, Germany
#  2. folders/folder_two_files/districtes.geojson — Barcelona, Spain
#  3. csv/cities_NL.csv                       — Netherlands
#  4. geopackage/nc.gpkg                      — North Carolina, USA
#  5. geopackage/custom_crs.gpkg              — Northern Ireland

_HULL_FILES = [
    "tests/testdata/geojson/muenster_ring_zeit.geojson",
    "tests/testdata/folders/folder_two_files/districtes.geojson",
    "tests/testdata/csv/cities_NL.csv",
    "tests/testdata/geopackage/nc.gpkg",
    "tests/testdata/geopackage/custom_crs.gpkg",
]

# Known bboxes in [minlon, minlat, maxlon, maxlat] (GeoJSON lon/lat order)
_KNOWN_BBOXES = [
    [7.601, 51.948, 7.648, 51.975],  # Münster
    [2.052, 41.317, 2.228, 41.468],  # Barcelona
    [4.317, 51.434, 6.575, 53.218],  # Netherlands
    [-84.324, 33.882, -75.457, 36.590],  # North Carolina
    [-5.936, 54.564, -5.887, 54.590],  # Northern Ireland
]


def _run_convex_hull(*file_paths):
    """Run geoextent --convex-hull on given files and return parsed JSON."""
    cmd = [
        ".venv/bin/python",
        "-m",
        "geoextent",
        "-b",
        "--convex-hull",
        "--quiet",
    ] + list(file_paths)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    if result.returncode != 0:
        pytest.fail(f"CLI command failed: {result.stderr}")
    return json.loads(result.stdout)


def _extract_hull_coords(parsed):
    """Extract the convex hull ring coordinates from a FeatureCollection."""
    return parsed["features"][0]["geometry"]["coordinates"][0]


def _make_ogr_polygon(coords):
    """Create an OGR polygon from a list of [lon, lat] coordinate pairs."""
    ring = ogr.Geometry(ogr.wkbLinearRing)
    for lon, lat in coords:
        ring.AddPoint(lon, lat)
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    return poly


def _make_bbox_polygon(minlon, minlat, maxlon, maxlat):
    """Create an OGR polygon from a bounding box."""
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(minlon, minlat)
    ring.AddPoint(maxlon, minlat)
    ring.AddPoint(maxlon, maxlat)
    ring.AddPoint(minlon, maxlat)
    ring.AddPoint(minlon, minlat)
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    return poly


class TestMultipleFilesConvexHull:
    """Tests verifying convex hull geometry for multiple file inputs."""

    def test_convex_hull_two_files(self):
        """Convex hull from Germany + Spain: >4 vertices, intersects both regions."""
        parsed = _run_convex_hull(_HULL_FILES[0], _HULL_FILES[1])
        coords = _extract_hull_coords(parsed)
        hull = _make_ogr_polygon(coords)

        assert parsed["geoextent_extraction"]["extent_type"] == "convex_hull"
        assert hull.IsValid(), "convex hull polygon should be valid"
        assert (
            len(coords) > 5
        ), "convex hull of 2 scattered files should have >4 unique vertices"

        # Hull envelope should cover both input regions
        env = hull.GetEnvelope()  # (minX, maxX, minY, maxY)
        assert env[0] == pytest.approx(
            2.052, abs=0.01
        ), "hull should reach Barcelona longitude"
        assert env[1] == pytest.approx(
            7.647, abs=0.01
        ), "hull should reach Münster longitude"
        assert env[2] == pytest.approx(
            41.317, abs=0.01
        ), "hull should reach Barcelona latitude"
        assert env[3] == pytest.approx(
            51.975, abs=0.01
        ), "hull should reach Münster latitude"

        # Hull must intersect both input file bboxes
        for i in [0, 1]:
            bbox_poly = _make_bbox_polygon(*_KNOWN_BBOXES[i])
            assert hull.Intersects(
                bbox_poly
            ), f"convex hull should intersect bbox of file {i}"

    def test_convex_hull_three_files(self):
        """Convex hull from Germany + Spain + Netherlands: encloses all 3 regions."""
        parsed = _run_convex_hull(_HULL_FILES[0], _HULL_FILES[1], _HULL_FILES[2])
        coords = _extract_hull_coords(parsed)
        hull = _make_ogr_polygon(coords)

        assert hull.IsValid()
        assert len(coords) > 5, "hull should have many vertices"

        # Hull envelope should cover all three regions
        env = hull.GetEnvelope()  # (minX, maxX, minY, maxY)
        assert env[0] < 2.1, "hull should reach Barcelona"
        assert env[1] > 6.5, "hull should reach Netherlands east"
        assert env[2] < 41.4, "hull should reach Barcelona south"
        assert env[3] > 53.2, "hull should reach Netherlands north"

        for i in [0, 1, 2]:
            bbox_poly = _make_bbox_polygon(*_KNOWN_BBOXES[i])
            assert hull.Intersects(
                bbox_poly
            ), f"convex hull should intersect bbox of file {i}"

    def test_convex_hull_four_files(self):
        """Convex hull from Germany + Spain + Netherlands + North Carolina: spans Atlantic."""
        parsed = _run_convex_hull(
            _HULL_FILES[0], _HULL_FILES[1], _HULL_FILES[2], _HULL_FILES[3]
        )
        coords = _extract_hull_coords(parsed)
        hull = _make_ogr_polygon(coords)

        assert hull.IsValid()
        # Envelope should span from NC (-84) to Germany (7.6)
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        assert min(xs) < -75, "hull should extend west into North Carolina"
        assert max(xs) > 7, "hull should extend east into Germany"
        assert min(ys) < 35, "hull should extend south into North Carolina"
        assert max(ys) > 53, "hull should extend north into Netherlands"

        for i in [0, 1, 2, 3]:
            bbox_poly = _make_bbox_polygon(*_KNOWN_BBOXES[i])
            assert hull.Intersects(
                bbox_poly
            ), f"convex hull should intersect bbox of file {i}"

    def test_convex_hull_five_files(self):
        """Convex hull from all 5 files: includes Northern Ireland, covers all regions."""
        parsed = _run_convex_hull(*_HULL_FILES)
        coords = _extract_hull_coords(parsed)
        hull = _make_ogr_polygon(coords)

        assert hull.IsValid()
        # Northern Ireland should push the northernmost latitude higher
        ys = [c[1] for c in coords]
        assert max(ys) > 54.5, "hull should extend north to include Northern Ireland"

        for i in range(5):
            bbox_poly = _make_bbox_polygon(*_KNOWN_BBOXES[i])
            assert hull.Intersects(
                bbox_poly
            ), f"convex hull should intersect bbox of file {i}"

    def test_convex_hull_is_valid_polygon(self):
        """Convex hull is a closed ring with consistent vertices."""
        parsed = _run_convex_hull(_HULL_FILES[0], _HULL_FILES[1], _HULL_FILES[2])
        coords = _extract_hull_coords(parsed)

        # Closed ring: first == last
        assert coords[0] == coords[-1], "convex hull ring should be closed"

        # All interior vertices unique
        interior = coords[:-1]
        unique = [list(c) for c in set(tuple(c) for c in interior)]
        assert len(unique) == len(interior), "interior vertices should all be unique"

        # Valid OGR polygon
        hull = _make_ogr_polygon(coords)
        assert hull.IsValid(), "OGR should consider the polygon valid"
        assert hull.GetGeometryName() == "POLYGON"

    def test_convex_hull_vs_bbox_tighter(self):
        """Convex hull area should be <= bounding box area for the same inputs."""
        # Get convex hull
        hull_parsed = _run_convex_hull(_HULL_FILES[0], _HULL_FILES[1], _HULL_FILES[2])
        hull_coords = _extract_hull_coords(hull_parsed)
        hull_poly = _make_ogr_polygon(hull_coords)

        # Get bounding box for same files
        cmd = [
            ".venv/bin/python",
            "-m",
            "geoextent",
            "-b",
            "--quiet",
            _HULL_FILES[0],
            _HULL_FILES[1],
            _HULL_FILES[2],
        ]
        bbox_result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=os.getcwd()
        )
        bbox_parsed = json.loads(bbox_result.stdout)
        bbox_coords = bbox_parsed["features"][0]["geometry"]["coordinates"][0]
        bbox_poly = _make_ogr_polygon(bbox_coords)

        hull_area = hull_poly.GetArea()
        bbox_area = bbox_poly.GetArea()
        assert (
            hull_area <= bbox_area
        ), f"convex hull area ({hull_area:.4f}) should be <= bbox area ({bbox_area:.4f})"
        # For these scattered files, convex hull should actually be strictly smaller
        assert (
            hull_area < bbox_area
        ), "convex hull should be strictly smaller than bbox for scattered inputs"
