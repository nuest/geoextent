#!/usr/bin/env python3
"""Generate synthetic raster test files for temporal extent testing.

Creates GeoTIFF and NetCDF files with various temporal metadata configurations.
All rasters are 10x10 pixels, single-band Float32, WGS84, 0.1 deg pixel size.

Usage:
    .venv/bin/python tests/scripts/generate_raster_temporal_testdata.py
"""

import os
import numpy as np
from osgeo import gdal, osr
import netCDF4


TIF_DIR = "tests/testdata/tif"
NC_DIR = "tests/testdata/nc"


def _make_geotiff(
    filename, origin_lon, origin_lat, metadata=None, band_imagery_metadata=None
):
    """Create a minimal 10x10 WGS84 GeoTIFF."""
    filepath = os.path.join(TIF_DIR, filename)
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(filepath, 10, 10, 1, gdal.GDT_Float32)
    ds.SetGeoTransform([origin_lon, 0.1, 0, origin_lat, 0, -0.1])

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    ds.SetProjection(srs.ExportToWkt())

    band = ds.GetRasterBand(1)
    band.WriteArray(np.ones((10, 10), dtype=np.float32))

    if metadata:
        for key, value in metadata.items():
            ds.SetMetadataItem(key, value)

    if band_imagery_metadata:
        for key, value in band_imagery_metadata.items():
            band.SetMetadataItem(key, value, "IMAGERY")

    ds.FlushCache()
    ds = None
    print(f"  Created {filepath}")


def _make_netcdf(
    filename,
    origin_lon,
    origin_lat,
    time_units=None,
    time_values=None,
    acdd_start=None,
    acdd_end=None,
):
    """Create a minimal 10x10 WGS84 NetCDF with optional CF time and/or ACDD attributes."""
    filepath = os.path.join(NC_DIR, filename)

    ds = netCDF4.Dataset(filepath, "w", format="NETCDF4_CLASSIC")

    # Create spatial dimensions
    lats = np.arange(origin_lat, origin_lat + 1.0, 0.1)
    lons = np.arange(origin_lon, origin_lon + 1.0, 0.1)

    ds.createDimension("lat", len(lats))
    ds.createDimension("lon", len(lons))

    lat_var = ds.createVariable("lat", "f4", ("lat",))
    lat_var.units = "degrees_north"
    lat_var.standard_name = "latitude"
    lat_var[:] = lats

    lon_var = ds.createVariable("lon", "f4", ("lon",))
    lon_var.units = "degrees_east"
    lon_var.standard_name = "longitude"
    lon_var[:] = lons

    # CRS metadata via grid_mapping
    crs_var = ds.createVariable("crs", "i4")
    crs_var.grid_mapping_name = "latitude_longitude"
    crs_var.semi_major_axis = 6378137.0
    crs_var.inverse_flattening = 298.257223563

    if time_values is not None:
        ds.createDimension("time", len(time_values))
        time_var = ds.createVariable("time", "f8", ("time",))
        if time_units:
            time_var.units = time_units
        time_var.calendar = "standard"
        time_var[:] = np.array(time_values, dtype=np.float64)

        data_var = ds.createVariable("data", "f4", ("time", "lat", "lon"))
        data_var.grid_mapping = "crs"
        data_var[:] = np.ones(
            (len(time_values), len(lats), len(lons)), dtype=np.float32
        )
    else:
        data_var = ds.createVariable("data", "f4", ("lat", "lon"))
        data_var.grid_mapping = "crs"
        data_var[:] = np.ones((len(lats), len(lons)), dtype=np.float32)

    # ACDD global attributes
    if acdd_start:
        ds.time_coverage_start = acdd_start
    if acdd_end:
        ds.time_coverage_end = acdd_end

    ds.Conventions = "CF-1.6"

    ds.close()
    print(f"  Created {filepath}")


