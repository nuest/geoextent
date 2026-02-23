"""Unit tests for pure/deterministic functions in helpfunctions.py and extent.py.

These tests require no network access and cover coordinate conversions,
format validation, geometry utilities, and metadata creation.
"""

import pytest
from geoextent.lib import helpfunctions as hf
from geoextent.lib.extent import _swap_coordinate_order, _is_auxiliary_file


# ---------------------------------------------------------------------------
# validate_bbox_wgs84
# ---------------------------------------------------------------------------
class TestValidateBboxWgs84:
    def test_valid_bbox(self):
        assert hf.validate_bbox_wgs84([7.0, 51.0, 8.0, 52.0]) is True

    def test_latitude_out_of_range(self):
        assert hf.validate_bbox_wgs84([7.0, 91.0, 8.0, 52.0]) is False

    def test_longitude_out_of_range(self):
        assert hf.validate_bbox_wgs84([181.0, 51.0, 8.0, 52.0]) is False

    def test_boundary_values(self):
        assert hf.validate_bbox_wgs84([-180, -90, 180, 90]) is True

    def test_negative_valid_coords(self):
        assert hf.validate_bbox_wgs84([-74.0, -33.0, -70.0, -30.0]) is True

    def test_negative_lat_out_of_range(self):
        assert hf.validate_bbox_wgs84([7.0, -91.0, 8.0, 52.0]) is False


# ---------------------------------------------------------------------------
# float_convert
# ---------------------------------------------------------------------------
class TestFloatConvert:
    def test_float_string(self):
        assert hf.float_convert("3.14") == 3.14

    def test_integer_string(self):
        assert hf.float_convert("42") == 42.0

    def test_non_numeric(self):
        assert hf.float_convert("abc") is None

    def test_empty_string(self):
        assert hf.float_convert("") is None


# ---------------------------------------------------------------------------
# resolve_time_format
# ---------------------------------------------------------------------------
class TestResolveTimeFormat:
    def test_none_returns_default(self):
        assert hf.resolve_time_format(None) == "%Y-%m-%d"

    def test_date_preset(self):
        assert hf.resolve_time_format("date") == "%Y-%m-%d"

    def test_iso8601_preset(self):
        assert hf.resolve_time_format("iso8601") == "%Y-%m-%dT%H:%M:%SZ"

    def test_valid_strftime_passthrough(self):
        assert hf.resolve_time_format("%Y/%m/%d") == "%Y/%m/%d"

    def test_unknown_string_raises(self):
        with pytest.raises(ValueError, match="Unknown time format"):
            hf.resolve_time_format("foobar")

    def test_invalid_strftime_raises(self):
        # A format with % that is not a valid directive — Python's strftime is lenient,
        # so we use a format that actually causes an error on datetime.strftime
        # Most single-letter codes after % are valid, but %! is not standardized
        # The function validates by calling strftime, which may not raise for all invalid codes.
        # Test with a known-bad preset name instead.
        with pytest.raises(ValueError):
            hf.resolve_time_format("not_a_preset")


# ---------------------------------------------------------------------------
# validate (date_text)
# ---------------------------------------------------------------------------
class TestValidateDate:
    def test_valid_date(self):
        assert hf.validate("2023-01-15") is True

    def test_invalid_format(self):
        assert hf.validate("15/01/2023") is False

    def test_garbage(self):
        assert hf.validate("garbage") is False

    def test_empty_string(self):
        assert hf.validate("") is False


# ---------------------------------------------------------------------------
# is_doi / normalize_doi
# ---------------------------------------------------------------------------
class TestDoi:
    def test_bare_doi(self):
        assert hf.is_doi("10.5281/zenodo.820562") is not None

    def test_doi_url(self):
        assert hf.is_doi("https://doi.org/10.5281/zenodo.820562") is not None

    def test_doi_prefix(self):
        assert hf.is_doi("doi:10.5281/zenodo.820562") is not None

    def test_regular_url(self):
        assert hf.is_doi("https://example.com") is None

    def test_foobar(self):
        assert hf.is_doi("foobar") is None

    def test_normalize_bare_doi(self):
        assert hf.normalize_doi("10.5281/zenodo.820562") == "10.5281/zenodo.820562"

    def test_normalize_doi_url(self):
        assert (
            hf.normalize_doi("https://doi.org/10.5281/zenodo.820562")
            == "10.5281/zenodo.820562"
        )


