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
    extent_output = {"bbox": [40.7128, -74.0059, 40.7589, -73.9352], "crs": "4326"}

    url = hf.generate_geojsonio_url(extent_output)
    assert url is not None, "should generate URL for valid bbox"
    assert "geojson.io" in url, "URL should point to geojson.io"
    assert "http" in url, "URL should be valid HTTP URL"

    # Test with convex hull
    convex_hull_output = {
        "bbox": [
            [40.7128, -74.0059],
            [40.7128, -73.9352],
            [40.7589, -73.9352],
            [40.7589, -74.0059],
            [40.7128, -74.0059],
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
    extent_output = {"bbox": [40.7128, -74.0059, 40.7589, -73.9352], "crs": "4326"}

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


def test_geojsonio_url_includes_inputs():
    """Test that geojsonio URL includes original input identifiers in Feature properties"""
    import geoextent.lib.helpfunctions as hf
    import json
    import urllib.parse

    extent_output = {"bbox": [40.7128, -74.0059, 40.7589, -73.9352], "crs": "4326"}

    # Single input — should be a one-element list
    url = hf.generate_geojsonio_url(
        extent_output, inputs=["tests/testdata/geojson/muenster_ring_zeit.geojson"]
    )
    assert url is not None
    fragment = urllib.parse.urlparse(url).fragment
    geojson_str = urllib.parse.unquote(fragment.split("data=data:application/json,")[1])
    geojson_data = json.loads(geojson_str)
    props = geojson_data["features"][0]["properties"]
    assert "inputs" in props, "Feature properties should contain 'inputs'"
    assert props["inputs"] == ["tests/testdata/geojson/muenster_ring_zeit.geojson"]

    # Multiple inputs
    url = hf.generate_geojsonio_url(
        extent_output,
        inputs=["10.5281/zenodo.820562", "https://doi.org/10.1594/PANGAEA.734969"],
    )
    assert url is not None
    fragment = urllib.parse.urlparse(url).fragment
    geojson_str = urllib.parse.unquote(fragment.split("data=data:application/json,")[1])
    geojson_data = json.loads(geojson_str)
    props = geojson_data["features"][0]["properties"]
    assert props["inputs"] == [
        "10.5281/zenodo.820562",
        "https://doi.org/10.1594/PANGAEA.734969",
    ]

    # No inputs — should not have 'inputs' key
    url = hf.generate_geojsonio_url(extent_output)
    assert url is not None
    fragment = urllib.parse.urlparse(url).fragment
    geojson_str = urllib.parse.unquote(fragment.split("data=data:application/json,")[1])
    geojson_data = json.loads(geojson_str)
    props = geojson_data["features"][0]["properties"]
    assert "inputs" not in props, "No 'inputs' when inputs parameter is not provided"


def test_generate_geojsonio_url_raise_on_error():
    """When raise_on_error=True, a make_url failure raises GeojsonioUrlError
    so the CLI can distinguish "service failed" from "no spatial extent"."""
    import geoextent.lib.helpfunctions as hf
    from unittest.mock import patch

    extent_output = {"bbox": [40.7128, -74.0059, 40.7589, -73.9352], "crs": "4326"}

    # Simulate the 401 returned by the anonymous-gist fallback for big GeoJSON.
    fake_err = Exception("401 Requires authentication")

    # Default mode: swallow + return None (preserves legacy callers).
    with patch("geoextent.lib.helpfunctions.geojsonio.make_url", side_effect=fake_err):
        assert hf.generate_geojsonio_url(extent_output) is None

    # Opt-in mode: re-raise as GeojsonioUrlError carrying the underlying text.
    with patch("geoextent.lib.helpfunctions.geojsonio.make_url", side_effect=fake_err):
        with pytest.raises(hf.GeojsonioUrlError) as exc_info:
            hf.generate_geojsonio_url(extent_output, raise_on_error=True)
        assert "401" in str(exc_info.value)

    # No-extent case must always return None — never raise — regardless of flag.
    assert hf.generate_geojsonio_url({}, raise_on_error=True) is None
    assert hf.generate_geojsonio_url(None, raise_on_error=True) is None


def test_generate_geojsonio_url_gist_fallback_message(caplog):
    """When the payload exceeds the geojsonio library's ``MAX_URL_LEN``
    (150 KB of GeoJSON content), ``geojsonio.make_url`` routes through
    the anonymous GitHub Gist fallback, which now returns 401 because
    gist creation requires auth. geojson.io itself does not document a
    payload-size limit — this threshold is purely the wrapper library's
    choice. We must:

    1. Detect the size, so the warning blames the *gist* endpoint
       (not just "geojsonio.make_url"), and
    2. Hint at ``--convex-hull`` so the user knows how to shrink the
       payload.

    Build the oversize extent on the fly — a real 150 KB+ fixture file
    would be wasteful to commit.
    """
    import geoextent.lib.helpfunctions as hf
    import logging
    from unittest.mock import patch

    # Convex hull format = list of [lon, lat] pairs. Build a polygon ring
    # large enough to clear the 150 KB threshold by a comfortable margin.
    # Each "[x.xxxxxxx, y.yyyyyyy], " is ~24 bytes encoded, so 8000
    # vertices ≈ 190 KB.
    n = 8000
    ring = [[round(2.0 + i * 1e-6, 7), round(48.0 + i * 1e-6, 7)] for i in range(n)]
    ring.append(ring[0])  # close the ring
    extent_output = {"bbox": ring, "convex_hull": True, "crs": "4326"}

    fake_err = Exception("401 Requires authentication")

    with caplog.at_level(logging.WARNING, logger="geoextent"):
        with patch(
            "geoextent.lib.helpfunctions.geojsonio.make_url", side_effect=fake_err
        ):
            with pytest.raises(hf.GeojsonioUrlError) as exc_info:
                hf.generate_geojsonio_url(extent_output, raise_on_error=True)

    err_text = str(exc_info.value)
    # 1. The error must identify the gist endpoint specifically, not just
    #    "geojsonio.make_url" — so users can debug the auth wall.
    assert "Gist" in err_text, f"expected Gist endpoint in message, got: {err_text!r}"
    assert "401" in err_text
    # 2. Payload size must be reported (and large) so users see why.
    assert "bytes" in err_text
    # 3. The hint must point at --convex-hull as the user-actionable fix.
    assert (
        "--convex-hull" in err_text
    ), f"expected --convex-hull hint in message for oversize payload, got: {err_text!r}"
    # 4. The library's documented threshold should be cited.
    assert "150 KB" in err_text, (
        "the message should cite the geojsonio threshold so users can "
        "decide whether shrinking is worth it"
    )

    # The warning log line should also carry these breadcrumbs.
    warning_text = "\n".join(r.getMessage() for r in caplog.records)
    assert "Gist" in warning_text
    assert "--convex-hull" in warning_text
    assert "150 KB" in warning_text


def test_geojsonio_url_fragment_limit_matches_library():
    """The threshold used for the message switch must track geojsonio's
    own ``MAX_URL_LEN`` so we don't drift if the library tweaks it."""
    import geoextent.lib.helpfunctions as hf
    from geojsonio.geojsonio import MAX_URL_LEN as upstream

    assert hf._GEOJSONIO_URL_FRAGMENT_LIMIT == int(upstream), (
        f"helpfunctions threshold {hf._GEOJSONIO_URL_FRAGMENT_LIMIT} drifted "
        f"from geojsonio.MAX_URL_LEN {upstream}"
    )


def test_generate_geojsonio_url_small_payload_no_gist_hint():
    """Small payloads don't go through the gist fallback, so the message
    must NOT pretend the gist is at fault or suggest --convex-hull."""
    import geoextent.lib.helpfunctions as hf
    from unittest.mock import patch

    extent_output = {"bbox": [40.7128, -74.0059, 40.7589, -73.9352], "crs": "4326"}
    fake_err = Exception("connection reset")

    with patch("geoextent.lib.helpfunctions.geojsonio.make_url", side_effect=fake_err):
        with pytest.raises(hf.GeojsonioUrlError) as exc_info:
            hf.generate_geojsonio_url(extent_output, raise_on_error=True)

    err_text = str(exc_info.value)
    assert "connection reset" in err_text
    assert "Gist" not in err_text, "small payloads do not hit the gist fallback"
    assert (
        "--convex-hull" not in err_text
    ), "do not nag about geometry size when the error is unrelated to size"


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
    return geoextent.from_file(filepath, bbox=True, tbox=False)


def extract_tbox_only(filepath):
    """Extract only tbox from a file"""
    return geoextent.from_file(filepath, bbox=False, tbox=True)


def extract_bbox_and_tbox(filepath):
    """Extract both bbox and tbox from a file"""
    return geoextent.from_file(filepath, bbox=True, tbox=True)
