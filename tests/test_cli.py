import os  # used to get the location of the testdata
from osgeo import ogr
import sys
import pytest
import tempfile
import json
import geoextent
from help_functions_test import create_zip, parse_coordinates, tolerance


def test_help_text_direct(script_runner):
    ret = script_runner.run("geoextent", "--help")
    assert ret.success, "process should return success"
    assert ret.stderr == "", "stderr should be empty"
    assert "geoextent [-h]" in ret.stdout, "usage instructions are printed to console"


def test_help_text_no_args(script_runner):
    ret = script_runner.run("geoextent")
    assert ret.success, "process should return success"
    assert ret.stderr == "", "stderr should be empty"
    assert "geoextent [-h]" in ret.stdout, "usage instructions are printed to console"


def test_details_folder(script_runner):
    ret = script_runner.run(
        "geoextent", "-b", "-t", "--details", "tests/testdata/folders/folder_one_file"
    )
    assert ret.success, "process should return success"
    result = ret.stdout
    assert "'details'" in result


def test_no_details_folder(script_runner):
    ret = script_runner.run(
        "geoextent", "-b", "-t", "tests/testdata/folders/folder_one_file"
    )
    assert ret.success, "process should return success"
    result = ret.stdout
    assert "'details'" not in result


def test_error_no_file(script_runner):
    ret = script_runner.run("geoextent", "doesntexist")
    assert not ret.success, "process should return failure"
    assert ret.stderr != "", "stderr should not be empty"
    assert "doesntexist" in ret.stderr, "wrong input is printed to console"
    assert ret.stdout == ""


def test_error_no_option(script_runner):
    ret = script_runner.run("geoextent", "README.md")
    assert not ret.success, "process should return failure"
    assert ret.stderr != "", "stderr should not be empty"
    assert "one of extraction options" in ret.stderr
    assert ret.stdout == ""


def test_debug_output(script_runner):
    ret = script_runner.run(
        "geoextent", "-b", "tests/testdata/geojson/muenster_ring_zeit.geojson"
    )
    assert ret.success, "process should return success"
    assert "DEBUG:geoextent" not in ret.stderr
    assert "INFO:geoextent" not in ret.stderr
    assert "DEBUG:geoextent" not in ret.stdout
    assert "INFO:geoextent" not in ret.stdout

    # FIXME
    # ret = script_runner.run('geoextent',
    #    '--debug',
    #    '-b',
    #    'tests/testdata/geojson/muenster_ring_zeit.geojson')
    # assert ret.success, "process should return success"
    # assert "DEBUG:geoextent" in ret.stdout
    # assert "geoextent" not in ret.stdout


# FIXME
# def test_debug_config_env_var(script_runner):
#    os.environ["GEOEXTENT_DEBUG"] = "1" # this is picked up by the library, BUT the stdout is empty still
#    ret = script_runner.run('geoextent', '-b', 'tests/testdata/geojson/muenster_ring_zeit.geojson')
#    assert ret.success, "process should return success"
#    assert "DEBUG:geoextent" in ret.stdout
#    os.environ["GEOEXTENT_DEBUG"] = None


def test_geojson_invalid_second_input(script_runner):
    ret = script_runner.run(
        "geoextent",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
        "tests/testdata/geojson/not_existing.geojson",
    )
    assert not ret.success, "process should return failure"
    assert ret.stderr != "", "stderr should not be empty"
    assert (
        "not a valid directory or file" in ret.stderr
    ), "wrong input is printed to console"
    assert (
        "tests/testdata/geojson/not_existing.geojson" in ret.stderr
    ), "wrong input is printed to console"
    assert ret.stdout == ""


def test_geojson_bbox(script_runner):
    ret = script_runner.run(
        "geoextent", "-b", "tests/testdata/geojson/muenster_ring_zeit.geojson"
    )
    assert ret.success, "process should return success"
    result = ret.stdout
    bboxList = parse_coordinates(result)
    assert bboxList == pytest.approx(
        [7.601680, 51.948814, 7.647256, 51.974624], abs=tolerance
    )
    assert "4326" in result


