"""Tests for Remote Raster (COG) content provider.

Tests cover:
- URL validation (no network)
- Provider metadata (no network)
- Metadata-only extraction from remote GeoTIFF files (network)

Test URLs:
- https://raw.githubusercontent.com/GeoTIFF/test-data/main/files/gfw-azores.tif
  1.0 MB, WGS84, Azores region, confirmed COG
- https://raw.githubusercontent.com/GeoTIFF/test-data/main/files/lcv_landuse.cropland_hyde_p_10km_s0..0cm_2016_v3.2.tif
  0.96 MB, WGS84, near-global, confirmed COG
"""

import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.content_providers.RemoteRaster import RemoteRaster
from conftest import NETWORK_SKIP_EXCEPTIONS

# --- Validation tests (no network, fast) ---


class TestRemoteRasterValidation:
    """Fast validation tests that do not require network access."""

    def test_url_validation_tif(self):
        """URL ending in .tif is accepted."""
        provider = RemoteRaster()
        assert provider.validate_provider("https://example.com/data/raster.tif")
        assert provider.url == "https://example.com/data/raster.tif"

    def test_url_validation_tiff(self):
        """URL ending in .tiff is accepted."""
        provider = RemoteRaster()
        assert provider.validate_provider("https://example.com/data/raster.tiff")

    def test_url_validation_case_insensitive(self):
        """URL matching is case-insensitive for extension."""
        provider = RemoteRaster()
        assert provider.validate_provider("https://example.com/data/raster.TIF")
        assert provider.validate_provider("https://example.com/data/raster.TIFF")

    def test_url_validation_with_query_params(self):
        """URL with query params after .tif is accepted."""
        provider = RemoteRaster()
        assert provider.validate_provider(
            "https://example.com/data/raster.tif?token=abc123"
        )

    def test_url_validation_rejects_non_raster(self):
        """Non-.tif URLs are rejected."""
        provider = RemoteRaster()
        assert not provider.validate_provider("https://example.com/data/file.csv")
        assert not provider.validate_provider("https://example.com/data/file.geojson")
        assert not provider.validate_provider("https://example.com/data/file.shp")

    def test_url_validation_rejects_doi(self):
        """DOIs are rejected (handled by other providers)."""
        provider = RemoteRaster()
        assert not provider.validate_provider("10.5281/zenodo.14711942")

    def test_url_validation_rejects_local_path(self):
        """Local file paths are rejected."""
        provider = RemoteRaster()
        assert not provider.validate_provider("/tmp/data/raster.tif")
        assert not provider.validate_provider("data/raster.tif")

    def test_url_validation_rejects_http_without_extension(self):
        """HTTP URL without .tif extension is rejected."""
        provider = RemoteRaster()
        assert not provider.validate_provider("https://example.com/api/raster/12345")

    def test_provider_info(self):
        """provider_info() returns expected structure."""
        info = RemoteRaster.provider_info()
        assert info is not None
        assert "name" in info
        assert "COG" in info["name"]
        assert "description" in info
        assert "examples" in info
        assert len(info["examples"]) >= 1

    def test_supports_metadata_extraction(self):
        """Provider declares metadata extraction support."""
        provider = RemoteRaster()
        assert provider.supports_metadata_extraction is True


# --- Network tests (marked slow via conftest) ---


class TestRemoteRasterExtraction:
    """Network tests for remote raster metadata extraction."""

    def test_remote_raster_metadata_only_extraction(self):
        """Provider sample test: GeoTIFF/test-data gfw-azores.tif (COG).

        Expected bbox: approximately lon [-33.4, -20.9], lat [37, 41]
        (Azores region, WGS84)
        """
        try:
            result = geoextent.from_remote(
                "https://raw.githubusercontent.com/GeoTIFF/test-data/main/files/gfw-azores.tif",
                bbox=True,
                tbox=False,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Spatial: Azores region
        # EPSG:4326 native order: [minlat, minlon, maxlat, maxlon]
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        # Latitude range: roughly 37-41
        assert bbox[0] > 30, f"minlat {bbox[0]} should be > 30"
        assert bbox[2] < 45, f"maxlat {bbox[2]} should be < 45"
        # Longitude range: roughly -34 to -20
        assert bbox[1] < -15, f"minlon {bbox[1]} should be < -15"
        assert bbox[3] > -40, f"maxlon {bbox[3]} should be > -40"

    def test_remote_raster_cog_global(self):
        """COG with near-global extent (lcv_landuse)."""
        try:
            result = geoextent.from_remote(
                "https://raw.githubusercontent.com/GeoTIFF/test-data/main/files/lcv_landuse.cropland_hyde_p_10km_s0..0cm_2016_v3.2.tif",
                bbox=True,
                tbox=False,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        # Near-global: lon ~ [-180, 180], lat ~ [-62, 87]
        assert bbox[1] < -170, f"minlon {bbox[1]} should be < -170"
        assert bbox[3] > 170, f"maxlon {bbox[3]} should be > 170"

    def test_remote_raster_invalid_url(self):
        """Non-existent URL returns no bbox."""
        try:
            result = geoextent.from_remote(
                "https://raw.githubusercontent.com/GeoTIFF/test-data/main/files/nonexistent_file.tif",
                bbox=True,
                tbox=False,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        # May return None or a result dict without bbox (metadata fallback)
        if result is not None:
            assert result.get("bbox") is None