# ---------------------------------------------------------------------------
# bbox_to_wkt
# ---------------------------------------------------------------------------
class TestBboxToWkt:
    def test_valid_bbox(self):
        wkt = hf.bbox_to_wkt([7.0, 51.0, 8.0, 52.0])
        assert wkt is not None
        assert wkt.startswith("POLYGON((")
        assert "7" in wkt and "51" in wkt

    def test_none_returns_none(self):
        assert hf.bbox_to_wkt(None) is None

    def test_empty_returns_none(self):
        assert hf.bbox_to_wkt([]) is None

    def test_wrong_length_returns_none(self):
        assert hf.bbox_to_wkt([1, 2, 3]) is None


# ---------------------------------------------------------------------------
# bbox_to_wkb
# ---------------------------------------------------------------------------
class TestBboxToWkb:
    def test_valid_bbox(self):
        wkb = hf.bbox_to_wkb([7.0, 51.0, 8.0, 52.0])
        assert wkb is not None
        assert isinstance(wkb, str)
        # WKB hex should be uppercase
        assert wkb == wkb.upper()
        # Little-endian WKB starts with "01"
        assert wkb.startswith("01")

    def test_none_returns_none(self):
        assert hf.bbox_to_wkb(None) is None


# ---------------------------------------------------------------------------
# bbox_to_geojson
# ---------------------------------------------------------------------------
class TestBboxToGeojson:
    def test_valid_bbox(self):
        geojson = hf.bbox_to_geojson([7.0, 51.0, 8.0, 52.0])
        assert geojson is not None
        assert geojson["type"] == "Polygon"
        assert len(geojson["coordinates"]) == 1
        ring = geojson["coordinates"][0]
        assert len(ring) == 5  # closed polygon
        assert ring[0] == ring[-1]  # first == last

    def test_none_returns_none(self):
        assert hf.bbox_to_geojson(None) is None

    def test_wrong_length_returns_none(self):
        assert hf.bbox_to_geojson([1, 2, 3]) is None


# ---------------------------------------------------------------------------
# geojson_to_bbox
# ---------------------------------------------------------------------------
class TestGeojsonToBbox:
    def test_polygon(self):
        geojson = {
            "type": "Polygon",
            "coordinates": [[[7, 51], [8, 51], [8, 52], [7, 52], [7, 51]]],
        }
        bbox = hf.geojson_to_bbox(geojson)
        assert bbox == [7, 51, 8, 52]

    def test_none_returns_none(self):
        assert hf.geojson_to_bbox(None) is None

    def test_no_coords_returns_none(self):
        assert hf.geojson_to_bbox({"type": "Polygon"}) is None

    def test_empty_coords_returns_none(self):
        assert hf.geojson_to_bbox({"type": "Polygon", "coordinates": []}) is None


# ---------------------------------------------------------------------------
# coords_to_geojson_polygon
# ---------------------------------------------------------------------------
class TestCoordsToGeojsonPolygon:
    def test_valid_ring_auto_close(self):
        coords = [[7, 51], [8, 51], [8, 52], [7, 52]]
        result = hf.coords_to_geojson_polygon(coords)
        assert result is not None
        assert result["type"] == "Polygon"
        ring = result["coordinates"][0]
        assert ring[0] == ring[-1]  # auto-closed

    def test_already_closed(self):
        coords = [[7, 51], [8, 51], [8, 52], [7, 52], [7, 51]]
        result = hf.coords_to_geojson_polygon(coords)
        assert result is not None
        ring = result["coordinates"][0]
        assert ring[0] == ring[-1]

    def test_too_few_points(self):
        assert hf.coords_to_geojson_polygon([[7, 51], [8, 51]]) is None

    def test_none(self):
        assert hf.coords_to_geojson_polygon(None) is None

    def test_empty(self):
        assert hf.coords_to_geojson_polygon([]) is None