def test_geojson_bbox_long_name(script_runner):
    ret = script_runner.run(
        "geoextent",
        "--bounding-box",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret.success, "process should return success"
    result = ret.stdout
    bboxList = parse_coordinates(result)
    assert bboxList == pytest.approx(
        [7.601680, 51.948814, 7.6472568, 51.974624], abs=tolerance
    )
    assert "4326" in result


def test_geojson_bbox_invalid_coordinates(script_runner):
    ret = script_runner.run(
        "geoextent", "-b", "tests/testdata/geojson/invalid_coordinate.geojson"
    )
    assert ret.success, "process should return success"
    assert ret.stderr is not None
    assert "bbox" not in ret.stdout, "stderr should not be empty"


def test_geojson_time(script_runner):
    ret = script_runner.run(
        "geoextent", "-t", "tests/testdata/geojson/muenster_ring_zeit.geojson"
    )
    assert ret.success, "process should return success"
    assert (
        "['2018-11-14', '2018-11-14']" in ret.stdout
    ), "time value is printed to console"


def test_geojson_time_invalid(script_runner):
    ret = script_runner.run(
        "geoextent", "-t", "tests/testdata/geojson/invalid_time.geojson"
    )
    assert ret.success, "process should return success"
    assert "'tbox'" not in ret.stdout


def test_print_supported_formats(script_runner):
    ret = script_runner.run("geoextent", "--formats")
    assert ret.success, "process should return success"
    assert ret.stderr == "", "stderr should be empty"
    assert (
        "Supported formats:" in ret.stdout
    ), "list of supported formats is printed to console"


def test_netcdf_bbox(script_runner):
    ret = script_runner.run("geoextent", "-b", "tests/testdata/nc/zeroes.nc")
    assert ret.success, "process should return success"
    assert ret.stderr == "", "stderr should be empty"
    result = ret.stdout
    bboxList = parse_coordinates(result)
    assert bboxList == pytest.approx(
        [19.86842, -52.63157, 25.13157, 52.63157], abs=tolerance
    )
    assert "4326" in result


@pytest.mark.skip(reason="file format not implemented yet")
def test_netcdf_time(script_runner):
    result = script_runner.run(
        "geoextent", "-t", "tests/testdata/nc/ECMWF_ERA-40_subset.nc"
    )
    assert result.success, "process should return success"
    assert result.stderr == "", "stderr should be empty"
    assert (
        "['2002-07-01','2002-07-31']" in result.stdout
    ), "time value is printed to console"


@pytest.mark.skip(reason="file format not implemented yet")
def test_netcdf_time_invalid(script_runner):
    ret = script_runner.run(
        "geoextent", "-b", "tests/testdata/nc/ECMWF_ERA-40_subset.nc"
    )
    assert ret.success, "process should return success"
    assert ret.stderr is not None
    assert ret.stderr == "invalid time format", "stderr should not be empty"


def test_kml_bbox(script_runner):
    ret = script_runner.run("geoextent", "-b", "tests/testdata/kml/aasee.kml")
    result = ret.stdout
    bboxList = parse_coordinates(result)
    assert bboxList == pytest.approx(
        [7.594213, 51.942465, 7.618246, 51.957278], abs=tolerance
    )
    assert "4326" in result


@pytest.mark.skipif(
    sys.platform == "darwin", reason="MacOS does not load the file properly"
)
def test_kml_time(script_runner):
    ret = script_runner.run(
        "geoextent", "-t", "tests/testdata/kml/TimeStamp_example.kml"
    )
    assert ret.success, "process should return success"
    assert ret.stderr == "", "stderr should be empty"
    assert (
        "['2007-01-14', '2007-01-14']" in ret.stdout
    ), "time value is printed to console"


def test_kml_time_invalid(script_runner):
    ret = script_runner.run(
        "geoextent",
        "-t",
        "tests/testdata/kml/abstractviews_timeprimitive_example_error.kml",
    )
    assert ret.success, "process should return success"
    assert ret.stderr is not None
    assert "'tbox'" not in ret.stdout


def test_gpkg_bbox(script_runner):
    ret = script_runner.run("geoextent", "-b", "tests/testdata/geopackage/nc.gpkg")
    result = ret.stdout
    assert ret.success, "process should return success"
    assert ret.stderr == "", "stderr should be empty"
    bboxList = parse_coordinates(result)
    assert bboxList == pytest.approx(
        [-84.32383, 33.882102, -75.456585, 36.589757], abs=tolerance
    )
    assert "4326" in result


def test_gpkg_tbox(script_runner):
    ret = script_runner.run(
        "geoextent", "-t", "tests/testdata/geopackage/wandelroute_maastricht.gpkg"
    )
    result = ret.stdout
    assert ret.success, "process should return success"
    assert ret.stderr == "", "stderr should be empty"
    assert "['2021-01-05', '2021-01-05']" in result


def test_csv_bbox(script_runner):
    ret = script_runner.run("geoextent", "-b", "tests/testdata/csv/cities_NL.csv")
    assert ret.success, "process should return success"
    result = ret.stdout
    bboxList = parse_coordinates(result)
    assert bboxList == pytest.approx(
        [4.3175, 51.434444, 6.574722, 53.217222], abs=tolerance
    )
    assert "4326" in result


def test_csv_time(script_runner):
    ret = script_runner.run("geoextent", "-t", "tests/testdata/csv/cities_NL.csv")
    assert ret.success, "process should return success"
    assert (
        "['2017-08-01', '2019-09-30']" in ret.stdout
    ), "time value is printed to console"


def test_csv_time_invalid(script_runner):
    ret = script_runner.run(
        "geoextent", "-t", "tests/testdata/csv/cities_NL_lat&long.csv"
    )
    assert ret.success, "process should return success"
    assert ret.stderr is not None
    assert "no TemporalExtent" in ret.stderr, "stderr should not be empty"


def test_gml_time(script_runner):
    ret = script_runner.run("geoextent", "-t", "tests/testdata/gml/clc_1000_PT.gml")
    assert ret.success, "process should return success"
    assert ret.stderr == "", "stderr should be empty"
    assert (
        "['2005-12-31', '2013-11-30']" in ret.stdout
    ), "time value is printed to console"


@pytest.mark.skip(reason="multiple input directories not implemented yet")
def test_gml_only_one_time_feature_valid(script_runner):
    ret = script_runner.run(
        "geoextent", "-t", "tests/testdata/gml/mypolygon_px6_error_time_one_feature.gml"
    )
    assert ret.stdout
    assert (
        "'tbox': ['2012-04-15', '2012-04-15']" in ret.stdout
    ), "time value is printed to console"


def test_shp_bbox_no_crs(script_runner):
    ret = script_runner.run(
        "geoextent", "-b", "tests/testdata/shapefile/Abgrabungen_Kreis_Kleve_Shape.shp"
    )
    assert ret.success, "process should return success"
    assert "'bbox'" not in ret.stdout


def test_shp_tbox(script_runner):
    ret = script_runner.run(
        "geoextent", "-t", "tests/testdata/shapefile/ifgi_denkpause.shp"
    )
    assert ret.success, "process should return success"
    assert "'tbox'" in ret.stdout
    assert "['2021-01-01', '2021-01-01']" in ret.stdout


@pytest.mark.skip(reason="multiple input files not implemented yet")
def test_multiple_files(script_runner):
    ret = script_runner.run(
        "python",
        "geoextent",
        "-b",
        "tests/testdata/shapefile/Abgrabungen_Kreis_Kleve_Shape.shp",
        "tests/testdata/geojson/ausgleichsflaechen_moers.geojson",
    )
    assert ret.success, "process should return success"
    assert ret.stderr == "", "stderr should be empty"
    assert (
        "[7.6016807556152335, 51.94881477206191, 7.647256851196289, 51.974624029877454]"
        in ret.stdout
    ), "bboxes and time values of all files inside folder, are printed to console"
    assert (
        "[6.574722, 51.434444, 4.3175, 53.217222]" in ret.stdout
    ), "bboxes and time values of all files inside folder, are printed to console"
    assert (
        "[292063.81225905, 5618144.09259115, 302531.3161606, 5631223.82854667]"
        in ret.stdout
    ), "bboxes and time values of all files inside folder, are printed to console"


def test_folder(script_runner):
    ret = script_runner.run(
        "geoextent", "-b", "-t", "tests/testdata/folders/folder_two_files"
    )
    assert ret.success, "process should return success"
    assert ret.stderr == "", "stderr should be empty"
    result = ret.stdout
    bboxList = parse_coordinates(result)
    assert bboxList == pytest.approx(
        [2.052333, 41.317038, 7.647256, 51.974624], abs=tolerance
    )
    assert (
        "['2018-11-14', '2019-09-11']" in result
    ), "merge time value of folder files, is printed to console"
    assert "4326" in result


def test_zipfile(script_runner):
    folder_name = "tests/testdata/folders/folder_one_file"
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, "zipfile.zip")
        create_zip(folder_name, zip_path)
        ret = script_runner.run("geoextent", "-b", "-t", zip_path)
        assert ret.success, "process should return success"
        result = ret.stdout
        bboxList = parse_coordinates(result)
        assert bboxList == pytest.approx(
            [7.601680, 51.948814, 7.647256, 51.974624], abs=tolerance
        )
        assert "['2018-11-14', '2018-11-14']" in result
        assert "4326" in result


