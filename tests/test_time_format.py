"""Tests for the --time-format / time_format feature.

Covers:
- resolve_time_format() utility function
- API integration via fromFile() with different handlers
- Directory extraction with time_format
- CLI argument parsing and validation
"""

import subprocess
import sys

import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.helpfunctions import resolve_time_format


class TestResolveTimeFormat:
    """Unit tests for resolve_time_format()."""

    def test_none_returns_default(self):
        assert resolve_time_format(None) == "%Y-%m-%d"

    def test_date_preset(self):
        assert resolve_time_format("date") == "%Y-%m-%d"

    def test_iso8601_preset(self):
        assert resolve_time_format("iso8601") == "%Y-%m-%dT%H:%M:%SZ"

    def test_custom_strftime(self):
        assert resolve_time_format("%Y/%m/%d") == "%Y/%m/%d"

    def test_custom_strftime_with_time(self):
        assert resolve_time_format("%d.%m.%Y %H:%M") == "%d.%m.%Y %H:%M"

    def test_invalid_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown time format"):
            resolve_time_format("bogus")

    def test_string_without_percent_raises(self):
        with pytest.raises(ValueError, match="Unknown time format"):
            resolve_time_format("nope")


class TestTimeFormatAPI:
    """Integration tests for time_format parameter in API functions."""

    def test_geotiff_default(self):
        result = geoextent.fromFile(
            "tests/testdata/tif/tif_tifftag_datetime.tif", tbox=True
        )
        assert result["tbox"] == ["2019-03-21", "2019-03-21"]

    def test_geotiff_iso8601(self):
        result = geoextent.fromFile(
            "tests/testdata/tif/tif_tifftag_datetime.tif",
            tbox=True,
            time_format="iso8601",
        )
        assert result["tbox"] == ["2019-03-21T08:15:00Z", "2019-03-21T08:15:00Z"]

    def test_geotiff_custom_format(self):
        result = geoextent.fromFile(
            "tests/testdata/tif/tif_tifftag_datetime.tif",
            tbox=True,
            time_format="%d.%m.%Y %H:%M",
        )
        assert result["tbox"] == ["21.03.2019 08:15", "21.03.2019 08:15"]

    def test_netcdf_iso8601(self):
        result = geoextent.fromFile(
            "tests/testdata/nc/nc_days_since.nc",
            tbox=True,
            time_format="iso8601",
        )
        assert result["tbox"] == ["2015-01-01T00:00:00Z", "2016-01-01T00:00:00Z"]

    def test_vector_iso8601(self):
        result = geoextent.fromFile(
            "tests/testdata/folders/folder_one_file/muenster_ring_zeit.geojson",
            tbox=True,
            time_format="iso8601",
        )
        assert result["tbox"] is not None
        assert "T" in result["tbox"][0]
        assert result["tbox"][0].endswith("Z")

    def test_csv_iso8601(self):
        result = geoextent.fromFile(
            "tests/testdata/csv/cities_NL.csv",
            tbox=True,
            time_format="iso8601",
        )
        assert result["tbox"] is not None
        assert "T" in result["tbox"][0]
        assert result["tbox"][0].endswith("Z")

    def test_geotiff_date_preset_same_as_default(self):
        default = geoextent.fromFile(
            "tests/testdata/tif/tif_tifftag_datetime.tif", tbox=True
        )
        explicit = geoextent.fromFile(
            "tests/testdata/tif/tif_tifftag_datetime.tif",
            tbox=True,
            time_format="date",
        )
        assert default["tbox"] == explicit["tbox"]


class TestTimeFormatDirectory:
    """Tests for time_format in directory extraction."""

    def test_directory_with_time_format(self):
        result = geoextent.fromDirectory(
            "tests/testdata/folders/folder_one_file",
            bbox=True,
            tbox=True,
            time_format="iso8601",
        )
        assert result.get("tbox") is not None
        assert "T" in result["tbox"][0]
        assert result["tbox"][0].endswith("Z")


class TestTimeFormatCLI:
    """Tests for --time-format CLI argument."""

    def test_cli_time_format_iso8601(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "geoextent",
                "-t",
                "--time-format",
                "iso8601",
                "tests/testdata/tif/tif_tifftag_datetime.tif",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "2019-03-21T08:15:00Z" in result.stdout

    def test_cli_time_format_custom(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "geoextent",
                "-t",
                "--time-format",
                "%Y/%m/%d",
                "tests/testdata/tif/tif_tifftag_datetime.tif",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "2019/03/21" in result.stdout

    def test_cli_time_format_invalid(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "geoextent",
                "-t",
                "--time-format",
                "bogus",
                "tests/testdata/tif/tif_tifftag_datetime.tif",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