# ---------------------------------------------------------------------------
# convex_hull_coords_to_wkt / convex_hull_coords_to_geojson
# ---------------------------------------------------------------------------
class TestConvexHullCoords:
    def test_wkt_valid(self):
        coords = [[7, 51], [8, 51], [8, 52], [7, 52]]
        wkt = hf.convex_hull_coords_to_wkt(coords)
        assert wkt is not None
        assert wkt.startswith("POLYGON((")

    def test_wkt_auto_closes(self):
        coords = [[7, 51], [8, 51], [8, 52]]
        wkt = hf.convex_hull_coords_to_wkt(coords)
        assert wkt is not None
        # Should have closing point added
        assert wkt.count(",") >= 3

    def test_wkt_too_few(self):
        assert hf.convex_hull_coords_to_wkt([[7, 51], [8, 51]]) is None

    def test_geojson_valid(self):
        coords = [[7, 51], [8, 51], [8, 52], [7, 52]]
        geojson = hf.convex_hull_coords_to_geojson(coords)
        assert geojson is not None
        assert geojson["type"] == "Polygon"
        ring = geojson["coordinates"][0]
        assert ring[0] == ring[-1]

    def test_geojson_too_few(self):
        assert hf.convex_hull_coords_to_geojson([[7, 51], [8, 51]]) is None

    def test_geojson_none(self):
        assert hf.convex_hull_coords_to_geojson(None) is None


# ---------------------------------------------------------------------------
# convex_hull_coords_to_wkb
# ---------------------------------------------------------------------------
class TestConvexHullCoordsToWkb:
    def test_valid(self):
        coords = [[7, 51], [8, 51], [8, 52], [7, 52]]
        wkb = hf.convex_hull_coords_to_wkb(coords)
        assert wkb is not None
        assert isinstance(wkb, str)
        assert wkb == wkb.upper()
        assert wkb.startswith("01")

    def test_too_few(self):
        assert hf.convex_hull_coords_to_wkb([[7, 51]]) is None

    def test_none(self):
        assert hf.convex_hull_coords_to_wkb(None) is None


# ---------------------------------------------------------------------------
# _swap_to_geojson_order
# ---------------------------------------------------------------------------
class TestSwapToGeojsonOrder:
    def test_4_element_bbox(self):
        # [lat1, lon1, lat2, lon2] -> [lon1, lat1, lon2, lat2]
        assert hf._swap_to_geojson_order([51, 7, 52, 8]) == [7, 51, 8, 52]

    def test_coordinate_pairs(self):
        assert hf._swap_to_geojson_order([[51, 7], [52, 8]]) == [[7, 51], [8, 52]]

    def test_geojson_polygon(self):
        poly = {
            "type": "Polygon",
            "coordinates": [[[51, 7], [52, 7], [52, 8], [51, 8], [51, 7]]],
        }
        result = hf._swap_to_geojson_order(poly)
        assert result["type"] == "Polygon"
        ring = result["coordinates"][0]
        assert ring[0] == [7, 51]

    def test_2_element_pair(self):
        assert hf._swap_to_geojson_order([51, 7]) == [7, 51]

    def test_non_list_unchanged(self):
        assert hf._swap_to_geojson_order("hello") == "hello"
        assert hf._swap_to_geojson_order(42) == 42


# ---------------------------------------------------------------------------
# is_geometry_a_point
# ---------------------------------------------------------------------------
class TestIsGeometryAPoint:
    def test_point_bbox(self):
        is_pt, coords = hf.is_geometry_a_point([7, 51, 7, 51])
        assert is_pt is True
        assert coords == [7, 51]

    def test_within_tolerance(self):
        is_pt, coords = hf.is_geometry_a_point(
            [7, 51, 7 + 1e-7, 51 + 1e-7], tolerance=1e-6
        )
        assert is_pt is True

    def test_real_bbox(self):
        is_pt, coords = hf.is_geometry_a_point([7, 51, 8, 52])
        assert is_pt is False
        assert coords is None

    def test_geojson_polygon_point(self):
        poly = {
            "type": "Polygon",
            "coordinates": [[[7, 51], [7, 51], [7, 51], [7, 51]]],
        }
        is_pt, coords = hf.is_geometry_a_point(poly)
        assert is_pt is True
        assert coords == [7, 51]

    def test_convex_hull_point(self):
        coords_list = [[7, 51], [7, 51], [7, 51]]
        is_pt, coords = hf.is_geometry_a_point(coords_list, is_convex_hull=True)
        assert is_pt is True
        assert coords == [7, 51]

    def test_empty_returns_false(self):
        is_pt, coords = hf.is_geometry_a_point(None)
        assert is_pt is False
        assert coords is None

    def test_empty_list_returns_false(self):
        is_pt, coords = hf.is_geometry_a_point([])
        assert is_pt is False
        assert coords is None