@pytest.mark.skip(reason="multiple input directories not implemented yet")
def test_multiple_folders(script_runner):
    ret = script_runner.run(
        "python",
        "geoextent",
        "-b",
        "tests/testdata/shapefile",
        "tests/testdata/geojson",
        "tests/testdata/nc",
    )
    assert ret.success, "process should return success"
    assert ret.stderr == "", "stderr should be empty"
    assert (
        "full bbox" in ret.stdout
    ), "joined bboxes of all files inside folder are printed to console"


def test_zenodo_valid_link_repository(script_runner):
    ret = script_runner.run("geoextent", "-b", "-t", "https://zenodo.org/record/820562")
    assert ret.success, "process should return success"
    assert "has no identifiable time extent" in ret.stderr
    result = ret.stdout
    bboxList = parse_coordinates(result)
    assert bboxList == pytest.approx(
        [96.21146, 25.55834, 96.35495, 25.63293], abs=tolerance
    )
    assert "4326" in result


def test_zenodo_valid_doi_repository(script_runner):
    ret = script_runner.run(
        "geoextent", "-b", "-t", "https://doi.org/10.5281/zenodo.820562"
    )
    assert ret.success, "process should return success"
    assert "has no identifiable time extent" in ret.stderr
    result = ret.stdout
    bboxList = parse_coordinates(result)
    assert bboxList == pytest.approx(
        [96.21146, 25.55834, 96.35495, 25.63293], abs=tolerance
    )
    assert "4326" in result


def test_zenodo_valid_link_repository_with_no_geoextent(script_runner):
    ret = script_runner.run(
        "geoextent", "-b", "-t", "https://zenodo.org/record/1810558"
    )
    result = ret.stdout
    assert (
        "bbox" not in result
    ), "This repository contains a PDF file, it should not return a bbox"
    assert (
        "tbox" not in result
    ), "This repository contains a PDF file, it should not return a tbox"


def test_zenodo_invalid_link_repository(script_runner):
    ret = script_runner.run("geoextent", "-b", "-t", "https://zenado.org/record/820562")
    assert not ret.success, "Typo in URL"
    assert "is not a valid" in ret.stderr, "Typo in URL"


def test_zenodo_valid_but_removed_repository(script_runner):
    ret = script_runner.run("geoextent", "-b", "-t", "https://zenodo.org/record/1")
    assert not ret.success
    assert "does not exist" in ret.stderr


def test_zenodo_invalid_doi_but_removed_repository(script_runner):
    ret = script_runner.run(
        "geoextent", "-b", "-t", "https://doi.org/10.5281/zenodo.not.exist"
    )
    assert not ret.success
    assert "Geoextent can not handle this repository identifier" in ret.stderr


def test_zenodo_invalid_but_no_extraction_options(script_runner):
    ret = script_runner.run("geoextent", "https://zenodo.org/record/1")
    assert not ret.success, "No extractions options, geoextent should fail"
    assert (
        "Require at least one of extraction options, but bbox is False and tbox is False"
        in ret.stderr
    )


def test_zenodo_valid_but_not_open_access(script_runner):
    ret = script_runner.run("geoextent", "-b", "-t", "https://zenodo.org/record/51746")
    assert (
        not ret.success
    ), "The repository exists but it is not accessible. Geoextent should fail"
    assert (
        "This record does not have Open Access files. Verify the Access rights of the record"
        in ret.stderr
    )


def test_export_relative_path(script_runner):
    relative = "geoextent_output.gpkg"
    geo_version = geoextent.__version__
    script_runner.run(
        "geoextent",
        "-b",
        "-t",
        "--output",
        relative,
        "tests/testdata/folders/folder_two_files",
    )
    datasource = ogr.Open(relative)
    layer = datasource.GetLayer(0)

    for feature in layer:
        if feature.GetField("handler") == "geoextent:" + geo_version:
            bbox_geom = feature.geometry()

    ext = bbox_geom.GetEnvelope()
    is_valid = bbox_geom.IsValid()
    bbox = [ext[0], ext[2], ext[1], ext[3]]
    os.remove(relative)

    assert is_valid, "Check that the figure is valid ()"
    assert bbox == pytest.approx(
        [2.052333, 41.317038, 7.647256, 51.974624], abs=tolerance
    )


def test_export_no_output_file(script_runner):
    ret = script_runner.run(
        "geoextent", "-b", "-t", "--output", "tests/testdata/folders/folder_two_files"
    )
    assert "Exception: Invalid command, input file missing" in ret.stderr


def test_invalid_order_no_input_file(script_runner):
    ret = script_runner.run(
        "geoextent", "-b", "--output", "-t", "tests/testdata/folders/folder_two_files"
    )
    assert "error: argument --output: expected one argument" in ret.stderr


def test_zenodo_valid_doi_repository_wrong_geopackage_extension(script_runner):
    with pytest.warns(ResourceWarning):
        with tempfile.NamedTemporaryFile(suffix=".abc") as tmp:
            ret = script_runner.run(
                "geoextent",
                "-b",
                "-t",
                "--output",
                tmp.name,
                "https://doi.org/10.5281/zenodo.820562",
            )
    assert ret.success, "process should return success"


def test_export_absolute_path(script_runner):
    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, "geoextent_output.gpkg")
        ret = script_runner.run(
            "geoextent",
            "-b",
            "-t",
            "--output",
            out_path,
            "tests/testdata/folders/folder_two_files",
        )
        assert ret.success
        assert os.path.exists(out_path)


def test_export_invalid_folder_path(script_runner):
    ret = script_runner.run(
        "geoextent",
        "-b",
        "-t",
        "--output",
        "tests/testdata/folders",
        "tests/testdata/folders/folder_two_files",
    )
    assert not ret.success, "Output should be a file not a directory"
    assert "Output must be a file, not a directory:" in ret.stderr


def test_export_overwrite_file(script_runner):
    with tempfile.TemporaryDirectory() as tmp:
        filepath = os.path.join(tmp, "geoextent_output.gpkg")
        file = open(filepath, "w+")
        file.close()
        ret = script_runner.run(
            "geoextent",
            "-b",
            "-t",
            "--output",
            filepath,
            "tests/testdata/folders/folder_two_files",
        )
        assert ret.success
        assert "Overwriting " + tmp in ret.stderr


def test_format_geojson_default(script_runner):
    """Test that GeoJSON format is the default"""
    ret = script_runner.run(
        "geoextent", "-b", "tests/testdata/geojson/muenster_ring_zeit.geojson"
    )
    assert ret.success, "process should return success"
    result = ret.stdout
    assert '"type": "Polygon"' in result
    assert '"coordinates"' in result


