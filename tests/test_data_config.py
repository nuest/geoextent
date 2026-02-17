"""
Centralized test data configuration for geoextent tests.
This module contains all test file paths and expected results to reduce duplication.
"""

# Test data file paths
TEST_DATA = {
    # NetCDF files
    "netcdf": {
        "zeroes": "tests/testdata/nc/zeroes.nc",
        "ecmwf_era40": "tests/testdata/nc/ECMWF_ERA-40_subset1.nc",
        "nc_gpkg": "tests/testdata/nc/nc.gpkg",
    },
    # KML files
    "kml": {
        "aasee": "tests/testdata/kml/aasee.kml",
        "timestamp_example": "tests/testdata/kml/TimeStamp_example.kml",
    },
    # GPX files
    "gpx": {
        "with_all_fields": "tests/testdata/gpx/gpx1.1_with_all_fields.gpx",
        "error_format": "tests/testdata/gpx/gpx1.1_with_all_fields_error_format.gpx",
    },
    # GML files
    "gml": {
        "clc_portugal": "tests/testdata/gml/clc_1000_PT.gml",
    },
    # GeoJSON files
    "geojson": {
        "muenster_ring": "tests/testdata/geojson/muenster_ring_zeit.geojson",
        "one_point": "tests/testdata/geojson/onePoint.geojson",
        "empty": "tests/testdata/geojson/empty.geojson",
        "invalid_coordinate": "tests/testdata/geojson/invalid_coordinate.geojson",
    },
    # CSV files
    "csv": {
        "cities_nl": "tests/testdata/csv/cities_NL.csv",
        "cities_nl_lat_long": "tests/testdata/csv/cities_NL_lat&long.csv",
        "empty": "tests/testdata/csv/empty_csv.csv",
        # Column variations
        "cities_nl_datetime": "tests/testdata/csv/cities_NL_Datetime.csv",
        "cities_nl_latitude": "tests/testdata/csv/cities_NL_LATITUDE.csv",
        "cities_nl_lat": "tests/testdata/csv/cities_NL_LAT.csv",
        "cities_nl_time_date": "tests/testdata/csv/cities_NL_TIME_DATE.csv",
        # Different delimiters
        "semicolon_delimiter": "tests/testdata/csv/csv_semicolon_delimiter.csv",
        "comma_delimiter": "tests/testdata/csv/csv_comma_delimiter.csv",
        # Column order variations
        "case1": "tests/testdata/csv/cities_NL_case1.csv",
        "case2": "tests/testdata/csv/cities_NL_case2.csv",
        "case3": "tests/testdata/csv/cities_NL_case3.csv",
        "case4": "tests/testdata/csv/cities_NL_case4.csv",
        "case5": "tests/testdata/csv/cities_NL_case5.csv",
        # Time format variations
        "time_iso8601": "tests/testdata/csv/3DCMTcatalog_TakemuraEPS.csv",
        "time_dd_mm_yyyy": "tests/testdata/csv/3DCMTcatalog_TakemuraEPS_dd_mm_yyyy.csv",
        "time_month_abbr": "tests/testdata/csv/3DCMTcatalog_TakemuraEPS_month_abbr_dd_yyyy_time_format.csv",
        "time_mixed": "tests/testdata/csv/3DCMTcatalog_TakemuraEPS_mixed_time_formats.csv",
        # GDAL column name variations (issue #53)
        "cities_nl_xy": "tests/testdata/csv/cities_NL_XY.csv",
        "cities_nl_easting_northing": "tests/testdata/csv/cities_NL_easting_northing.csv",
        "cities_nl_the_geom": "tests/testdata/csv/cities_NL_the_geom.csv",
        "cities_nl_csvt": "tests/testdata/csv/cities_NL_csvt.csv",
        # GeoCSV variants (issue #52)
        "geocsv_semicolon": "tests/testdata/csv/cities_NL_geocsv_semicolon.csv",
        "geocsv_prj": "tests/testdata/csv/cities_NL_geocsv_prj.csv",
        "geocsv_earthscope": "tests/testdata/csv/cities_NL_geocsv_earthscope.csv",
        "geocsv_wkt_polygons": "tests/testdata/csv/cities_NL_geocsv_wkt_polygons.csv",
        "geocsv_earthscope_wkt": "tests/testdata/csv/cities_NL_geocsv_earthscope_wkt.csv",
        "earthscope_stations": "tests/testdata/csv/earthscope_stations.csv",
        # PRJ sidecar with projected CRS (issue #52, step 6)
        "rd_new_prj": "tests/testdata/csv/cities_NL_rd_new.csv",
    },
    # Folders
    "folders": {
        "one_file": "tests/testdata/folders/folder_one_file",
        "multiple_files": "tests/testdata/folders/folder_multiple_files",
        "mixed_files": "tests/testdata/folders/folder_mixed_files",
    },
    # Shapefile
    "shapefile": {
        "muenster_ring": "tests/testdata/shp/muenster_ring.shp",
    },
    # GeoTIFF
    "geotiff": {
        "wf_100m": "tests/testdata/tif/wf_100m_klas.tif",
    },
}

