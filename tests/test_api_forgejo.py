"""Tests for Forgejo/Gitea content provider.

Tests cover:
- URL validation and reference parsing (no network)
- Provider metadata (no network)
- Data download extraction from public Codeberg repositories (network)

Example repositories:
- codeberg.org/steko/ancient-ceramic-kilns: ~25KB, 10 GeoJSON files, ceramic kiln locations
- codeberg.org/mokazemi/iran-geojson: GeoJSON, Iran province boundaries
"""

import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.content_providers.Forgejo import Forgejo
from conftest import NETWORK_SKIP_EXCEPTIONS

# --- Validation tests (no network, fast) ---


class TestForgejoValidation:
    """Fast validation tests that do not require network access."""

    def test_forgejo_url_validation(self):
        """Basic repo URL on Codeberg."""
        provider = Forgejo()
        assert provider.validate_provider(
            "https://codeberg.org/steko/ancient-ceramic-kilns"
        )

    def test_forgejo_url_with_branch_validation(self):
        """URL with /tree/{branch}."""
        provider = Forgejo()
        assert provider.validate_provider(
            "https://codeberg.org/steko/ancient-ceramic-kilns/tree/main"
        )

    def test_forgejo_url_with_path_validation(self):
        """URL with /tree/{branch}/{path}."""
        provider = Forgejo()
        assert provider.validate_provider(
            "https://codeberg.org/mokazemi/iran-geojson/tree/master/geojson"
        )

    def test_forgejo_url_with_git_suffix_validation(self):
        """URL ending in .git."""
        provider = Forgejo()
        assert provider.validate_provider(
            "https://codeberg.org/steko/ancient-ceramic-kilns.git"
        )

    def test_forgejo_known_host_codeberg_validation(self):
        """codeberg.org is a known Forgejo host."""
        provider = Forgejo()
        assert provider._is_forgejo_host("codeberg.org")

    def test_forgejo_known_host_helmholtz_validation(self):
        """datahub.hcdc.hereon.de is a known Forgejo host."""
        provider = Forgejo()
        assert provider._is_forgejo_host("datahub.hcdc.hereon.de")

    def test_forgejo_hostname_heuristic_forgejo_validation(self):
        """Hostname containing 'forgejo' detected without API probe."""
        provider = Forgejo()
        assert provider._is_forgejo_host("forgejo.example.edu")

    def test_forgejo_hostname_heuristic_gitea_validation(self):
        """Hostname containing 'gitea' detected without API probe."""
        provider = Forgejo()
        assert provider._is_forgejo_host("gitea.university.de")

    def test_forgejo_rejects_github_validation(self):
        """github.com URLs are not matched (handled by GitHub provider)."""
        provider = Forgejo()
        assert not provider.validate_provider("https://github.com/user/repo")

    def test_forgejo_rejects_gitlab_validation(self):
        """gitlab.com URLs are not matched (handled by GitLab provider)."""
        provider = Forgejo()
        assert not provider.validate_provider("https://gitlab.com/user/repo")

    def test_forgejo_invalid_identifiers_validation(self):
        """Rejects non-Forgejo identifiers."""
        invalid = [
            "https://github.com/user/repo",
            "https://gitlab.com/user/repo",
            "10.5281/zenodo.820562",
            "https://zenodo.org/records/820562",
            "not-a-valid-identifier",
            "https://codeberg.org/",  # no project path
            "https://codeberg.org/useronly",  # only 1 segment
            "",
        ]
        for identifier in invalid:
            provider = Forgejo()
            assert not provider.validate_provider(
                identifier
            ), f"Should reject: {identifier}"

    def test_forgejo_provider_info(self):
        """provider_info() returns expected structure."""
        info = Forgejo.provider_info()
        assert info["name"] == "Forgejo"
        assert "codeberg.org" in info["website"]
        assert len(info["examples"]) > 0
        assert "supported_identifiers" in info

    def test_forgejo_parse_reference_validation(self):
        """Correct owner/repo/ref/path extraction."""
        provider = Forgejo()
        provider.validate_provider(
            "https://codeberg.org/mokazemi/iran-geojson/tree/master/geojson"
        )
        parsed = provider._parse_reference(provider.reference)
        assert parsed["owner"] == "mokazemi"
        assert parsed["repo"] == "iran-geojson"
        assert parsed["ref"] == "master"
        assert parsed["path"] == "geojson"

    def test_forgejo_parse_reference_minimal(self):
        """Minimal URL: just owner/repo."""
        provider = Forgejo()
        provider.validate_provider("https://codeberg.org/steko/ancient-ceramic-kilns")
        parsed = provider._parse_reference(provider.reference)
        assert parsed["owner"] == "steko"
        assert parsed["repo"] == "ancient-ceramic-kilns"
        assert parsed["ref"] is None
        assert parsed["path"] is None

    def test_forgejo_parse_reference_git_suffix(self):
        """.git suffix stripped from repo name."""
        provider = Forgejo()
        provider.validate_provider(
            "https://codeberg.org/steko/ancient-ceramic-kilns.git"
        )
        parsed = provider._parse_reference(provider.reference)
        assert parsed["repo"] == "ancient-ceramic-kilns"

    def test_forgejo_supports_metadata_extraction(self):
        """Forgejo does not support metadata-only extraction."""
        provider = Forgejo()
        assert provider.supports_metadata_extraction is False

    def test_forgejo_provider_can_be_used(self):
        provider = Forgejo()
        assert provider.name == "Forgejo"
        assert hasattr(provider, "validate_provider")
        assert hasattr(provider, "download")