def generate_geotiffs():
    print("Generating GeoTIFF test files...")

    # 1. TIFFTAG_DATETIME
    _make_geotiff(
        "tif_tifftag_datetime.tif",
        35.0,
        -1.0,
        metadata={"TIFFTAG_DATETIME": "2019:03:21 08:15:00"},
    )

    # 2. ACQUISITIONDATETIME (IMAGERY domain)
    _make_geotiff(
        "tif_acq_datetime.tif",
        -73.5,
        4.0,
        band_imagery_metadata={"ACQUISITIONDATETIME": "2024-07-04T14:30:00Z"},
    )

    # 3. Invalid TIFFTAG_DATETIME
    _make_geotiff(
        "tif_tifftag_invalid.tif",
        10.0,
        48.0,
        metadata={"TIFFTAG_DATETIME": "not-a-valid-date"},
    )

    # 4. Empty TIFFTAG_DATETIME
    _make_geotiff(
        "tif_tifftag_empty.tif", -43.0, -22.5, metadata={"TIFFTAG_DATETIME": ""}
    )

    # 5. No temporal metadata
    _make_geotiff("tif_no_temporal.tif", 12.0, 55.5)

    # 6. Both TIFFTAG and ACQUISITIONDATETIME
    _make_geotiff(
        "tif_both_tifftag_and_acq.tif",
        115.0,
        -8.0,
        metadata={"TIFFTAG_DATETIME": "2020:01:15 00:00:00"},
        band_imagery_metadata={"ACQUISITIONDATETIME": "2020-06-30T12:00:00Z"},
    )

    # 7. Invalid ACQUISITIONDATETIME
    _make_geotiff(
        "tif_acq_invalid.tif",
        25.0,
        60.0,
        band_imagery_metadata={"ACQUISITIONDATETIME": "garbage"},
    )


def generate_netcdfs():
    print("Generating NetCDF test files...")

    # 1. CF days since
    _make_netcdf(
        "nc_days_since.nc",
        10.0,
        47.0,
        time_units="days since 2015-01-01",
        time_values=[0, 365],
    )

    # 2. CF seconds since
    _make_netcdf(
        "nc_seconds_since.nc",
        126.5,
        37.0,
        time_units="seconds since 2000-06-01 00:00:00",
        time_values=[0, 86400],
    )

    # 3. CF minutes since
    _make_netcdf(
        "nc_minutes_since.nc",
        -3.5,
        40.0,
        time_units="minutes since 2010-12-25 06:00:00",
        time_values=[0, 1440],
    )

    # 4. ACDD coverage (no CF time dim)
    _make_netcdf(
        "nc_acdd_coverage.nc",
        -120.0,
        37.0,
        acdd_start="2018-04-01T00:00:00Z",
        acdd_end="2018-09-30T23:59:59Z",
    )

    # 5. ACDD start only
    _make_netcdf(
        "nc_acdd_start_only.nc", 151.0, -33.5, acdd_start="2022-11-15T00:00:00Z"
    )

    # 6. CF + ACDD both present (CF should win)
    _make_netcdf(
        "nc_cf_and_acdd.nc",
        18.0,
        59.0,
        time_units="hours since 2005-01-01",
        time_values=[0, 8760],
        acdd_start="2005-01-01T00:00:00Z",
        acdd_end="2006-01-01T00:00:00Z",
    )

    # 7. Invalid time units + ACDD fallback
    _make_netcdf(
        "nc_invalid_time_units.nc",
        100.0,
        13.5,
        time_units="not a valid string",
        time_values=[0, 1],
        acdd_start="2019-01-01T00:00:00Z",
    )

    # 8. No temporal metadata
    _make_netcdf("nc_no_temporal.nc", 28.0, -25.5)

    # 9. NaN in time values
    _make_netcdf(
        "nc_nan_time_values.nc",
        -58.0,
        -34.5,
        time_units="days since 2020-01-01",
        time_values=[float("nan"), 10, float("nan"), 30],
    )


if __name__ == "__main__":
    os.makedirs(TIF_DIR, exist_ok=True)
    os.makedirs(NC_DIR, exist_ok=True)
    generate_geotiffs()
    generate_netcdfs()
    print("Done!")
