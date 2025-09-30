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


class TestCSVEdgeCases:
    """Test CSV edge cases and error conditions"""

    def test_empty_csv_file(self):
        """Test handling of empty CSV file"""
        result = extract_bbox_only(get_test_file("csv", "empty"))
        assert_empty_result(result)
