"""Tests for GitHub content provider.

Tests cover:
- URL validation and reference parsing (no network)
- Provider metadata (no network)
- Data download extraction from public repositories (network)

Example repositories:
- fraxen/tectonicplates: ~5MB, GeoJSON, global tectonic plates (Bird 2003)
- Nowosad/spDataLarge: ~20MB, GeoTIFF + GeoPackage, Zion NP area
"""

import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.content_providers.GitHub import GitHub
from conftest import NETWORK_SKIP_EXCEPTIONS

# --- Validation tests (no network, fast) ---


class TestGitHubValidation:
    """Fast validation tests that do not require network access."""

    def test_github_url_validation(self):
        """Basic repo URL."""
        provider = GitHub()
        assert provider.validate_provider("https://github.com/fraxen/tectonicplates")

    def test_github_url_with_branch_validation(self):
        """URL with /tree/{branch}."""
        provider = GitHub()
        assert provider.validate_provider(
            "https://github.com/nuest/geoextent/tree/main"
        )

    def test_github_url_with_path_validation(self):
        """URL with /tree/{branch}/{path}."""
        provider = GitHub()
        assert provider.validate_provider(
            "https://github.com/Nowosad/spDataLarge/tree/master/inst/raster"
        )

    def test_github_url_with_git_suffix_validation(self):
        """URL ending in .git."""
        provider = GitHub()
        assert provider.validate_provider(
            "https://github.com/fraxen/tectonicplates.git"
        )

    def test_github_invalid_identifiers_validation(self):
        """Rejects non-GitHub identifiers."""
        invalid = [
            "https://gitlab.com/user/repo",
            "https://bitbucket.org/user/repo",
            "10.5281/zenodo.820562",
            "https://zenodo.org/records/820562",
            "not-a-valid-identifier",
            "",
        ]
        for identifier in invalid:
            provider = GitHub()
            assert not provider.validate_provider(
                identifier
            ), f"Should reject: {identifier}"

    def test_github_provider_info(self):
        """provider_info() returns expected structure."""
        info = GitHub.provider_info()
        assert info["name"] == "GitHub"
        assert "github.com" in info["website"]
        assert len(info["examples"]) > 0
        assert "supported_identifiers" in info

    def test_github_parse_reference_validation(self):
        """Correct owner/repo/ref/path extraction."""
        provider = GitHub()
        provider.validate_provider(
            "https://github.com/Nowosad/spDataLarge/tree/master/inst/raster"
        )
        parsed = provider._parse_reference(provider.reference)
        assert parsed["owner"] == "Nowosad"
        assert parsed["repo"] == "spDataLarge"
        assert parsed["ref"] == "master"
        assert parsed["path"] == "inst/raster"

    def test_github_parse_reference_minimal(self):
        """Minimal URL: just owner/repo."""
        provider = GitHub()
        provider.validate_provider("https://github.com/fraxen/tectonicplates")
        parsed = provider._parse_reference(provider.reference)
        assert parsed["owner"] == "fraxen"
        assert parsed["repo"] == "tectonicplates"
        assert parsed["ref"] is None
        assert parsed["path"] is None

    def test_github_parse_reference_git_suffix(self):
        """.git suffix stripped from repo name."""
        provider = GitHub()
        provider.validate_provider("https://github.com/fraxen/tectonicplates.git")
        parsed = provider._parse_reference(provider.reference)
        assert parsed["repo"] == "tectonicplates"

    def test_github_supports_metadata_extraction(self):
        """GitHub does not support metadata-only extraction."""
        provider = GitHub()
        assert provider.supports_metadata_extraction is False

    def test_github_provider_can_be_used(self):
        provider = GitHub()
        assert provider.name == "GitHub"
        assert hasattr(provider, "validate_provider")
        assert hasattr(provider, "download")


# --- Network tests (slow, data download extraction) ---


class TestGitHubExtraction:
    """Network tests for GitHub data download and extraction.

    These tests download actual files from public GitHub repositories.
    """

    def test_github_metadata_only_extraction(self):
        """Provider sample test: fraxen/tectonicplates — global GeoJSON.

        Expected bbox covers the entire globe (tectonic plates).
        """
        try:
            result = geoextent.fromRemote(
                "https://github.com/fraxen/tectonicplates",
                bbox=True,
                tbox=False,
                download_skip_nogeo=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Spatial: tectonic plates cover the entire globe
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        # EPSG:4326 native order: [minlat, minlon, maxlat, maxlon]
        # Global coverage: roughly [-90, -180, 90, 180]
        assert bbox[0] < -60  # minlat (south)
        assert bbox[1] < -170  # minlon (west)
        assert bbox[2] > 60  # maxlat (north)
        assert bbox[3] > 170  # maxlon (east)

    def test_github_specific_directory(self):
        """Extract from a specific subdirectory path."""
        try:
            result = geoextent.fromRemote(
                "https://github.com/nuest/geoextent/tree/main/tests/testdata/geojson",
                bbox=True,
                tbox=False,
                download_skip_nogeo=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"
        assert result.get("bbox") is not None

    def test_github_download_skip_nogeo(self):
        """Verify --download-skip-nogeo filters non-geospatial files."""
        try:
            result = geoextent.fromRemote(
                "https://github.com/fraxen/tectonicplates",
                bbox=True,
                tbox=False,
                download_skip_nogeo=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        # Should still get a result since there are GeoJSON files
        assert result is not None
        assert result.get("bbox") is not None

    def test_github_spdatalarge_raster_extraction(self):
        """Nowosad/spDataLarge raster subdirectory — GeoTIFF + GeoPackage.

        The inst/raster directory contains files spanning multiple regions:
        - Zion NP (Utah, USA): srtm.tif, landsat.tif, nlcd.tif, nlcd2011.tif
          Approx WGS84 bbox: [-113.24, 37.13, -112.85, 37.52]
        - Mongon (Peru): dem.tif, ndvi.tif, ep.tif (UTM 17S)
          Approx WGS84 bbox: [-77.9, -9.9, -77.7, -9.7]
        - Southern Ecuador: ta.tif (UTM 17S)
          Approx WGS84 bbox: [-79.1, -4.0, -78.9, -3.8]
        - New Zealand: nz_elev.tif
          Approx WGS84 bbox: [169, -47, 178, -34]

        The merged bbox should span from New Zealand to South America to Utah.
        ~20MB download.
        """
        try:
            result = geoextent.fromRemote(
                "https://github.com/Nowosad/spDataLarge/tree/master/inst/raster",
                bbox=True,
                tbox=False,
                download_skip_nogeo=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Spatial: merged bbox across Utah, Peru, Ecuador, and New Zealand
        # EPSG:4326 native order: [minlat, minlon, maxlat, maxlon]
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4

        # minlat: ~-47 (New Zealand, southernmost extent)
        assert bbox[0] == pytest.approx(-47, abs=2)
        # minlon: ~-113.2 (Utah / Zion NP, westernmost extent)
        assert bbox[1] == pytest.approx(-113.2, abs=1)
        # maxlat: ~37.5 (Utah / Zion NP, northernmost extent)
        assert bbox[2] == pytest.approx(37.5, abs=1)
        # maxlon: ~178 (New Zealand, easternmost extent)
        assert bbox[3] == pytest.approx(178, abs=2)
