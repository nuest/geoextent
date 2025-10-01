import pytest
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
    tolerance,
)
from test_data_config import (
    get_test_file,
    get_expected_bbox,
    get_expected_tbox,
    get_expected_crs,
)

# Test data constants
NL_CITIES_BBOX = [4.3175, 51.434444, 6.574722, 53.217222]
NL_CITIES_TBOX = ["2017-08-01", "2019-09-30"]


class TestCSVBboxExtraction:
    """Test spatial extent extraction from CSV files"""

    def test_extract_bbox_lat_long_columns(self):
        """Test bbox extraction from CSV with lat/long columns"""
        result = extract_bbox_only(get_test_file("csv", "cities_nl_lat_long"))
        assert_bbox_result(result, get_expected_bbox("csv", "cities_nl"))
        assert_no_tbox(result)

    def test_extract_bbox_standard_format(self):
        """Test bbox extraction from standard CSV format"""
        result = extract_bbox_only(get_test_file("csv", "cities_nl"))
        assert_bbox_result(result, get_expected_bbox("csv", "cities_nl"))


class TestCSVTboxExtraction:
    """Test temporal extent extraction from CSV files"""

    def test_extract_tbox_only(self):
        """Test tbox extraction without bbox"""
        result = extract_tbox_only(get_test_file("csv", "cities_nl"))
        assert_tbox_result(result, get_expected_tbox("csv", "cities_nl"))
        assert_no_bbox(result)


class TestCSVCombinedExtraction:
    """Test combined spatial and temporal extent extraction"""

    def test_extract_bbox_and_tbox(self):
        """Test extraction of both spatial and temporal extents"""
        result = extract_bbox_and_tbox(get_test_file("csv", "cities_nl"))
        assert_bbox_and_tbox_result(
            result,
            get_expected_bbox("csv", "cities_nl"),
            get_expected_tbox("csv", "cities_nl"),
        )


class TestCSVDelimiters:
    """Test CSV parsing with different delimiters"""

    def test_semicolon_delimiter(self):
        """Test CSV parsing with semicolon delimiter"""
        result = extract_bbox_and_tbox(get_test_file("csv", "semicolon_delimiter"))
        assert_bbox_and_tbox_result(
            result,
            get_expected_bbox("csv", "cities_nl"),
            get_expected_tbox("csv", "cities_nl"),
        )

    def test_comma_delimiter(self):
        """Test CSV parsing with comma delimiter"""
        result = extract_bbox_and_tbox(get_test_file("csv", "comma_delimiter"))
        assert_bbox_and_tbox_result(
            result,
            get_expected_bbox("csv", "cities_nl"),
            get_expected_tbox("csv", "cities_nl"),
        )


class TestCSVColumnVariations:
    """Test CSV files with different column naming and order variations"""

    def test_datetime_column(self):
        """Test CSV with datetime column"""
        result = extract_bbox_and_tbox("tests/testdata/csv/cities_NL_Datetime.csv")
        assert_bbox_and_tbox_result(result, NL_CITIES_BBOX, NL_CITIES_TBOX)

    def test_latitude_column_name(self):
        """Test CSV with LATITUDE column name"""
        result = extract_bbox_and_tbox("tests/testdata/csv/cities_NL_LATITUDE.csv")
        assert_bbox_and_tbox_result(result, NL_CITIES_BBOX, NL_CITIES_TBOX)

    def test_lat_column_name(self):
        """Test CSV with LAT column name"""
        result = extract_bbox_and_tbox("tests/testdata/csv/cities_NL_LAT.csv")
        assert_bbox_and_tbox_result(result, NL_CITIES_BBOX, NL_CITIES_TBOX)

    def test_time_date_columns(self):
        """Test CSV with TIME_DATE columns"""
        result = extract_bbox_and_tbox("tests/testdata/csv/cities_NL_TIME_DATE.csv")
        expected_tbox = ["2010-09-01", "2019-09-30"]
        assert_bbox_and_tbox_result(result, NL_CITIES_BBOX, expected_tbox)

    def test_columns_different_order_case1(self):
        """Test CSV with columns in different order - case 1"""
        result = extract_bbox_and_tbox("tests/testdata/csv/cities_NL_case1.csv")
        assert_bbox_and_tbox_result(result, NL_CITIES_BBOX, NL_CITIES_TBOX)

    def test_columns_different_order_case2(self):
        """Test CSV with columns in different order - case 2 (caps)"""
        result = extract_bbox_and_tbox("tests/testdata/csv/cities_NL_case2.csv")
        assert_bbox_and_tbox_result(result, NL_CITIES_BBOX, NL_CITIES_TBOX)

    def test_columns_alternative_names_case3(self):
        """Test CSV with alternative column names - case 3"""
        result = extract_bbox_and_tbox("tests/testdata/csv/cities_NL_case3.csv")
        assert_bbox_and_tbox_result(result, NL_CITIES_BBOX, NL_CITIES_TBOX)

    def test_columns_alternative_names_case4(self):
        """Test CSV with alternative column names - case 4"""
        result = extract_bbox_and_tbox("tests/testdata/csv/cities_NL_case4.csv")
        assert_bbox_and_tbox_result(result, NL_CITIES_BBOX, NL_CITIES_TBOX)

    def test_columns_alternative_names_case5(self):
        """Test CSV with alternative column names - case 5"""
        result = extract_bbox_and_tbox("tests/testdata/csv/cities_NL_case5.csv")
        assert_bbox_and_tbox_result(result, NL_CITIES_BBOX, NL_CITIES_TBOX)


