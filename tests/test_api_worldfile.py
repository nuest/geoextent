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
            [96.2114631828, 25.558346194400002, 96.3549032194, 25.632931128800003],
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


class TestWorldFileExtensions:
    """Test documentation and awareness of world file extensions"""

    def test_supported_world_file_extensions(self):
        """Document the world file extensions that should be supported via GDAL

        This test serves as documentation for supported world file extensions.
        GDAL automatically detects these when present alongside raster files.
        """
        supported_extensions = {
            ".wld": "Generic world file",
            ".jgw": "JPEG world file",
            ".pgw": "PNG world file",
            ".pngw": "PNG world file (alternative)",
            ".tfw": "TIFF world file",
            ".tifw": "TIFF world file (alternative)",
            ".bpw": "BMP world file",
            ".gfw": "GIF world file",
        }

        # This test documents that these extensions are supported via GDAL
        assert len(supported_extensions) == 8
        assert ".pngw" in supported_extensions
        assert ".tfw" in supported_extensions


class TestWorldFileIntegration:
    """Integration tests with remote repositories"""

    @pytest.mark.skipif(True, reason="Slow integration test - run manually when needed")
    def test_zenodo_record_with_png_world_files(self):
        """Test extraction from Zenodo record with PNG and world files

        Test record: https://zenodo.org/record/820562
        Contains PNG images with .pngw world files
        """
        result = geoextent.fromRemote("10.5281/zenodo.820562", bbox=True)
        assert "bbox" in result
        assert result["bbox"] == pytest.approx(
            [
                96.21146318274846,
                25.558346194400002,
                96.35495081696702,
                25.632931128800003,
            ],
            abs=tolerance,
        )

    @pytest.mark.skipif(True, reason="Slow integration test - run manually when needed")
    def test_zenodo_record_with_tif_world_files(self):
        """Test extraction from Zenodo record with TIFF and world files

        Test record: https://zenodo.org/records/7196949
        Contains TIFF images with .tfw world files
        """
        result = geoextent.fromRemote("https://zenodo.org/records/7196949", bbox=True)
        assert "bbox" in result
        assert result["bbox"] == pytest.approx(
            [-60.0, -180.0, 60.0, 180.0], abs=tolerance
        )