def test_format_geojson_explicit(script_runner):
    """Test explicitly requesting GeoJSON format"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--format",
        "geojson",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret.success, "process should return success"
    result = ret.stdout
    assert '"type": "Polygon"' in result
    assert '"coordinates"' in result


def test_format_wkt(script_runner):
    """Test WKT format output"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--format",
        "wkt",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret.success, "process should return success"
    result = ret.stdout
    assert "POLYGON((" in result
    # Check that it's not GeoJSON format
    assert '"type": "Polygon"' not in result


def test_format_wkb(script_runner):
    """Test WKB format output"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--format",
        "wkb",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret.success, "process should return success"
    result = ret.stdout.strip().split("\n")[0]  # Get first line, ignore progress bars
    # WKB should be a hex string (raw output for single files)
    assert isinstance(result, str)
    assert len(result) > 0
    # Check that it's valid hex
    try:
        bytes.fromhex(result)
    except ValueError:
        pytest.fail(f"WKB output is not valid hex: {result}")
    # Check that it's not WKT or GeoJSON format
    assert "POLYGON((" not in result
    assert '"type": "Polygon"' not in result
    assert '"bbox":' not in result


def test_format_invalid(script_runner):
    """Test invalid format parameter"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--format",
        "invalid",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert not ret.success, "process should return failure for invalid format"
    assert "invalid choice: 'invalid'" in ret.stderr


def test_format_folder_geojson(script_runner):
    """Test GeoJSON format with folder containing multiple files"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--format",
        "geojson",
        "--details",
        "tests/testdata/folders/folder_two_files",
    )
    assert ret.success, "process should return success"
    result = ret.stdout
    assert '"type": "Polygon"' in result
    assert '"coordinates"' in result


def test_format_folder_wkt(script_runner):
    """Test WKT format with folder containing multiple files"""
    ret = script_runner.run(
        "geoextent", "-b", "--format", "wkt", "tests/testdata/folders/folder_two_files"
    )
    assert ret.success, "process should return success"
    result = ret.stdout.strip().split("\n")[0]  # Get first line, ignore progress bars
    # Should output raw WKT polygon
    assert result.startswith("POLYGON((")
    assert result.endswith("))")
    # Check that it's not JSON format
    assert not result.startswith("{")
    assert '"coordinates"' not in result


def test_format_multiple_files_wkb(script_runner):
    """Test WKB format with multiple individual files"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--format",
        "wkb",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
        "tests/testdata/csv/cities_NL.csv",
    )
    assert ret.success, "process should return success"
    result = ret.stdout.strip().split("\n")[0]  # Get first line, ignore progress bars
    # Should output raw WKB hex string (merged bbox from multiple files)
    assert isinstance(result, str)
    assert len(result) > 0
    # Should be valid hex
    try:
        bytes.fromhex(result)
    except ValueError:
        pytest.fail(f"WKB output is not valid hex: {result}")
    # Check that it's not WKT or JSON format
    assert not result.startswith("POLYGON((")
    assert not result.startswith("{")
    assert '"type": "Polygon"' not in result


def test_format_wkt_exact_output(script_runner):
    """Test exact WKT output for muenster_ring_zeit.geojson"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--format",
        "wkt",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret.success, "process should return success"
    expected_wkt = "POLYGON((7.6016807556152335 51.94881477206191,7.647256851196289 51.94881477206191,7.647256851196289 51.974624029877454,7.6016807556152335 51.974624029877454,7.6016807556152335 51.94881477206191))"
    # Get only the first line (WKT output), ignore progress bar output
    actual_output = ret.stdout.strip().split("\n")[0]
    assert (
        actual_output == expected_wkt
    ), f"Expected: {expected_wkt}, Got: {actual_output}"


def test_format_wkb_exact_output(script_runner):
    """Test exact WKB output for muenster_ring_zeit.geojson"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--format",
        "wkb",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret.success, "process should return success"
    expected_wkb = "00000000030000000100000005401E681EFFFFFFFF4049F972C32FFBDA401E96CA800000004049F972C32FFBDA401E96CA800000004049FCC07AEF1C15401E681EFFFFFFFF4049FCC07AEF1C15401E681EFFFFFFFF4049F972C32FFBDA"
    # Get only the first line (WKB output), ignore progress bar output
    actual_output = ret.stdout.strip().split("\n")[0]
    assert (
        actual_output == expected_wkb
    ), f"Expected: {expected_wkb}, Got: {actual_output}"


def test_format_directory_wkt_raw_output(script_runner):
    """Test that WKT format for directories outputs raw WKT polygon"""
    ret = script_runner.run(
        "geoextent", "-b", "--format", "wkt", "tests/testdata/geojson/"
    )
    assert ret.success, "process should return success"
    result = ret.stdout.strip().split("\n")[0]  # Get first line, ignore progress bars

    # Should output raw WKT polygon, not JSON
    expected_wkt = "POLYGON((6.220493316650391 50.52150360276628,7.647256851196289 50.52150360276628,7.647256851196289 51.974624029877454,6.220493316650391 51.974624029877454,6.220493316650391 50.52150360276628))"
    assert result == expected_wkt

    # Should not be JSON format
    assert not result.startswith("{")
    assert "format" not in result
    assert "details" not in result


def test_format_directory_wkb_raw_output(script_runner):
    """Test that WKB format for directories outputs raw WKB hex string"""
    ret = script_runner.run(
        "geoextent", "-b", "--format", "wkb", "tests/testdata/geojson/"
    )
    assert ret.success, "process should return success"
    result = ret.stdout.strip().split("\n")[0]  # Get first line, ignore progress bars

    # Should output raw WKB hex string, not JSON
    assert isinstance(result, str)
    assert len(result) > 0

    # Should be valid hex
    try:
        bytes.fromhex(result)
    except ValueError:
        pytest.fail(f"WKB output is not valid hex: {result}")

    # Should not be WKT or JSON format
    assert not result.startswith("POLYGON((")
    assert not result.startswith("{")
    assert "format" not in result
    assert "details" not in result


