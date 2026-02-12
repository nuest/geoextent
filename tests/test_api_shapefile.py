from help_functions_test import (
    assert_bbox_result,
    assert_tbox_result,
    assert_no_bbox,
    assert_no_tbox,
    extract_bbox_only,
    extract_tbox_only,
)


class TestShapefileBboxExtraction:
    """Test spatial extent extraction from Shapefile format"""

    def test_extract_bbox_with_crs(self):
        """Test bbox extraction from shapefile with valid CRS"""
        result = extract_bbox_only(
            "tests/testdata/shapefile/gis_osm_buildings_a_free_1.shp"
        )
        expected_bbox = [-167.400123, -89.998844, 166.700078, -60.708069]
        assert_bbox_result(result, expected_bbox)
        assert_no_tbox(result)

    def test_extract_bbox_with_auto_identified_crs(self):
        """Test bbox extraction from shapefile where CRS is auto-identified via EPSG lookup"""
        result = extract_bbox_only(
            "tests/testdata/shapefile/Abgrabungen_Kreis_Kleve_Shape.shp"
        )
        # This shapefile has EPSG:25832 which is auto-identified and transformed to WGS84
        expected_bbox = [
            6.0373054738033725,
            51.36725472296136,
            6.499786759861303,
            51.847920000368205,
        ]
        assert_bbox_result(result, expected_bbox)
        assert_no_tbox(result)


class TestShapefileTboxExtraction:
    """Test temporal extent extraction from Shapefile format"""

    def test_extract_tbox_only(self):
        """Test tbox extraction from shapefile with temporal data"""
        result = extract_tbox_only("tests/testdata/shapefile/ifgi_denkpause.shp")
        expected_tbox = ["2021-01-01", "2021-01-01"]
        assert_tbox_result(result, expected_tbox)
        assert_no_bbox(result)
