"""Comprehensive tests for raster temporal extent extraction.

Covers all supported metadata sources:
- GeoTIFF TIFFTAG_DATETIME
- Band-level ACQUISITIONDATETIME (IMAGERY domain)
- NetCDF CF time dimensions (various unit types)
- ACDD global attributes (time_coverage_start/end)
- NaN filtering, invalid values, and fallback chain priority
"""

import logging
import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance


class TestGeoTIFFTemporalExtent:
    """Tests for GeoTIFF temporal metadata extraction."""

    def test_tifftag_datetime(self):
        result = geoextent.fromFile(
            "tests/testdata/tif/tif_tifftag_datetime.tif", tbox=True
        )
        assert result["tbox"] == ["2019-03-21", "2019-03-21"]

    def test_acquisition_datetime(self):
        result = geoextent.fromFile(
            "tests/testdata/tif/tif_acq_datetime.tif", tbox=True
        )
        assert result["tbox"] == ["2024-07-04", "2024-07-04"]

    def test_tifftag_invalid_returns_none(self):
        result = geoextent.fromFile(
            "tests/testdata/tif/tif_tifftag_invalid.tif", tbox=True
        )
        assert "tbox" not in result

    def test_tifftag_empty_returns_none(self):
        result = geoextent.fromFile(
            "tests/testdata/tif/tif_tifftag_empty.tif", tbox=True
        )
        assert "tbox" not in result

    def test_no_temporal_metadata(self):
        result = geoextent.fromFile("tests/testdata/tif/tif_no_temporal.tif", tbox=True)
        assert "tbox" not in result

    def test_tifftag_priority_over_acquisition(self):
        result = geoextent.fromFile(
            "tests/testdata/tif/tif_both_tifftag_and_acq.tif", tbox=True
        )
        assert result["tbox"] == ["2020-01-15", "2020-01-15"]

    def test_acquisition_invalid_returns_none(self):
        result = geoextent.fromFile("tests/testdata/tif/tif_acq_invalid.tif", tbox=True)
        assert "tbox" not in result

    def test_tifftag_datetime_iso8601(self):
        result = geoextent.fromFile(
            "tests/testdata/tif/tif_tifftag_datetime.tif",
            tbox=True,
            time_format="iso8601",
        )
        assert result["tbox"] == ["2019-03-21T08:15:00Z", "2019-03-21T08:15:00Z"]

    def test_tifftag_bbox_and_tbox(self):
        result = geoextent.fromFile(
            "tests/testdata/tif/tif_tifftag_datetime.tif", bbox=True, tbox=True
        )
        assert "bbox" in result
        assert "tbox" in result
        assert result["tbox"] == ["2019-03-21", "2019-03-21"]


class TestNetCDFTemporalExtent:
    """Tests for NetCDF temporal metadata extraction."""

    def test_cf_days_since(self):
        result = geoextent.fromFile("tests/testdata/nc/nc_days_since.nc", tbox=True)
        assert result["tbox"] == ["2015-01-01", "2016-01-01"]

    def test_cf_seconds_since(self):
        result = geoextent.fromFile("tests/testdata/nc/nc_seconds_since.nc", tbox=True)
        assert result["tbox"] == ["2000-06-01", "2000-06-02"]

    def test_cf_minutes_since(self):
        result = geoextent.fromFile("tests/testdata/nc/nc_minutes_since.nc", tbox=True)
        assert result["tbox"] == ["2010-12-25", "2010-12-26"]

    def test_acdd_coverage(self):
        result = geoextent.fromFile("tests/testdata/nc/nc_acdd_coverage.nc", tbox=True)
        assert result["tbox"] == ["2018-04-01", "2018-09-30"]

    def test_acdd_start_only(self):
        result = geoextent.fromFile(
            "tests/testdata/nc/nc_acdd_start_only.nc", tbox=True
        )
        assert result["tbox"] == ["2022-11-15", "2022-11-15"]

    def test_cf_priority_over_acdd(self):
        result = geoextent.fromFile("tests/testdata/nc/nc_cf_and_acdd.nc", tbox=True)
        assert result["tbox"] == ["2005-01-01", "2006-01-01"]

    def test_invalid_units_fallback_acdd(self):
        result = geoextent.fromFile(
            "tests/testdata/nc/nc_invalid_time_units.nc", tbox=True
        )
        assert result["tbox"] == ["2019-01-01", "2019-01-01"]

    def test_no_temporal_metadata(self):
        result = geoextent.fromFile("tests/testdata/nc/nc_no_temporal.nc", tbox=True)
        assert "tbox" not in result

    def test_nan_time_values_filtered(self):
        result = geoextent.fromFile(
            "tests/testdata/nc/nc_nan_time_values.nc", tbox=True
        )
        assert result["tbox"] == ["2020-01-11", "2020-01-31"]


class TestRasterTemporalErrorHandling:
    """Tests for error handling: invalid metadata still returns bbox."""

    def test_invalid_tifftag_still_returns_bbox(self):
        result = geoextent.fromFile(
            "tests/testdata/tif/tif_tifftag_invalid.tif", bbox=True, tbox=True
        )
        assert "bbox" in result
        assert "tbox" not in result

    def test_invalid_tifftag_logs_debug(self, caplog):
        with caplog.at_level(logging.DEBUG, logger="geoextent"):
            geoextent.fromFile("tests/testdata/tif/tif_tifftag_invalid.tif", tbox=True)
        assert any(
            "Cannot parse TIFFTAG_DATETIME" in msg for msg in caplog.messages
        ), f"Expected debug log about unparseable TIFFTAG_DATETIME, got: {caplog.messages}"

    def test_invalid_acq_still_returns_bbox(self):
        result = geoextent.fromFile(
            "tests/testdata/tif/tif_acq_invalid.tif", bbox=True, tbox=True
        )
        assert "bbox" in result
        assert "tbox" not in result

    def test_nc_no_temporal_still_returns_bbox(self):
        result = geoextent.fromFile(
            "tests/testdata/nc/nc_no_temporal.nc", bbox=True, tbox=True
        )
        assert "bbox" in result
        assert "tbox" not in result
