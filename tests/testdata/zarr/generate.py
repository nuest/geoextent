#!/usr/bin/env python3
"""Generate synthetic Zarr test datasets using GDAL.

Run once to create test data committed to the repository:
    .venv/bin/python tests/testdata/zarr/generate.py
"""

import os
import shutil
import numpy as np
from osgeo import gdal, osr

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def create_zarr(name, srs_epsg, zarr_format, gt, nx=10, ny=10):
    """Create a small Zarr raster dataset.

    Parameters
    ----------
    name : str
        Output directory name (e.g. "wgs84_v2.zarr").
    srs_epsg : int or None
        EPSG code for CRS, or None for no CRS.
    zarr_format : str
        "ZARR_V2" or "ZARR_V3".
    gt : tuple
        GDAL GeoTransform (origin_x, pixel_width, 0, origin_y, 0, -pixel_height).
    nx, ny : int
        Raster dimensions.
    """
    out_path = os.path.join(SCRIPT_DIR, name)
    if os.path.exists(out_path):
        shutil.rmtree(out_path)

    drv = gdal.GetDriverByName("Zarr")
    ds = drv.Create(
        out_path, nx, ny, 1, gdal.GDT_Float32, options=[f"FORMAT={zarr_format}"]
    )
    ds.SetGeoTransform(gt)

    if srs_epsg is not None:
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(srs_epsg)
        # Use traditional GIS order (lon, lat) so GeoTransform X=lon, Y=lat
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        ds.SetSpatialRef(srs)

    band = ds.GetRasterBand(1)
    data = np.arange(nx * ny, dtype=np.float32).reshape(ny, nx)
    band.WriteArray(data)
    band.SetNoDataValue(-9999.0)
    band.FlushCache()
    ds = None

    print(f"Created {out_path}")


def main():
    # 1. WGS84, Zarr V2 — Muenster area (lon 7-8, lat 51-52)
    create_zarr(
        "wgs84_v2.zarr",
        srs_epsg=4326,
        zarr_format="ZARR_V2",
        gt=(7.0, 0.1, 0.0, 52.0, 0.0, -0.1),
    )

    # 2. UTM 32N, Zarr V2 — projected CRS (easting 380000-390000, northing 5750000-5760000)
    create_zarr(
        "utm32n_v2.zarr",
        srs_epsg=32632,
        zarr_format="ZARR_V2",
        gt=(380000.0, 1000.0, 0.0, 5760000.0, 0.0, -1000.0),
    )

    # 3. WGS84, Zarr V3
    create_zarr(
        "wgs84_v3.zarr",
        srs_epsg=4326,
        zarr_format="ZARR_V3",
        gt=(7.0, 0.1, 0.0, 52.0, 0.0, -0.1),
    )

    # 4. No CRS, Zarr V2 — pixel coordinates outside WGS84 bounds, should be rejected
    create_zarr(
        "no_crs_v2.zarr",
        srs_epsg=None,
        zarr_format="ZARR_V2",
        gt=(0.0, 100.0, 0.0, 10000.0, 0.0, -100.0),
    )


if __name__ == "__main__":
    main()