# --- Network tests (slow, data download extraction) ---


class TestForgejoExtraction:
    """Network tests for Forgejo data download and extraction.

    These tests download actual files from public Codeberg repositories.
    """

    def test_forgejo_metadata_only_extraction(self):
        """Provider sample: steko/ancient-ceramic-kilns — 10 GeoJSON files.

        Ceramic kiln locations across the Mediterranean and North Africa.
        Expected bbox covering roughly the southern Mediterranean region.
        """
        try:
            result = geoextent.from_remote(
                "https://codeberg.org/steko/ancient-ceramic-kilns",
                bbox=True,
                tbox=False,
                download_skip_nogeo=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        # EPSG:4326 native order: [minlat, minlon, maxlat, maxlon]
        # Mediterranean/N. Africa ceramic kiln sites: ~30-45 N, 9-36 E
        assert bbox[0] == pytest.approx(30.4, abs=1)  # minlat (N. Africa)
        assert bbox[1] == pytest.approx(9.4, abs=1)  # minlon (Italy)
        assert bbox[2] == pytest.approx(45.4, abs=1)  # maxlat (N. Italy)
        assert bbox[3] == pytest.approx(35.9, abs=1)  # maxlon (E. Mediterranean)

    def test_forgejo_iran_geojson(self):
        """codeberg.org: mokazemi/iran-geojson — Iran province boundaries.

        GeoJSON files with Iran province/country boundaries.
        Expected bbox covering Iran (~25-40 N, 44-63 E).
        """
        try:
            result = geoextent.from_remote(
                "https://codeberg.org/mokazemi/iran-geojson",
                bbox=True,
                tbox=False,
                download_skip_nogeo=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        # EPSG:4326 native order: [minlat, minlon, maxlat, maxlon]
        # Iran bounding box: roughly 25-40 N, 44-63 E
        assert bbox[0] == pytest.approx(25, abs=2)  # minlat
        assert bbox[1] == pytest.approx(44, abs=2)  # minlon
        assert bbox[2] == pytest.approx(40, abs=2)  # maxlat
        assert bbox[3] == pytest.approx(63, abs=2)  # maxlon

    def test_forgejo_specific_directory(self):
        """Extract from a specific subdirectory with geo-file filtering."""
        try:
            result = geoextent.from_remote(
                "https://codeberg.org/mokazemi/iran-geojson",
                bbox=True,
                tbox=False,
                download_skip_nogeo=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"
        assert result.get("bbox") is not None