def test_format_directory_wkt_vs_single_file(script_runner):
    """Test that directory WKT output covers larger area than single file WKT output"""
    # Get directory output
    ret_dir = script_runner.run(
        "geoextent", "-b", "--format", "wkt", "tests/testdata/geojson/"
    )
    assert ret_dir.success, "directory process should return success"
    dir_result = ret_dir.stdout.strip().split("\n")[0]

    # Get single file output
    ret_file = script_runner.run(
        "geoextent",
        "-b",
        "--format",
        "wkt",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret_file.success, "file process should return success"
    file_result = ret_file.stdout.strip().split("\n")[0]

    # Directory should output expected WKT polygon (covers all files)
    expected_dir_wkt = "POLYGON((6.220493316650391 50.52150360276628,7.647256851196289 50.52150360276628,7.647256851196289 51.974624029877454,6.220493316650391 51.974624029877454,6.220493316650391 50.52150360276628))"
    assert dir_result == expected_dir_wkt

    # Single file should output raw WKT string (smaller area)
    assert file_result.startswith("POLYGON((")
    assert file_result.endswith("))")

    # They should be different (directory covers larger area)
    assert dir_result != file_result


def test_format_directory_nested_wkt(script_runner):
    """Test WKT format with nested directory structure outputs raw WKT"""
    ret = script_runner.run(
        "geoextent", "-b", "--format", "wkt", "tests/testdata/folders"
    )
    assert ret.success, "process should return success"
    result = ret.stdout.strip().split("\n")[0]  # Get first line, ignore progress bars

    # Should output raw WKT polygon, not JSON
    assert result.startswith("POLYGON((")
    assert result.endswith("))")
    assert not result.startswith("{")
    assert "details" not in result


def test_format_directory_wkb_hex_validation(script_runner):
    """Test that WKB format outputs valid hexadecimal string"""
    ret = script_runner.run(
        "geoextent", "-b", "--format", "wkb", "tests/testdata/geojson/"
    )
    assert ret.success, "process should return success"
    result = ret.stdout.strip().split("\n")[0]  # Get first line, ignore progress bars

    # Should be valid hex string
    try:
        bytes.fromhex(result)
    except ValueError:
        pytest.fail(f"WKB output is not valid hex: {result}")

    # Should not be WKT or JSON format
    assert not result.startswith("POLYGON((")
    assert not result.startswith("{")
    assert "details" not in result


def test_quiet_mode_suppresses_progress_bars(script_runner):
    """Test that --quiet suppresses progress bars and warnings"""
    ret = script_runner.run(
        "geoextent", "-b", "--format", "wkt", "--quiet", "tests/testdata/geojson/"
    )
    assert ret.success, "process should return success"

    # Stderr should be empty (no progress bars or warnings)
    assert ret.stderr == "", "stderr should be empty in quiet mode"

    # Stdout should contain only the result
    result = ret.stdout.strip()
    assert result.startswith("POLYGON(("), "should output WKT polygon"

    # Should not contain any progress indicators or warnings
    assert "Processing" not in ret.stdout
    assert "%" not in ret.stdout
    assert "WARNING" not in ret.stdout


def test_quiet_mode_vs_normal_mode(script_runner):
    """Test that --quiet produces different output than normal mode"""
    # Normal mode
    ret_normal = script_runner.run("geoextent", "-b", "tests/testdata/geojson/")
    assert ret_normal.success, "normal process should return success"

    # Quiet mode
    ret_quiet = script_runner.run(
        "geoextent", "-b", "--quiet", "tests/testdata/geojson/"
    )
    assert ret_quiet.success, "quiet process should return success"

    # Both should have the same WKT result in stdout
    normal_result = ret_normal.stdout.strip().split("\n")[0]
    quiet_result = ret_quiet.stdout.strip()
    assert normal_result == quiet_result, "WKT results should be identical"

    # But stderr should be different (normal has progress, quiet doesn't)
    assert len(ret_normal.stderr) > 0, "normal mode should have progress output"
    assert ret_quiet.stderr == "", "quiet mode should have no stderr output"


def test_quiet_mode_suppresses_warnings(script_runner):
    """Test that --quiet suppresses warning messages"""
    # Test with a file that generates warnings
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--quiet",
        "tests/testdata/geojson/invalid_coordinate.geojson",
    )
    assert ret.success, "process should return success"

    # Should not contain WARNING messages
    assert "WARNING" not in ret.stdout
    assert "WARNING" not in ret.stderr
    assert ret.stderr == "", "stderr should be empty"

    # Should still produce valid output
    result = ret.stdout.strip()
    assert '"format": "geojson"' in result


def test_quiet_mode_enables_no_progress(script_runner):
    """Test that --quiet automatically enables --no-progress behavior"""
    ret = script_runner.run(
        "geoextent", "-b", "--quiet", "tests/testdata/folders/folder_two_files"
    )
    assert ret.success, "process should return success"

    # Should have no progress-related output
    assert "Processing" not in ret.stderr
    assert "%" not in ret.stderr
    assert "|" not in ret.stderr  # Progress bar characters
    assert ret.stderr == "", "stderr should be completely empty"


