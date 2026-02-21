import os
import pytest
from help_functions_test import tolerance
import geoextent.lib.extent as geoextent


def test_zarr_v2_bbox():
    """Extract bounding box from a WGS84 Zarr V2 store."""
    result = geoextent.from_file(
        "tests/testdata/zarr/wgs84_v2.zarr", bbox=True, tbox=False
    )
    assert result is not None
    assert "bbox" in result
    assert "crs" in result
    assert result["crs"] == "4326"
    assert result["bbox"] == pytest.approx([7.0, 51.0, 8.0, 52.0], abs=tolerance)


def test_zarr_v2_projected_bbox():
    """Extract bounding box from a UTM 32N Zarr V2 store (tests CRS transform)."""
    result = geoextent.from_file(
        "tests/testdata/zarr/utm32n_v2.zarr", bbox=True, tbox=False
    )
    assert result is not None
    assert "bbox" in result
    assert "crs" in result
    assert result["crs"] == "4326"
    # Projected CRS transformed to WGS84 — Muenster area
    assert result["bbox"] == pytest.approx(
        [51.8878, 7.2563, 51.9798, 7.3984], abs=tolerance
    )


def test_zarr_v3_bbox():
    """Extract bounding box from a WGS84 Zarr V3 store."""
    result = geoextent.from_file(
        "tests/testdata/zarr/wgs84_v3.zarr", bbox=True, tbox=False
    )
    assert result is not None
    assert "bbox" in result
    assert "crs" in result
    assert result["crs"] == "4326"
    assert result["bbox"] == pytest.approx([7.0, 51.0, 8.0, 52.0], abs=tolerance)


def test_zarr_no_crs():
    """Zarr store without CRS and coords outside WGS84 bounds returns no bbox."""
    result = geoextent.from_file(
        "tests/testdata/zarr/no_crs_v2.zarr", bbox=True, tbox=False
    )
    assert result is None or "bbox" not in result


def test_zarr_format_recognition():
    """Verify format and handler metadata for Zarr files."""
    result = geoextent.from_file("tests/testdata/zarr/wgs84_v2.zarr", bbox=True)
    assert result["format"] == "zarr"
    assert result["geoextent_handler"] == "handle_raster"


def test_zarr_in_directory():
    """Test that .zarr stores inside a directory are treated as datasets, not traversed."""
    result = geoextent.from_directory("tests/testdata/zarr", bbox=True, tbox=False)
    assert result is not None
    assert "bbox" in result
    assert result["crs"] == "4326"


def test_zarr_fromfile_is_directory():
    """Test that from_file accepts .zarr directory paths."""
    path = "tests/testdata/zarr/wgs84_v2.zarr"
    assert os.path.isdir(path)
    result = geoextent.from_file(path, bbox=True)
    assert result is not None
    assert "bbox" in result


def test_zarr_tbox_none():
    """Zarr V2 store without temporal metadata returns no tbox."""
    result = geoextent.from_file(
        "tests/testdata/zarr/wgs84_v2.zarr", bbox=False, tbox=True
    )
    assert result is None or "tbox" not in result
