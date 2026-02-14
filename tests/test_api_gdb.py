import pytest
from help_functions_test import tolerance
import geoextent.lib.extent as geoextent


def test_gdb_extract_bbox():
    result = geoextent.fromFile(
        "tests/testdata/gdb/points_muenster.gdb", bbox=True, tbox=False
    )
    assert "bbox" in result
    assert "crs" in result
    # Expected: [minlat, minlon, maxlat, maxlon] in EPSG:4326 native order
    assert result["bbox"] == pytest.approx(
        [51.9469, 7.6088, 51.9636, 7.6403], abs=tolerance
    )
    assert result["crs"] == "4326"


def test_gdb_extract_only_bbox():
    result = geoextent.fromFile(
        "tests/testdata/gdb/points_muenster.gdb", bbox=True, tbox=False
    )
    assert "bbox" in result
    assert "crs" in result
    assert "tbox" not in result


def test_gdb_extract_time():
    result = geoextent.fromFile(
        "tests/testdata/gdb/points_muenster.gdb", bbox=False, tbox=True
    )
    assert "bbox" not in result
    assert "crs" not in result
    # Points have no temporal attributes
    assert result is None or "tbox" not in result


def test_gdb_format_recognition():
    result = geoextent.fromFile("tests/testdata/gdb/points_muenster.gdb", bbox=True)
    assert result["format"] == "gdb"
    assert result["geoextent_handler"] == "handleVector"


def test_gdb_in_directory():
    """Test that a .gdb inside a directory is treated as a dataset, not traversed."""
    result = geoextent.fromDirectory("tests/testdata/gdb", bbox=True, tbox=False)
    assert result is not None
    assert "bbox" in result
    assert result["bbox"] == pytest.approx(
        [51.9469, 7.6088, 51.9636, 7.6403], abs=tolerance
    )
    assert result["crs"] == "4326"


def test_gdb_fromfile_is_directory():
    """Test that fromFile handles .gdb (which is a directory) correctly."""
    import os

    path = "tests/testdata/gdb/points_muenster.gdb"
    assert os.path.isdir(path)
    result = geoextent.fromFile(path, bbox=True)
    assert result is not None
    assert "bbox" in result