def test_quiet_mode_with_format_options(script_runner):
    """Test that --quiet works with different format options"""
    # Test with WKT
    ret_wkt = script_runner.run(
        "geoextent",
        "-b",
        "--format",
        "wkt",
        "--quiet",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret_wkt.success, "WKT quiet process should return success"
    assert ret_wkt.stderr == "", "WKT stderr should be empty"
    assert ret_wkt.stdout.strip().startswith("POLYGON(("), "should output WKT"

    # Test with WKB
    ret_wkb = script_runner.run(
        "geoextent",
        "-b",
        "--format",
        "wkb",
        "--quiet",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret_wkb.success, "WKB quiet process should return success"
    assert ret_wkb.stderr == "", "WKB stderr should be empty"
    # WKB should be hex string
    wkb_result = ret_wkb.stdout.strip()
    assert len(wkb_result) > 0 and not wkb_result.startswith(
        "POLYGON"
    ), "should output WKB hex"


def test_quiet_mode_suppresses_pandas_warnings(script_runner):
    """Test that --quiet suppresses pandas UserWarnings from date parsing"""
    # Test with a CSV file that generates pandas date parsing warnings
    ret_quiet = script_runner.run(
        "geoextent",
        "-t",
        "--quiet",
        "tests/testdata/csv/cities_NL_case5.csv",
    )
    assert ret_quiet.success, "quiet process should return success"
    assert ret_quiet.stderr == "", "stderr should be empty (no warnings)"

    # Should still have valid JSON output
    result = json.loads(ret_quiet.stdout.strip())
    assert "tbox" in result
    assert result["format"] == "csv"
    assert result["geoextent_handler"] == "handleCSV"

    # Note: In the test environment, pandas warnings might not appear in stderr
    # due to test framework behavior, but the core functionality of quiet mode
    # suppressing warnings (tested manually) works correctly


def test_debug_quiet_conflict_prioritizes_debug(script_runner):
    """Test that --debug and --quiet conflict shows critical message and prioritizes debug"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--debug",
        "--quiet",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret.success, "process should return success"

    # Should contain critical message about conflicting options
    assert "Conflicting options --debug and --quiet provided" in ret.stderr
    assert "Debug mode takes priority, quiet mode disabled" in ret.stderr

    # Should show progress bars (quiet mode disabled, debug mode active)
    assert "Processing" in ret.stderr

    # Should have JSON output (not raw format)
    assert ret.stdout.strip().startswith("{")
    assert "format" in ret.stdout


def test_debug_only_works_normally(script_runner):
    """Test that --debug alone works normally"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--debug",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret.success, "process should return success"

    # Should NOT contain critical message about conflicts
    assert "Conflicting options --debug and --quiet provided" not in ret.stderr

    # Should show progress bars (debug mode doesn't disable them)
    assert "Processing" in ret.stderr

    # Should have JSON output
    assert ret.stdout.strip().startswith("{")
    assert "format" in ret.stdout


def test_quiet_only_works_normally(script_runner):
    """Test that --quiet alone works normally"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--quiet",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret.success, "process should return success"

    # Should NOT contain critical message
    assert "CRITICAL:geoextent:Conflicting options" not in ret.stderr

    # Should be quiet (no debug, info, or progress output)
    assert "DEBUG:" not in ret.stderr
    assert "INFO:" not in ret.stderr
    assert "Processing" not in ret.stderr
    assert ret.stderr == ""


def test_convex_hull_single_file(script_runner):
    """Test convex hull calculation for a single vector file"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--convex-hull",
        "--quiet",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret.success, "process should return success"

    result = json.loads(ret.stdout.strip())
    assert "convex_hull" in result
    assert result["convex_hull"] is True
    assert "bbox" in result
    assert "crs" in result
    assert result["format"] == "geojson"
    assert result["geoextent_handler"] == "handleVector"


def test_convex_hull_directory(script_runner):
    """Test convex hull calculation for a directory of vector files"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--convex-hull",
        "--quiet",
        "tests/testdata/geojson/",
    )
    assert ret.success, "process should return success"

    result = json.loads(ret.stdout.strip())
    assert "convex_hull" in result
    assert result["convex_hull"] is True
    assert "bbox" in result
    assert "crs" in result
    assert result["format"] == "folder"


def test_convex_hull_multiple_files(script_runner):
    """Test convex hull calculation for multiple vector files"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--convex-hull",
        "--quiet",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
        "tests/testdata/geojson/kalterherbergPoint.geojson",
    )
    assert ret.success, "process should return success"

    result = json.loads(ret.stdout.strip())
    assert "convex_hull" in result
    assert result["convex_hull"] is True
    assert "bbox" in result
    assert "crs" in result
    assert result["format"] == "multiple_files"
    # Details are not included unless --details is specified


def test_convex_hull_multiple_files_with_details(script_runner):
    """Test convex hull calculation for multiple vector files with details"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--convex-hull",
        "--details",
        "--quiet",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
        "tests/testdata/geojson/kalterherbergPoint.geojson",
    )
    assert ret.success, "process should return success"

    result = json.loads(ret.stdout.strip())
    assert "convex_hull" in result
    assert result["convex_hull"] is True
    assert "bbox" in result
    assert "crs" in result
    assert result["format"] == "multiple_files"
    assert "details" in result

    # Check that individual files also have convex_hull flag
    for filename, detail in result["details"].items():
        if detail and "convex_hull" in detail:
            assert detail["convex_hull"] is True


def test_convex_hull_fallback_csv(script_runner):
    """Test that convex hull falls back to bounding box for non-vector files like CSV"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--convex-hull",
        "--quiet",
        "tests/testdata/csv/cities_NL_case5.csv",
    )
    assert ret.success, "process should return success"

    result = json.loads(ret.stdout.strip())
    # Should NOT have convex_hull flag for CSV files
    assert "convex_hull" not in result
    assert "bbox" in result
    assert "crs" in result
    assert result["format"] == "csv"
    assert result["geoextent_handler"] == "handleCSV"