class TestCSVTimeFormats:
    """Test CSV files with different time formats"""

    def test_iso8601_time_format(self):
        """Test CSV with ISO8601 time format"""
        result = extract_tbox_only("tests/testdata/csv/3DCMTcatalog_TakemuraEPS.csv")
        expected_tbox = ["2017-04-08", "2020-02-06"]
        assert_tbox_result(result, expected_tbox)
        assert_no_bbox(result)

    def test_dd_mm_yyyy_time_format(self):
        """Test CSV with dd/mm/yyyy time format"""
        result = extract_tbox_only(
            "tests/testdata/csv/3DCMTcatalog_TakemuraEPS_dd_mm_yyyy.csv"
        )
        expected_tbox = ["2017-01-08", "2018-10-01"]
        assert_tbox_result(result, expected_tbox)
        assert_no_bbox(result)

    def test_month_abbreviation_format(self):
        """Test CSV with month abbreviation format"""
        result = extract_tbox_only(
            "tests/testdata/csv/3DCMTcatalog_TakemuraEPS_month_abbr_dd_yyyy_time_format.csv"
        )
        expected_tbox = ["2017-04-09", "2017-07-20"]
        assert_tbox_result(result, expected_tbox)
        assert_no_bbox(result)

    def test_mixed_time_formats(self):
        """Test CSV with mixed time formats"""
        result = extract_tbox_only(
            "tests/testdata/csv/3DCMTcatalog_TakemuraEPS_mixed_time_formats.csv"
        )
        expected_tbox = ["2017-04-09", "2018-01-31"]
        assert_tbox_result(result, expected_tbox)
        assert_no_bbox(result)


class TestCSVSampling:
    """Test CSV sampling functionality"""

    def test_random_sample_valid(self):
        """Test temporal extraction with valid random sampling"""
        import geoextent.lib.extent as geoextent

        result = geoextent.fromFile(
            "tests/testdata/csv/3DCMTcatalog_TakemuraEPS.csv",
            bbox=False,
            tbox=True,
            num_sample=5,
        )
        expected_tbox = ["2017-04-08", "2020-02-06"]
        assert_tbox_result(result, expected_tbox)
        assert_no_bbox(result)

    def test_random_sample_invalid_negative(self):
        """Test temporal extraction with invalid negative sample size"""
        import geoextent.lib.extent as geoextent

        result = geoextent.fromFile(
            "tests/testdata/csv/3DCMTcatalog_TakemuraEPS.csv",
            bbox=False,
            tbox=True,
            num_sample=-1,
        )
        assert_no_bbox(result)
        assert_no_tbox(result)

    def test_random_sample_larger_than_data(self):
        """Test temporal extraction with sample size larger than data"""
        import geoextent.lib.extent as geoextent

        result = geoextent.fromFile(
            "tests/testdata/csv/3DCMTcatalog_TakemuraEPS.csv",
            bbox=False,
            tbox=True,
            num_sample=1000000,
        )
        expected_tbox = ["2017-04-08", "2020-02-06"]
        assert_tbox_result(result, expected_tbox)
        assert_no_bbox(result)


