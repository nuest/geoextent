import zipfile
import os
import pytest
import geoextent.lib.extent as geoextent

tolerance = 1e-3


def create_zip(folder, zipfile_temp):
    """
    Function purpose: create a zip file
    Input: filepath
    Source: https://thispointer.com/python-how-to-create-a-zip-archive-from-multiple-files-or-directory/
    """

    with zipfile.ZipFile(zipfile_temp, "w") as zipObj:
        # Iterate over all the files in directory
        for folderName, sub_folders, filenames in os.walk(folder):
            for filename in filenames:
                # create complete filepath of file in directory
                file_root = os.path.abspath(folderName)
                filePath = os.path.join(file_root, filename)
                zipObj.write(filePath)


def parse_coordinates(result):
    """
    Function purpose: parse coordinates from console result into a list
    Input: string (now expects GeoJSON FeatureCollection format)
    Output: list of [minx, miny, maxx, maxy]
    """
    import json

    # Try to parse as JSON (new FeatureCollection format)
    try:
        parsed = json.loads(result)
        if isinstance(parsed, dict) and parsed.get("type") == "FeatureCollection":
            # Extract coordinates from FeatureCollection geometry
            features = parsed.get("features", [])
            if len(features) > 0:
                geometry = features[0].get("geometry", {})
                if geometry.get("type") == "Polygon":
                    coords = geometry.get("coordinates", [[]])[0]  # Get outer ring

                    # Convert polygon coordinates to bbox [minx, miny, maxx, maxy]
                    if (
                        len(coords) >= 4
                    ):  # Should have at least 4 points for a closed polygon
                        x_coords = [point[0] for point in coords]
                        y_coords = [point[1] for point in coords]
                        return [
                            min(x_coords),
                            min(y_coords),
                            max(x_coords),
                            max(y_coords),
                        ]
    except json.JSONDecodeError:
        pass

    # Fallback: try old format
    try:
        bboxStr = result[result.find("[") + 1 : result.find("]")]
        bboxList = [float(i) for i in bboxStr.split(",")]
        return bboxList
    except (ValueError, AttributeError):
        pass

    # If all parsing fails, return empty list
    return []


def test_generate_geojsonio_url():
    """Test the generate_geojsonio_url helper function"""
    import geoextent.lib.helpfunctions as hf
    import json

    # Test with regular bounding box
    extent_output = {"bbox": [-74.0059, 40.7128, -73.9352, 40.7589], "crs": "4326"}

    url = hf.generate_geojsonio_url(extent_output)
    assert url is not None, "should generate URL for valid bbox"
    assert "geojson.io" in url, "URL should point to geojson.io"
    assert "http" in url, "URL should be valid HTTP URL"

    # Test with convex hull
    convex_hull_output = {
        "bbox": [
            [-74.0059, 40.7128],
            [-73.9352, 40.7128],
            [-73.9352, 40.7589],
            [-74.0059, 40.7589],
            [-74.0059, 40.7128],
        ],
        "convex_hull": True,
        "crs": "4326",
    }

    url = hf.generate_geojsonio_url(convex_hull_output)
    assert url is not None, "should generate URL for convex hull"
    assert "geojson.io" in url, "URL should point to geojson.io"

    # Test with no bbox (should return None)
    no_bbox_output = {"tbox": ["2023-01-01", "2023-12-31"]}

    url = hf.generate_geojsonio_url(no_bbox_output)
    assert url is None, "should return None when no bbox present"

    # Test with empty input
    url = hf.generate_geojsonio_url(None)
    assert url is None, "should return None for empty input"


def test_geojsonio_url_format_independence():
    """Test that geojsonio URL generation works regardless of output format"""
    import geoextent.lib.helpfunctions as hf

    # Create extent output with regular bbox
    extent_output = {"bbox": [-74.0059, 40.7128, -73.9352, 40.7589], "crs": "4326"}

    # Generate URL - should work regardless of output format
    url = hf.generate_geojsonio_url(extent_output)
    assert url is not None, "should generate URL"
    assert "geojson.io" in url, "URL should point to geojson.io"

    # The URL should contain properly formatted GeoJSON regardless of input format
    # Decode the URL to check the data parameter contains valid GeoJSON
    import urllib.parse

    parsed_url = urllib.parse.urlparse(url)
    fragment = parsed_url.fragment

    # Should contain data parameter with GeoJSON
    assert "data=" in fragment, "URL should contain data parameter"


# Enhanced assertion helpers to reduce repetition
def assert_bbox_result(result, expected_bbox, expected_crs="4326"):
    """Assert that a result contains valid bbox data"""
    assert result is not None, "Result should not be None"
    assert "bbox" in result, "Result should contain bbox"
    assert "crs" in result, "Result should contain crs"
    assert result["bbox"] == pytest.approx(
        expected_bbox, abs=tolerance
    ), f"Expected bbox {expected_bbox}, got {result['bbox']}"
    assert (
        result["crs"] == expected_crs
    ), f"Expected CRS {expected_crs}, got {result['crs']}"


def assert_tbox_result(result, expected_tbox):
    """Assert that a result contains valid tbox data"""
    assert result is not None, "Result should not be None"
    assert "tbox" in result, "Result should contain tbox"
    assert (
        result["tbox"] == expected_tbox
    ), f"Expected tbox {expected_tbox}, got {result['tbox']}"


def assert_no_bbox(result):
    """Assert that a result does not contain bbox data"""
    if result is not None:
        assert "bbox" not in result, "Result should not contain bbox"
        assert "crs" not in result, "Result should not contain crs"


def assert_no_tbox(result):
    """Assert that a result does not contain tbox data"""
    if result is not None:
        assert "tbox" not in result, "Result should not contain tbox"


def assert_bbox_and_tbox_result(
    result, expected_bbox, expected_tbox, expected_crs="4326"
):
    """Assert that a result contains both valid bbox and tbox data"""
    assert_bbox_result(result, expected_bbox, expected_crs)
    assert_tbox_result(result, expected_tbox)


def assert_empty_result(result):
    """Assert that a result is None (empty/invalid file)"""
    assert result is None, "Result should be None for empty/invalid files"


def extract_bbox_only(filepath):
    """Extract only bbox from a file"""
    return geoextent.fromFile(filepath, bbox=True, tbox=False)


def extract_tbox_only(filepath):
    """Extract only tbox from a file"""
    return geoextent.fromFile(filepath, bbox=False, tbox=True)


def extract_bbox_and_tbox(filepath):
    """Extract both bbox and tbox from a file"""
    return geoextent.fromFile(filepath, bbox=True, tbox=True)