def test_convex_hull_with_wkt_format(script_runner):
    """Test convex hull with WKT output format"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "--convex-hull",
        "--format",
        "wkt",
        "--quiet",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret.success, "process should return success"

    # WKT output should be raw polygon string
    result = ret.stdout.strip()
    assert result.startswith("POLYGON((")
    assert result.endswith("))")


def test_convex_hull_with_temporal_extent(script_runner):
    """Test convex hull combined with temporal extent extraction"""
    ret = script_runner.run(
        "geoextent",
        "-b",
        "-t",
        "--convex-hull",
        "--quiet",
        "tests/testdata/geojson/muenster_ring_zeit.geojson",
    )
    assert ret.success, "process should return success"

    result = json.loads(ret.stdout.strip())
    assert "convex_hull" in result
    assert result["convex_hull"] is True
    assert "bbox" in result
    assert "tbox" in result
    assert "crs" in result


def test_convex_hull_vs_gdal_direct_calculation(script_runner):
    """Test that geoextent convex hull matches direct GDAL calculation"""
    import json
    from osgeo import ogr

    test_file = "tests/testdata/geojson/ausgleichsflaechen_moers.geojson"

    # Calculate convex hull directly with GDAL
    datasource = ogr.Open(test_file)
    layer = datasource.GetLayer(0)

    # Collect all geometries
    geometries = []
    for feature in layer:
        geom = feature.GetGeometryRef()
        if geom is not None:
            geometries.append(geom.Clone())

    # Create geometry collection and calculate convex hull
    geom_collection = ogr.Geometry(ogr.wkbGeometryCollection)
    for geom in geometries:
        geom_collection.AddGeometry(geom)

    convex_hull = geom_collection.ConvexHull()

    # Get coordinates from GDAL convex hull
    gdal_coords = []
    if convex_hull.GetGeometryType() == ogr.wkbPolygon:
        ring = convex_hull.GetGeometryRef(0)
        if ring is not None:
            point_count = ring.GetPointCount()
            for i in range(point_count):
                x, y, z = ring.GetPoint(i)
                gdal_coords.append([x, y])

    # Get convex hull from geoextent
    ret = script_runner.run("geoextent", "-b", "--convex-hull", "--quiet", test_file)
    assert ret.success, "geoextent should return success"

    geoextent_result = json.loads(ret.stdout.strip())

    # New FeatureCollection format
    assert (
        geoextent_result["type"] == "FeatureCollection"
    ), "should be a FeatureCollection"
    assert len(geoextent_result["features"]) == 1, "should have exactly one feature"

    feature = geoextent_result["features"][0]
    assert (
        feature["properties"]["convex_hull"] is True
    ), "should have convex hull flag in properties"

    # Extract coordinates from geoextent result
    geoextent_coords = feature["geometry"]["coordinates"][0]

    # Both should have the same number of points
    assert len(gdal_coords) == len(
        geoextent_coords
    ), f"Point counts should match: GDAL={len(gdal_coords)}, geoextent={len(geoextent_coords)}"

    # Coordinates should be very close (allowing for floating point precision)
    for i, (gdal_point, geoextent_point) in enumerate(
        zip(gdal_coords, geoextent_coords)
    ):
        assert (
            abs(gdal_point[0] - geoextent_point[0]) < 1e-10
        ), f"X coordinates should match at point {i}: GDAL={gdal_point[0]}, geoextent={geoextent_point[0]}"
        assert (
            abs(gdal_point[1] - geoextent_point[1]) < 1e-10
        ), f"Y coordinates should match at point {i}: GDAL={gdal_point[1]}, geoextent={geoextent_point[1]}"

    datasource = None  # Close datasource


def test_convex_hull_ausgleichsflaechen_moers_baseline(script_runner):
    """Integration test: Compare convex hull output for ausgleichsflaechen_moers.geojson against known baseline"""
    # Known baseline geometry for ausgleichsflaechen_moers.geojson convex hull
    expected_geometry = {
        "type": "Polygon",
        "coordinates": [
            [
                [6.622876570001159, 51.422305272549615],
                [6.59839841092796, 51.43605055141643],
                [6.598390453361757, 51.43606234977576],
                [6.598348865120752, 51.43612822971935],
                [6.597888191190831, 51.437157814826875],
                [6.59663465544554, 51.45390080555728],
                [6.600415284426673, 51.47441889630804],
                [6.62234874263546, 51.486636388722296],
                [6.627926433576252, 51.48620034107534],
                [6.66283120774708, 51.456988298214974],
                [6.662839251596646, 51.45675480848453],
                [6.624742777588445, 51.42351615293587],
                [6.62460862066547, 51.4234290734008],
                [6.623923921225536, 51.422984757324166],
                [6.622876570001159, 51.422305272549615],
            ]
        ],
    }

    test_file = "tests/testdata/geojson/ausgleichsflaechen_moers.geojson"

    # Get convex hull from geoextent
    ret = script_runner.run("geoextent", "-b", "--convex-hull", "--quiet", test_file)
    assert ret.success, "geoextent should return success"

    geoextent_result = json.loads(ret.stdout.strip())

    # New FeatureCollection format
    assert "type" in geoextent_result, "should have type"
    assert (
        geoextent_result["type"] == "FeatureCollection"
    ), "should be a FeatureCollection"
    assert "features" in geoextent_result, "should have features"
    assert len(geoextent_result["features"]) == 1, "should have exactly one feature"

    feature = geoextent_result["features"][0]
    assert "geometry" in feature, "feature should have geometry"
    assert "properties" in feature, "feature should have properties"
    assert (
        feature["properties"]["convex_hull"] is True
    ), "should have convex hull flag in properties"

    # Extract geometry from geoextent result
    actual_geometry = feature["geometry"]

    # Verify the geometry structure matches
    assert (
        actual_geometry["type"] == expected_geometry["type"]
    ), "geometry type should match"
    assert len(actual_geometry["coordinates"]) == len(
        expected_geometry["coordinates"]
    ), "coordinate structure should match"

    # Get coordinate arrays for comparison
    actual_coords = actual_geometry["coordinates"][0]
    expected_coords = expected_geometry["coordinates"][0]

    # Both should have the same number of points
    assert len(actual_coords) == len(
        expected_coords
    ), f"Point counts should match: expected={len(expected_coords)}, actual={len(actual_coords)}"

    # Coordinates should match exactly (or very close for floating point precision)
    for i, (expected_point, actual_point) in enumerate(
        zip(expected_coords, actual_coords)
    ):
        assert (
            abs(expected_point[0] - actual_point[0]) < 1e-10
        ), f"X coordinates should match at point {i}: expected={expected_point[0]}, actual={actual_point[0]}"
        assert (
            abs(expected_point[1] - actual_point[1]) < 1e-10
        ), f"Y coordinates should match at point {i}: expected={expected_point[1]}, actual={actual_point[1]}"


def test_geojsonio_option_with_bbox(script_runner):
    """Test --geojsonio option outputs a URL when bbox is extracted"""
    ret = script_runner.run(
        [
            "geoextent",
            "-b",
            "--geojsonio",
            "--quiet",
            "tests/testdata/geojson/muenster_ring_zeit.geojson",
        ]
    )
    assert ret.success, "process should return success"
    # Progress bars go to stderr but with --quiet they should be suppressed
    if ret.stderr:
        # Allow for any progress bar artifacts but shouldn't have errors
        assert (
            "error" not in ret.stderr.lower()
        ), f"stderr should not contain errors: {ret.stderr}"

    lines = ret.stdout.strip().split("\n")
    # Check that JSON output is present
    assert len(lines) >= 2, "should have JSON output and geojsonio URL"

    # Parse the JSON output (should be on first line)
    json_output = json.loads(lines[0])
    # Check that it's a FeatureCollection (new GeoJSON format)
    assert (
        json_output.get("type") == "FeatureCollection"
    ), "should be a FeatureCollection"
    assert len(json_output.get("features", [])) > 0, "should have features"
    assert json_output["features"][0].get("geometry"), "should have geometry"

    # Check for geojsonio URL in output
    geojsonio_line = None
    for line in lines[1:]:
        if "geojson.io" in line:
            geojsonio_line = line
            break

    assert geojsonio_line is not None, "should contain geojsonio URL"
    assert (
        "🌍 View spatial extent at: http" in geojsonio_line
    ), "should have clickable URL message"
    assert "geojson.io" in geojsonio_line, "URL should point to geojson.io"


def test_geojsonio_option_with_different_formats(script_runner):
    """Test --geojsonio option works with different output formats (WKT, WKB)"""
    # Test with WKT format
    ret = script_runner.run(
        [
            "geoextent",
            "-b",
            "--format",
            "wkt",
            "--geojsonio",
            "--quiet",
            "tests/testdata/geojson/muenster_ring_zeit.geojson",
        ]
    )
    assert ret.success, "process should return success"

    lines = ret.stdout.strip().split("\n")
    # First line should be WKT output
    assert lines[0].startswith("POLYGON"), "first line should be WKT format"

    # Should still have geojsonio URL
    geojsonio_line = None
    for line in lines[1:]:
        if "geojson.io" in line:
            geojsonio_line = line
            break

    assert (
        geojsonio_line is not None
    ), "should contain geojsonio URL even with WKT format"


def test_geojsonio_option_no_bbox(script_runner):
    """Test --geojsonio option with no bbox extraction"""
    ret = script_runner.run(
        [
            "geoextent",
            "-t",
            "--geojsonio",
            "--quiet",
            "tests/testdata/geojson/muenster_ring_zeit.geojson",
        ]
    )
    assert ret.success, "process should return success"

    lines = ret.stdout.strip().split("\n")
    # Should not have geojsonio URL since no bbox was extracted
    geojsonio_found = any("geojson.io" in line for line in lines)
    assert (
        not geojsonio_found
    ), "should not have geojsonio URL when no bbox is extracted"


def test_geojsonio_option_with_convex_hull(script_runner):
    """Test --geojsonio option works with convex hull"""
    ret = script_runner.run(
        [
            "geoextent",
            "-b",
            "--convex-hull",
            "--geojsonio",
            "--quiet",
            "tests/testdata/geojson/muenster_ring_zeit.geojson",
        ]
    )
    assert ret.success, "process should return success"

    lines = ret.stdout.strip().split("\n")
    # Check that JSON output is present
    json_output = json.loads(lines[0])
    # Check that it's a FeatureCollection (new GeoJSON format)
    assert (
        json_output.get("type") == "FeatureCollection"
    ), "should be a FeatureCollection"
    assert len(json_output.get("features", [])) > 0, "should have features"
    # Check that it's marked as convex hull
    feature = json_output["features"][0]
    assert (
        feature.get("properties", {}).get("convex_hull") is True
    ), "should be marked as convex hull"

    # Check for geojsonio URL
    geojsonio_line = None
    for line in lines[1:]:
        if "geojson.io" in line:
            geojsonio_line = line
            break

    assert geojsonio_line is not None, "should contain geojsonio URL for convex hull"


def test_geojsonio_option_quiet_mode(script_runner):
    """Test --geojsonio option in quiet mode"""
    ret = script_runner.run(
        [
            "geoextent",
            "-b",
            "--geojsonio",
            "--quiet",
            "tests/testdata/geojson/muenster_ring_zeit.geojson",
        ]
    )
    assert ret.success, "process should return success"

    lines = ret.stdout.strip().split("\n")
    # In quiet mode, should still have geojsonio URL (it's not a warning, it's requested output)
    geojsonio_line = None
    for line in lines:
        if "geojson.io" in line:
            geojsonio_line = line
            break

    assert geojsonio_line is not None, "should contain geojsonio URL even in quiet mode"


def test_browse_option_with_bbox(script_runner, monkeypatch):
    """Test --browse option opens URL in browser when bbox is extracted (without printing URL)"""
    # Mock webbrowser.open to prevent actually opening a browser
    browser_opened = []

    def mock_open(url):
        browser_opened.append(url)
        return True

    import webbrowser

    monkeypatch.setattr(webbrowser, "open", mock_open)

    ret = script_runner.run(
        [
            "geoextent",
            "-b",
            "--browse",
            "--quiet",
            "tests/testdata/geojson/muenster_ring_zeit.geojson",
        ]
    )
    assert ret.success, "process should return success"

    lines = ret.stdout.strip().split("\n")
    # Check that JSON output is present
    json_output = json.loads(lines[0])
    assert (
        json_output.get("type") == "FeatureCollection"
    ), "should be a FeatureCollection"

    # --browse without --geojsonio should NOT print the URL
    geojsonio_line = None
    for line in lines:
        if "geojson.io" in line:
            geojsonio_line = line
            break

    assert (
        geojsonio_line is None
    ), "should NOT print geojsonio URL without --geojsonio flag"

    # Verify that browser was opened
    assert len(browser_opened) == 1, "browser should have been opened once"
    assert "geojson.io" in browser_opened[0], "should open geojson.io URL"


def test_browse_option_with_geojsonio(script_runner, monkeypatch):
    """Test --browse with --geojsonio both set - URL printed then opened"""
    browser_opened = []

    def mock_open(url):
        browser_opened.append(url)
        return True

    import webbrowser

    monkeypatch.setattr(webbrowser, "open", mock_open)

    ret = script_runner.run(
        [
            "geoextent",
            "-b",
            "--geojsonio",
            "--browse",
            "--quiet",
            "tests/testdata/geojson/muenster_ring_zeit.geojson",
        ]
    )
    assert ret.success, "process should return success"

    lines = ret.stdout.strip().split("\n")

    # Should have geojsonio URL in output
    geojsonio_line = None
    for line in lines:
        if "geojson.io" in line:
            geojsonio_line = line
            break

    assert geojsonio_line is not None, "should contain geojsonio URL"

    # Verify that browser was opened
    assert len(browser_opened) == 1, "browser should have been opened once"
    assert "geojson.io" in browser_opened[0]


def test_browse_option_no_bbox(script_runner, monkeypatch):
    """Test --browse option with no bbox extraction"""
    browser_opened = []

    def mock_open(url):
        browser_opened.append(url)
        return True

    import webbrowser

    monkeypatch.setattr(webbrowser, "open", mock_open)

    ret = script_runner.run(
        [
            "geoextent",
            "-t",
            "--browse",
            "--quiet",
            "tests/testdata/geojson/muenster_ring_zeit.geojson",
        ]
    )
    assert ret.success, "process should return success"

    # Should not have geojsonio URL since no bbox was extracted
    lines = ret.stdout.strip().split("\n")
    geojsonio_found = any("geojson.io" in line for line in lines)
    assert (
        not geojsonio_found
    ), "should not have geojsonio URL when no bbox is extracted"

    # Browser should not have been opened
    assert len(browser_opened) == 0, "browser should not have been opened without bbox"


def test_browse_option_with_different_formats(script_runner, monkeypatch):
    """Test --browse option works with different output formats (WKT, WKB) without printing URL"""
    browser_opened = []

    def mock_open(url):
        browser_opened.append(url)
        return True

    import webbrowser

    monkeypatch.setattr(webbrowser, "open", mock_open)

    ret = script_runner.run(
        [
            "geoextent",
            "-b",
            "--format",
            "wkt",
            "--browse",
            "--quiet",
            "tests/testdata/geojson/muenster_ring_zeit.geojson",
        ]
    )
    assert ret.success, "process should return success"

    lines = ret.stdout.strip().split("\n")
    # First line should be WKT output
    assert lines[0].startswith("POLYGON"), "first line should be WKT format"

    # --browse without --geojsonio should NOT print the URL
    geojsonio_line = None
    for line in lines[1:]:
        if "geojson.io" in line:
            geojsonio_line = line
            break

    assert (
        geojsonio_line is None
    ), "should NOT print geojsonio URL without --geojsonio flag"

    # Browser should have been opened
    assert len(browser_opened) == 1, "browser should have been opened"
    assert "geojson.io" in browser_opened[0]
