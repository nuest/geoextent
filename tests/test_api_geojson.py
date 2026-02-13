from help_functions_test import (
    assert_bbox_result,
    assert_tbox_result,
    assert_bbox_and_tbox_result,
    assert_empty_result,
    assert_no_bbox,
    assert_no_tbox,
    extract_bbox_only,
    extract_tbox_only,
    extract_bbox_and_tbox,
)

# Test data constants
MUENSTER_RING_BBOX = [51.948814, 7.601680, 51.974624, 7.647256]
MUENSTER_RING_TBOX = ["2018-11-14", "2018-11-14"]
ONE_POINT_BBOX = [50.521503, 6.220493, 50.521503, 6.220493]


class TestGeoJSONBboxExtraction:
    """Test spatial extent extraction from GeoJSON files"""

    def test_extract_bbox_multigeometry(self):
        """Test bbox extraction from GeoJSON with multiple geometries"""
        result = extract_bbox_only("tests/testdata/geojson/muenster_ring_zeit.geojson")
        assert_bbox_result(result, MUENSTER_RING_BBOX)

    def test_extract_bbox_single_point(self):
        """Test bbox extraction from GeoJSON with single point"""
        result = extract_bbox_only("tests/testdata/geojson/onePoint.geojson")
        assert_bbox_result(result, ONE_POINT_BBOX)


class TestGeoJSONTboxExtraction:
    """Test temporal extent extraction from GeoJSON files"""

    def test_extract_tbox_only(self):
        """Test tbox extraction without bbox"""
        result = extract_tbox_only("tests/testdata/geojson/muenster_ring_zeit.geojson")
        assert_tbox_result(result, MUENSTER_RING_TBOX)
        assert_no_bbox(result)

    def test_extract_tbox_with_bbox_disabled(self):
        """Test tbox extraction with bbox explicitly disabled"""
        import geoextent.lib.extent as geoextent

        result = geoextent.fromFile(
            "tests/testdata/geojson/muenster_ring_zeit.geojson", bbox=False, tbox=True
        )
        assert_tbox_result(result, MUENSTER_RING_TBOX)
        assert_no_bbox(result)


class TestGeoJSONErrorHandling:
    """Test GeoJSON error cases and invalid data"""

    def test_invalid_coordinates(self):
        """Test handling of GeoJSON with invalid coordinates"""
        result = extract_bbox_only("tests/testdata/geojson/invalid_coordinate.geojson")
        # For invalid coordinates, the result might be None or contain no bbox
        if result is not None:
            assert_no_bbox(result)
        else:
            assert_empty_result(result)

    def test_empty_geojson_file(self):
        """Test handling of empty GeoJSON file"""
        result = extract_bbox_only("tests/testdata/geojson/empty.geojson")
        assert_empty_result(result)