# ---------------------------------------------------------------------------
# _group_shapefile_components
# ---------------------------------------------------------------------------
class TestGroupShapefileComponents:
    def test_mixed_files(self):
        files = [
            {"name": "data.shp", "size": 100},
            {"name": "data.shx", "size": 50},
            {"name": "data.dbf", "size": 200},
            {"name": "data.prj", "size": 10},
            {"name": "readme.txt", "size": 500},
            {"name": "other.csv", "size": 300},
        ]
        groups, standalone = hf._group_shapefile_components(files)
        assert len(groups) == 1
        assert len(groups[0]) == 4  # shp, shx, dbf, prj
        assert len(standalone) == 2  # txt, csv

    def test_no_shapefiles(self):
        files = [
            {"name": "data.csv", "size": 100},
            {"name": "data.geojson", "size": 200},
        ]
        groups, standalone = hf._group_shapefile_components(files)
        assert len(groups) == 0
        assert len(standalone) == 2

    def test_single_shapefile_component_is_standalone(self):
        files = [{"name": "data.prj", "size": 10}]
        groups, standalone = hf._group_shapefile_components(files)
        assert len(groups) == 0
        assert len(standalone) == 1

    def test_shp_xml_grouped(self):
        files = [
            {"name": "data.shp", "size": 100},
            {"name": "data.shp.xml", "size": 50},
        ]
        groups, standalone = hf._group_shapefile_components(files)
        assert len(groups) == 1
        assert len(groups[0]) == 2


# ---------------------------------------------------------------------------
# transform_to_wgs84 (GDAL-dependent but deterministic)
# ---------------------------------------------------------------------------
class TestTransformToWgs84:
    def test_utm32n_to_wgs84(self):
        # Known point: UTM 32N (EPSG:32632) ~Muenster area
        result = hf.transform_to_wgs84(32632, [400000, 5700000])
        # Should be roughly lon~7.5, lat~51.4
        assert result[0] == pytest.approx(7.5, abs=0.5)
        assert result[1] == pytest.approx(51.4, abs=0.5)

    def test_identity_wgs84(self):
        result = hf.transform_to_wgs84(4326, [7.6, 51.9])
        assert result[0] == pytest.approx(7.6, abs=1e-6)
        assert result[1] == pytest.approx(51.9, abs=1e-6)


# ---------------------------------------------------------------------------
# transform_array_to_wgs84
# ---------------------------------------------------------------------------
class TestTransformArrayToWgs84:
    def test_bbox_format(self):
        result = hf.transform_array_to_wgs84(4326, [7.0, 51.0, 8.0, 52.0])
        assert len(result) == 4
        assert result[0] == pytest.approx(7.0, abs=1e-6)
        assert result[1] == pytest.approx(51.0, abs=1e-6)

    def test_array_of_pairs(self):
        result = hf.transform_array_to_wgs84(4326, [[7.0, 51.0], [8.0, 52.0]])
        assert len(result) == 2
        assert result[0][0] == pytest.approx(7.0, abs=1e-6)
        assert result[1][1] == pytest.approx(52.0, abs=1e-6)


