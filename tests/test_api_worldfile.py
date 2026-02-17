"""
Tests for world file support in geoextent.

World files provide geospatial transformation information for raster images
that don't have embedded georeferencing. GDAL automatically detects and uses
world files when they are in the same directory as the image file with the
appropriate naming convention.

Supported world file extensions:
- .wld (generic world file)
- .jgw (JPEG world file)
- .pgw (PNG world file)
- .pngw (PNG world file - alternative)
- .tfw (TIFF world file)
- .tifw (TIFF world file - alternative)
- .bpw (BMP world file)
- .gfw (GIF world file)

References:
- https://en.wikipedia.org/wiki/World_file
- https://gdal.org/en/stable/drivers/raster/wld.html
"""

import geoextent.lib.extent as geoextent
from help_functions_test import tolerance
import pytest


class TestWorldFileSupport:
    """Test world file support for various raster formats"""

    def test_png_with_pngw_world_file(self):
        """Test PNG with .pngw world file

        Test data from: https://zenodo.org/record/820562
        PNG image with accompanying .pngw world file providing geospatial information.
        """
        result = geoextent.fromFile(
            "tests/testdata/worldfile/test_with_world.png", bbox=True
        )
        assert "bbox" in result
        assert "crs" in result
        assert result["bbox"] == pytest.approx(
            [25.558346194400002, 96.2114631828, 25.632931128800003, 96.3549032194],
            abs=tolerance,
        )
        assert result["crs"] == "4326"

    def test_png_with_world_file_no_projection(self):
        """Test that PNG with world file but no projection assumes WGS84"""
        result = geoextent.fromFile(
            "tests/testdata/worldfile/test_with_world.png", bbox=True
        )
        # World files don't include CRS info, so we assume WGS84
        assert result["crs"] == "4326"

    def test_png_with_world_file_handler(self):
        """Test that PNG with world file is handled by handleRaster"""
        result = geoextent.fromFile(
            "tests/testdata/worldfile/test_with_world.png", bbox=True
        )
        assert "geoextent_handler" in result
        assert result["geoextent_handler"] == "handleRaster"

    def test_tif_with_tfw_world_file(self):
        """Test TIFF with .tfw world file

        Synthetic 4x3 grayscale TIFF with a .tfw world file placing it over
        a small area near Berlin (52.5N, 13.4E).  Verifies that GDAL picks
        up the .tfw and geoextent correctly assumes WGS84 when no CRS is
        embedded.
        """
        result = geoextent.fromFile(
            "tests/testdata/worldfile/test_with_world.tif", bbox=True
        )
        assert "bbox" in result
        assert "crs" in result
        assert result["crs"] == "4326"
        assert result["geoextent_handler"] == "handleRaster"
        assert result["bbox"] == pytest.approx(
            [52.4995, 13.3995, 52.5025, 13.4035],
            abs=tolerance,
        )
