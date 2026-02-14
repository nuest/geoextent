import geoextent.lib.extent as geoextent
from help_functions_test import tolerance
import pytest


def test_geotiff_extract_bbox():
    result = geoextent.fromFile("tests/testdata/tif/wf_100m_klas.tif", bbox=True)
    assert "bbox" in result
    assert "crs" in result
    assert result["bbox"] == pytest.approx(
        [50.310251, 5.915300, 52.530775, 9.468398], abs=tolerance
    )
    assert result["crs"] == "4326"


def test_geotiff_extract_time():
    result = geoextent.fromFile("tests/testdata/tif/wf_100m_klas.tif", tbox=True)
    assert "temporal_extent" not in result


def test_geotiff_crs_used():
    result = geoextent.fromFile("tests/testdata/tif/wf_100m_klas.tif", bbox=True)
    assert "crs" in result
    assert result["crs"] == "4326"


def test_ungeoreferenced_raster_skipped_by_default():
    """Test that raster files with pixel-based coordinates are skipped.

    A GeoTIFF without CRS and with pixel coordinates (0, 0, 500, 500)
    which are outside valid WGS84 bounds should be rejected.
    """
    import tempfile
    import os
    import numpy as np
    from osgeo import gdal

    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as f:
        tmp_path = f.name

    try:
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(tmp_path, 500, 500, 1, gdal.GDT_Byte)
        # Default geotransform: (0, 1, 0, 0, 0, 1) → pixel coordinates [0, 0, 500, 500]
        # These exceed WGS84 bounds and should be rejected
        ds.GetRasterBand(1).WriteArray(np.zeros((500, 500), dtype=np.uint8))
        ds = None

        result = geoextent.fromFile(tmp_path, bbox=True)
        # Should return no bbox since pixel coords are outside WGS84 bounds
        assert result is None or "bbox" not in result
    finally:
        os.unlink(tmp_path)


def test_ungeoreferenced_raster_with_assume_wgs84():
    """Test that --assume-wgs84 forces WGS84 interpretation of ungeoreferenced rasters."""
    import tempfile
    import os
    import numpy as np
    from osgeo import gdal

    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as f:
        tmp_path = f.name

    try:
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(tmp_path, 10, 10, 1, gdal.GDT_Byte)
        # Set geotransform with coordinates in valid WGS84 bounds (lon 10-11, lat 50-51)
        ds.SetGeoTransform([10.0, 0.1, 0, 51.0, 0, -0.1])
        # Deliberately do NOT set projection
        ds.GetRasterBand(1).WriteArray(np.zeros((10, 10), dtype=np.uint8))
        ds = None

        # Without assume_wgs84: should still work because coords are within WGS84 bounds
        result = geoextent.fromFile(tmp_path, bbox=True)
        assert result is not None
        assert "bbox" in result

        # With assume_wgs84: explicitly enabled
        result2 = geoextent.fromFile(tmp_path, bbox=True, assume_wgs84=True)
        assert result2 is not None
        assert "bbox" in result2
    finally:
        os.unlink(tmp_path)
