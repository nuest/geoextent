import pytest
from help_functions_test import tolerance
import geoextent.lib.extent as geoextent


def test_shapefile_with_crs_extract_bbox():
    result = geoextent.fromFile(
        "tests/testdata/shapefile/gis_osm_buildings_a_free_1.shp", bbox=True, tbox=False
    )
    assert "temporal_extent" not in result
    assert result["bbox"] == pytest.approx(
        [-167.400123, -89.998844, 166.700078, -60.708069], abs=tolerance
    )
    assert result["crs"] == "4326"


def test_shapefile_without_crs_extract_bbox():
    result = geoextent.fromFile(
        "tests/testdata/shapefile/Abgrabungen_Kreis_Kleve_Shape.shp",
        bbox=True,
        tbox=False,
    )
    assert "tbox" not in result
    assert "bbox" not in result
    assert "crs" not in result


def test_shapefile_extract_bbox_with_crs():
    result = geoextent.fromFile(
        "tests/testdata/shapefile/gis_osm_buildings_a_free_1.shp", bbox=True, tbox=False
    )
    assert "temporal_extent" not in result
    assert result["bbox"] == pytest.approx(
        [-167.400123, -89.998844, 166.700078, -60.708069], abs=tolerance
    )
    assert result["crs"] == "4326"


def test_shapefile_extract_time():
    result = geoextent.fromFile(
        "tests/testdata/shapefile/ifgi_denkpause.shp", bbox=False, tbox=True
    )
    assert "bbox" not in result
    assert "crs" not in result
    assert "tbox" in result
    assert result["tbox"] == ["2021-01-01", "2021-01-01"]


def test_shapefile_precise_extent_validation_gis_osm_buildings():
    """Test with manually verified precise extent values for gis_osm_buildings_a_free_1.shp"""
    result = geoextent.fromFile(
        "tests/testdata/shapefile/gis_osm_buildings_a_free_1.shp", bbox=True, tbox=True
    )
    # Reference values extracted on 2025-09-23 and manually verified
    # This dataset covers a large geographic area (global OSM buildings)
    expected_bbox = [-167.4001236, -89.9988441, 166.7000786, -60.7080691]

    assert "bbox" in result
    assert "crs" in result
    assert result["crs"] == "4326"
    assert result["bbox"] == pytest.approx(expected_bbox, abs=1e-6)
    # This shapefile has no temporal data
    assert "tbox" not in result


def test_shapefile_precise_extent_validation_ifgi_denkpause():
    """Test with manually verified precise extent values for ifgi_denkpause.shp"""
    result = geoextent.fromFile(
        "tests/testdata/shapefile/ifgi_denkpause.shp", bbox=True, tbox=True
    )
    # Reference values extracted on 2025-09-23 and manually verified
    # This is a small area around IFGI in Münster, Germany
    expected_bbox = [7.594978277801928, 51.96852473231792, 7.5957650477781415, 51.969118924937405]
    expected_tbox = ["2021-01-01", "2021-01-01"]

    assert "bbox" in result
    assert "tbox" in result
    assert "crs" in result
    assert result["crs"] == "4326"
    assert result["bbox"] == pytest.approx(expected_bbox, abs=1e-6)
    assert result["tbox"] == expected_tbox