# Expected results for test data
EXPECTED_RESULTS = {
    # NetCDF expected results
    "netcdf": {
        "zeroes": {
            "bbox": [-52.63157, 19.86842, 52.63157, 25.13157],
            "crs": "4326",
        },
        "nc_gpkg": {
            "bbox": [33.882102, -84.323835, 36.589757, -75.456585],
            "crs": "4326",
        },
    },
    # KML expected results
    "kml": {
        "aasee": {
            "bbox": [51.942465, 7.594213, 51.957278, 7.618246],
            "crs": "4326",
        },
        "timestamp_example": {
            "tbox": ["2007-01-14", "2007-01-14"],
        },
    },
    # GPX expected results
    "gpx": {
        "with_all_fields": {
            "bbox": [10.0, -20.2, 14.0, 46.7],
            "crs": "4326",
            "tbox": ["2013-01-01", "2013-01-01"],
        },
    },
    # GML expected results
    "gml": {
        "clc_portugal": {
            "bbox": [32.39669, -17.54207, 39.30114, -6.95939],
            "crs": "4326",
        },
    },
    # GeoJSON expected results
    "geojson": {
        "muenster_ring": {
            "bbox": [51.948814, 7.601680, 51.974624, 7.647256],
            "crs": "4326",
            "tbox": ["2018-11-14", "2018-11-14"],
        },
        "one_point": {
            "bbox": [50.521503, 6.220493, 50.521503, 6.220493],
            "crs": "4326",
        },
    },
    # CSV expected results
    "csv": {
        "cities_nl": {
            "bbox": [51.434444, 4.3175, 53.217222, 6.574722],
            "crs": "4326",
            "tbox": ["2017-08-01", "2019-09-30"],
        },
        "cities_nl_time_date": {
            "bbox": [51.434444, 4.3175, 53.217222, 6.574722],
            "crs": "4326",
            "tbox": ["2010-09-01", "2019-09-30"],
        },
        "time_iso8601": {
            "tbox": ["2017-04-08", "2020-02-06"],
        },
        "time_dd_mm_yyyy": {
            "tbox": ["2017-01-08", "2018-10-01"],
        },
        "time_month_abbr": {
            "tbox": ["2017-04-09", "2017-07-20"],
        },
        "time_mixed": {
            "tbox": ["2017-04-09", "2018-01-31"],
        },
        # GeoCSV variants (issue #52) — same cities_NL point data
        "geocsv_semicolon": {
            "bbox": [51.434444, 4.3175, 53.217222, 6.574722],
            "crs": "4326",
            "tbox": ["2017-08-01", "2019-09-30"],
        },
        "geocsv_prj": {
            "bbox": [51.434444, 4.3175, 53.217222, 6.574722],
            "crs": "4326",
            "tbox": ["2017-08-01", "2019-09-30"],
        },
        "geocsv_earthscope": {
            "bbox": [51.434444, 4.3175, 53.217222, 6.574722],
            "crs": "4326",
            "tbox": ["2017-08-01", "2019-09-30"],
        },
        # WKT polygon data — bounding box of polygons
        "geocsv_wkt_polygons": {
            "bbox": [51.42, 4.31, 53.23, 6.58],
            "crs": "4326",
            "tbox": ["2017-08-01", "2019-09-30"],
        },
        "geocsv_earthscope_wkt": {
            "bbox": [51.42, 4.31, 53.23, 6.58],
            "crs": "4326",
        },
        # PRJ sidecar with projected CRS (EPSG:28992 RD New, issue #52 step 6)
        # Coordinates are transformed from RD New, so they differ slightly from
        # the original WGS84 cities_NL values due to double transformation
        "rd_new_prj": {
            "bbox": [51.4297, 4.3329, 53.2172, 6.5747],
            "crs": "4326",
            "tbox": ["2017-08-01", "2019-09-30"],
        },
        # Real EarthScope FDSNWS station data (3 stations: ADK, AFI, ANMO)
        "earthscope_stations": {
            "bbox": [-13.90853, -176.6842, 51.8823, -106.4572],
            "crs": "4326",
        },
    },
    # Folder expected results
    "folders": {
        "one_file": {
            "bbox": [51.948814, 7.601680, 51.974624, 7.647256],
            "crs": "4326",
            "tbox": ["2018-11-14", "2018-11-14"],
        },
    },
}


# Convenience functions to get test data
def get_test_file(format_name, file_key):
    """Get the path to a test file"""
    return TEST_DATA[format_name][file_key]


def get_expected_result(format_name, file_key):
    """Get the expected result for a test file"""
    return EXPECTED_RESULTS[format_name][file_key]


def get_expected_bbox(format_name, file_key):
    """Get the expected bbox for a test file"""
    result = EXPECTED_RESULTS[format_name][file_key]
    return result.get("bbox")


def get_expected_tbox(format_name, file_key):
    """Get the expected tbox for a test file"""
    result = EXPECTED_RESULTS[format_name][file_key]
    return result.get("tbox")


def get_expected_crs(format_name, file_key):
    """Get the expected CRS for a test file"""
    result = EXPECTED_RESULTS[format_name][file_key]
    return result.get("crs", "4326")  # Default to WGS84