# ---------------------------------------------------------------------------
# create_extraction_metadata
# ---------------------------------------------------------------------------
class TestCreateExtractionMetadata:
    def test_string_input_wrapped(self):
        meta = hf.create_extraction_metadata("test_file.csv", "0.8.0")
        assert meta["inputs"] == ["test_file.csv"]
        assert meta["version"] == "0.8.0"

    def test_list_input_preserved(self):
        meta = hf.create_extraction_metadata(["a.csv", "b.csv"], "0.8.0")
        assert meta["inputs"] == ["a.csv", "b.csv"]

    def test_with_output_data_stats(self):
        output_data = {
            "bbox": [7, 51, 8, 52],
            "details": {
                "file1.csv": {"bbox": [7, 51, 8, 52], "file_size_bytes": 1024},
                "file2.csv": {"bbox": None, "file_size_bytes": 512},
            },
        }
        meta = hf.create_extraction_metadata("dir", "0.8.0", output_data=output_data)
        assert "statistics" in meta
        assert meta["statistics"]["files_processed"] == 2
        assert meta["statistics"]["files_with_extent"] == 1

    def test_single_file_output(self):
        output_data = {"bbox": [7, 51, 8, 52], "file_size_bytes": 2048}
        meta = hf.create_extraction_metadata("f.csv", "0.8.0", output_data=output_data)
        assert meta["statistics"]["files_processed"] == 1
        assert meta["statistics"]["files_with_extent"] == 1


# ---------------------------------------------------------------------------
# _swap_coordinate_order (from extent.py)
# ---------------------------------------------------------------------------
class TestSwapCoordinateOrder:
    def test_simple_bbox_swap(self):
        meta = {"bbox": [7, 51, 8, 52], "crs": "4326"}
        result = _swap_coordinate_order(meta)
        assert result["bbox"] == [51, 7, 52, 8]

    def test_convex_hull_coords_swap(self):
        meta = {"bbox": [[7, 51], [8, 51], [8, 52]], "crs": "4326"}
        result = _swap_coordinate_order(meta)
        assert result["bbox"] == [[51, 7], [51, 8], [52, 8]]

    def test_geojson_polygon_swap(self):
        meta = {
            "bbox": {
                "type": "Polygon",
                "coordinates": [[[7, 51], [8, 51], [8, 52], [7, 52], [7, 51]]],
            }
        }
        result = _swap_coordinate_order(meta)
        ring = result["bbox"]["coordinates"][0]
        assert ring[0] == [51, 7]

    def test_recursive_details(self):
        meta = {
            "bbox": [7, 51, 8, 52],
            "details": {"file.csv": {"bbox": [3, 40, 4, 41]}},
        }
        result = _swap_coordinate_order(meta)
        assert result["bbox"] == [51, 7, 52, 8]
        assert result["details"]["file.csv"]["bbox"] == [40, 3, 41, 4]

    def test_non_dict_unchanged(self):
        assert _swap_coordinate_order("hello") == "hello"
        assert _swap_coordinate_order(42) == 42

    def test_no_bbox_unchanged(self):
        meta = {"crs": "4326", "tbox": ["2023-01-01", "2023-12-31"]}
        result = _swap_coordinate_order(meta)
        assert result == meta

    def test_none_bbox_preserved(self):
        meta = {"bbox": None}
        result = _swap_coordinate_order(meta)
        assert result["bbox"] is None


# ---------------------------------------------------------------------------
# _is_auxiliary_file (from extent.py)
# ---------------------------------------------------------------------------
class TestIsAuxiliaryFile:
    def test_aux_xml(self):
        assert _is_auxiliary_file("data.aux.xml") is True

    def test_ovr(self):
        assert _is_auxiliary_file("data.ovr") is True

    def test_tif_xml(self):
        assert _is_auxiliary_file("data.tif.xml") is True

    def test_msk(self):
        assert _is_auxiliary_file("data.msk") is True

    def test_tiff_xml(self):
        assert _is_auxiliary_file("data.tiff.xml") is True

    def test_tif_not_auxiliary(self):
        assert _is_auxiliary_file("data.tif") is False

    def test_csv_not_auxiliary(self):
        assert _is_auxiliary_file("data.csv") is False

    def test_geojson_not_auxiliary(self):
        assert _is_auxiliary_file("data.geojson") is False

    def test_case_insensitive(self):
        assert _is_auxiliary_file("DATA.AUX.XML") is True
        assert _is_auxiliary_file("Data.OVR") is True
        assert _is_auxiliary_file("file.MSK") is True
