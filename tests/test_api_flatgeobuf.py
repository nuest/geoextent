import pytest
from help_functions_test import tolerance
import geoextent.lib.extent as geoextent


def test_flatgeobuf_extract_bbox():
    result = geoextent.fromFile(
        "tests/testdata/flatgeobuf/countries.fgb", bbox=True, tbox=False
    )
    assert "bbox" in result
    assert "crs" in result
    assert result["bbox"] == pytest.approx(
        [-85.609038, -180.0, 83.645130, 180.0], abs=tolerance
    )
    assert result["crs"] == "4326"


def test_flatgeobuf_extract_only_bbox():
    result = geoextent.fromFile(
        "tests/testdata/flatgeobuf/countries.fgb", bbox=True, tbox=False
    )
    assert "bbox" in result
    assert "crs" in result
    assert "tbox" not in result


def test_flatgeobuf_extract_time():
    result = geoextent.fromFile(
        "tests/testdata/flatgeobuf/countries.fgb", bbox=False, tbox=True
    )
    assert "bbox" not in result
    assert "crs" not in result
    # Countries file has temporal attributes that should now be extracted
    assert "tbox" in result
    assert result["tbox"] == ["2023-03-23", "2025-09-21"]


def test_flatgeobuf_extract_both():
    result = geoextent.fromFile(
        "tests/testdata/flatgeobuf/countries.fgb", bbox=True, tbox=True
    )
    assert "bbox" in result
    assert "crs" in result
    assert result["bbox"] == pytest.approx(
        [-85.609038, -180.0, 83.645130, 180.0], abs=tolerance
    )
    assert result["crs"] == "4326"
    # Countries file now has extractable temporal attributes
    assert "tbox" in result
    assert result["tbox"] == ["2023-03-23", "2025-09-21"]


def test_flatgeobuf_format_recognition():
    result = geoextent.fromFile(
        "tests/testdata/flatgeobuf/countries.fgb", bbox=True, tbox=True
    )
    assert result["format"] == "fgb"
    assert result["geoextent_handler"] == "handleVector"