class TestCSVGeometryColumns:
    """Test CSV files with geometry columns (WKT/WKB format)"""

    def test_extract_bbox_from_geometry_column_opara_sample(self):
        """Test extraction from WKT geometry column using real Opara repository data"""
        result = extract_bbox_only("tests/testdata/csv_with_geometry_sample.csv")

        assert result is not None
        assert "bbox" in result
        bbox = result["bbox"]

        # Expected bbox based on the 20 sample rows from mc_registry_v6.csv
        # These coordinates cover parts of Africa based on the sample data
        assert bbox[0] < bbox[2]  # min_x < max_x
        assert bbox[1] < bbox[3]  # min_y < max_y

        # Check that we get reasonable coordinates for African continent
        assert -30 <= bbox[0] <= 50  # Longitude range for Africa
        assert -40 <= bbox[1] <= 40  # Latitude range for Africa
        assert -30 <= bbox[2] <= 50  # Longitude range for Africa
        assert -40 <= bbox[3] <= 40  # Latitude range for Africa

    def test_extract_bbox_wkt_geometry_column(self):
        """Test extraction from WKT geometry column"""
        result = extract_bbox_only("tests/testdata/csv_wkt_geometry.csv")
        assert_bbox_result(result, [8.0, 18.0, 15.0, 25.0])

    def test_extract_bbox_coordinates_column(self):
        """Test extraction from coordinates column"""
        result = extract_bbox_only("tests/testdata/csv_coordinates_column.csv")
        assert_bbox_result(result, [0.0, 0.0, 12.0, 22.0])

    def test_extract_bbox_coords_column(self):
        """Test extraction from coords column"""
        result = extract_bbox_only("tests/testdata/csv_coords_column.csv")
        assert_bbox_result(result, [0.0, 0.0, 10.0, 14.0])

    def test_extract_bbox_geom_column(self):
        """Test extraction from geom column"""
        result = extract_bbox_only("tests/testdata/csv_geom_column.csv")
        assert_bbox_result(result, [1.0, 1.0, 13.0, 23.0])

    def test_extract_bbox_wkb_column(self):
        """Test extraction from WKB (hex-encoded) column"""
        result = extract_bbox_only("tests/testdata/csv_wkb_column.csv")
        assert_bbox_result(result, [2.0, 2.0, 11.0, 19.0])

    def test_geometry_column_detection_patterns(self):
        """Test that all geometry column name patterns are detected"""
        import geoextent.lib.handleCSV as handleCSV
        import re

        # Test all search patterns
        search_geometry = [
            "(.)*geometry(.)*",
            "(.)*geom(.)*",
            "^wkt",
            "wkt$",
            "(.)*wkt(.)*",
            "^wkb",
            "wkb$",
            "(.)*wkb(.)*",
            "(.)*coordinates(.)*",
            "(.)*coords(.)*",
            "^coords",
            "coords$",
            "^coordinates",
            "coordinates$",
        ]

        test_columns = [
            "geometry",
            "geom",
            "wkt",
            "wkb",
            "coordinates",
            "coords",
            "my_geometry",
            "data_geom",
            "point_wkt",
            "line_wkb",
            "spatial_coordinates",
            "location_coords",
        ]

        for col_name in test_columns:
            found = False
            for pattern in search_geometry:
                p = re.compile(pattern, re.IGNORECASE)
                if p.search(col_name) is not None:
                    found = True
                    break
            assert found, f"Should detect geometry column: {col_name}"

    def test_geometry_fallback_to_coordinate_columns(self):
        """Test that extraction falls back to coordinate columns when no geometry column exists"""
        # Test with traditional lat/lon CSV that doesn't have geometry column
        result = extract_bbox_only("tests/testdata/csv/cities_NL_lat_lon_alt.csv")

        assert result is not None
        assert "bbox" in result
        bbox = result["bbox"]

        # Should still work with traditional coordinate extraction
        assert pytest.approx(bbox[0], tolerance) == 4.3175
        assert pytest.approx(bbox[1], tolerance) == 51.434444
        assert pytest.approx(bbox[2], tolerance) == 6.574722
        assert pytest.approx(bbox[3], tolerance) == 53.217222

    def test_invalid_geometry_handling(self):
        """Test that invalid WKT/WKB geometries are handled gracefully"""
        import geoextent.lib.handleCSV as handleCSV
        import csv
        import tempfile
        import os

        # Create a temporary CSV with some invalid geometry data
        test_data = [
            ["id", "geometry"],
            ["1", "POINT (10.0 20.0)"],  # Valid WKT
            ["2", "INVALID WKT DATA"],  # Invalid
            ["3", "POINT (15.0 25.0)"],  # Valid WKT
            ["4", ""],  # Empty
            ["5", "deadbeef"],  # Invalid hex
        ]

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            writer = csv.writer(f)
            writer.writerows(test_data)
            temp_path = f.name

        try:
            result = handleCSV._extract_bbox_from_geometry_column(temp_path)
            assert result is not None
            assert "bbox" in result
            bbox = result["bbox"]
            # Should extract bbox from valid geometries only
            assert bbox == [10.0, 20.0, 15.0, 25.0]  # min_x, min_y, max_x, max_y
        finally:
            os.unlink(temp_path)

    def test_mixed_geometry_types(self):
        """Test CSV with mixed geometry types (POINT, POLYGON, LINESTRING)"""
        import csv
        import tempfile
        import os

        # Create a temporary CSV with mixed geometry types
        test_data = [
            ["id", "geom_type", "geometry"],
            ["1", "point", "POINT (5.0 10.0)"],
            ["2", "polygon", "POLYGON ((0 0, 5 0, 5 5, 0 5, 0 0))"],
            ["3", "linestring", "LINESTRING (0 0, 10 10)"],
            ["4", "point", "POINT (15.0 20.0)"],
        ]

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            writer = csv.writer(f)
            writer.writerows(test_data)
            temp_path = f.name

        try:
            result = extract_bbox_only(temp_path)
            assert result is not None
            assert "bbox" in result
            bbox = result["bbox"]
            # Should encompass all geometries
            assert bbox == [0.0, 0.0, 15.0, 20.0]  # min_x, min_y, max_x, max_y
        finally:
            os.unlink(temp_path)


class TestCSVEdgeCases:
    """Test CSV edge cases and error conditions"""

    def test_empty_csv_file(self):
        """Test handling of empty CSV file"""
        result = extract_bbox_only(get_test_file("csv", "empty"))
        assert_empty_result(result)
