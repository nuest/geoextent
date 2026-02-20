"""Tests for Software Heritage content provider.

Tests cover:
- SWHID validation and URL parsing (no network)
- Provider metadata (no network)
- Data download extraction from archived repositories (network)

Example dataset:
- AWMC/geodata (Ancient World Mapping Center, ODbL-licensed)
  hasmonean_kingdom.geojson (9 KB) — Hasmonean Kingdom political shading
  Origin: swh:1:ori:d7e674d91900bb17eba543e437a17c3b161fb527
"""

import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.content_providers.SoftwareHeritage import SoftwareHeritage
from conftest import NETWORK_SKIP_EXCEPTIONS

# --- Validation tests (no network, fast) ---


class TestSWHValidation:
    """Fast validation tests that do not require network access."""

    def test_swh_swhid_cnt_validation(self):
        """Bare content SWHID."""
        provider = SoftwareHeritage()
        assert provider.validate_provider(
            "swh:1:cnt:5719fe02c1b20f2c0e013f0a3d5a89c657409257"
        )
        assert provider._swhid_type == "cnt"
        assert provider._swhid_hash == "5719fe02c1b20f2c0e013f0a3d5a89c657409257"

    def test_swh_swhid_dir_validation(self):
        """Bare directory SWHID."""
        provider = SoftwareHeritage()
        assert provider.validate_provider(
            "swh:1:dir:b9d02ab606442f4e63ab1f3317318e03176bdfe0"
        )
        assert provider._swhid_type == "dir"
        assert provider._swhid_hash == "b9d02ab606442f4e63ab1f3317318e03176bdfe0"

    def test_swh_swhid_rev_validation(self):
        """Bare revision SWHID."""
        provider = SoftwareHeritage()
        assert provider.validate_provider(
            "swh:1:rev:7ecf8bc2b4267af3a1c0897b9ecb9eaabb8aceca"
        )
        assert provider._swhid_type == "rev"

    def test_swh_swhid_rel_validation(self):
        """Bare release SWHID."""
        provider = SoftwareHeritage()
        assert provider.validate_provider(
            "swh:1:rel:0000000000000000000000000000000000000000"
        )
        assert provider._swhid_type == "rel"

    def test_swh_swhid_snp_validation(self):
        """Bare snapshot SWHID."""
        provider = SoftwareHeritage()
        assert provider.validate_provider(
            "swh:1:snp:7020d6636d11668ab0981cc362ae306871a461d5"
        )
        assert provider._swhid_type == "snp"

    def test_swh_swhid_ori_validation(self):
        """Bare origin SWHID."""
        provider = SoftwareHeritage()
        assert provider.validate_provider(
            "swh:1:ori:d7e674d91900bb17eba543e437a17c3b161fb527"
        )
        assert provider._swhid_type == "ori"

    def test_swh_browse_origin_url_validation(self):
        """Browse origin URL."""
        provider = SoftwareHeritage()
        assert provider.validate_provider(
            "https://archive.softwareheritage.org/browse/origin/directory/"
            "?origin_url=https://github.com/AWMC/geodata"
        )
        assert provider._origin_url == "https://github.com/AWMC/geodata"
        assert provider._subpath is None

    def test_swh_browse_origin_url_with_path_validation(self):
        """Browse origin URL with &path= parameter."""
        provider = SoftwareHeritage()
        assert provider.validate_provider(
            "https://archive.softwareheritage.org/browse/origin/directory/"
            "?origin_url=https://github.com/AWMC/geodata"
            "&path=Cultural-Data/political_shading/hasmonean"
        )
        assert provider._origin_url == "https://github.com/AWMC/geodata"
        assert provider._subpath == "Cultural-Data/political_shading/hasmonean"

    def test_swh_browse_directory_url_validation(self):
        """Browse directory URL."""
        provider = SoftwareHeritage()
        assert provider.validate_provider(
            "https://archive.softwareheritage.org/browse/directory/"
            "b9d02ab606442f4e63ab1f3317318e03176bdfe0/"
        )
        assert provider._swhid_type == "dir"
        assert provider._swhid_hash == "b9d02ab606442f4e63ab1f3317318e03176bdfe0"

    def test_swh_browse_revision_url_validation(self):
        """Browse revision URL."""
        provider = SoftwareHeritage()
        assert provider.validate_provider(
            "https://archive.softwareheritage.org/browse/revision/"
            "7ecf8bc2b4267af3a1c0897b9ecb9eaabb8aceca/"
        )
        assert provider._swhid_type == "rev"
        assert provider._swhid_hash == "7ecf8bc2b4267af3a1c0897b9ecb9eaabb8aceca"

    def test_swh_swhid_url_validation(self):
        """SWHID embedded in URL form."""
        provider = SoftwareHeritage()
        assert provider.validate_provider(
            "https://archive.softwareheritage.org/"
            "swh:1:dir:b9d02ab606442f4e63ab1f3317318e03176bdfe0"
        )
        assert provider._swhid_type == "dir"
        assert provider._swhid_hash == "b9d02ab606442f4e63ab1f3317318e03176bdfe0"

    def test_swh_swhid_with_qualifiers_validation(self):
        """SWHID with ;origin= and ;path= qualifiers."""
        provider = SoftwareHeritage()
        assert provider.validate_provider(
            "swh:1:dir:b9d02ab606442f4e63ab1f3317318e03176bdfe0"
            ";origin=https://github.com/AWMC/geodata"
            ";path=/Cultural-Data/political_shading/hasmonean"
        )
        assert provider._swhid_type == "dir"
        assert provider._origin_url == "https://github.com/AWMC/geodata"
        assert provider._subpath == "Cultural-Data/political_shading/hasmonean"

    def test_swh_invalid_identifiers_validation(self):
        """Rejects non-SWH identifiers."""
        invalid = [
            "https://github.com/AWMC/geodata",
            "10.5281/zenodo.820562",
            "https://zenodo.org/records/820562",
            "not-a-valid-identifier",
            "swh:2:dir:b9d02ab606442f4e63ab1f3317318e03176bdfe0",  # wrong version
            "swh:1:dir:tooshort",  # hash too short
            "",
        ]
        for identifier in invalid:
            provider = SoftwareHeritage()
            assert not provider.validate_provider(
                identifier
            ), f"Should reject: {identifier}"

    def test_swh_provider_info(self):
        """provider_info() returns expected structure."""
        info = SoftwareHeritage.provider_info()
        assert info["name"] == "Software Heritage"
        assert "softwareheritage.org" in info["website"]
        assert len(info["examples"]) > 0
        assert "supported_identifiers" in info

    def test_swh_supports_metadata_extraction(self):
        """Software Heritage does not support metadata-only extraction."""
        provider = SoftwareHeritage()
        assert provider.supports_metadata_extraction is False


# --- Network tests (slow, data download extraction) ---


class TestSWHExtraction:
    """Network tests for Software Heritage data download and extraction.

    These tests download actual files from Software Heritage's API.
    """

    def test_swh_metadata_only_extraction(self):
        """Provider sample: AWMC/geodata hasmonean subdirectory via browse origin URL.

        Downloads hasmonean_kingdom.geojson (9 KB) from the AWMC/geodata repository
        archived at Software Heritage. Expected bbox covers the Hasmonean Kingdom
        region (modern Israel/Palestine/Jordan).
        """
        try:
            result = geoextent.fromRemote(
                "https://archive.softwareheritage.org/browse/origin/directory/"
                "?origin_url=https://github.com/AWMC/geodata"
                "&path=Cultural-Data/political_shading/hasmonean",
                bbox=True,
                tbox=False,
                download_skip_nogeo=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Spatial: Hasmonean Kingdom (Levant region)
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        # EPSG:4326 native order: [minlat, minlon, maxlat, maxlon]
        assert bbox[0] == pytest.approx(30.9, abs=0.5)  # minlat
        assert bbox[1] == pytest.approx(33.8, abs=0.5)  # minlon
        assert bbox[2] == pytest.approx(33.4, abs=0.5)  # maxlat
        assert bbox[3] == pytest.approx(36.2, abs=0.5)  # maxlon

    def test_swh_swhid_dir_extraction(self):
        """Direct directory SWHID extraction — hasmonean subdir.

        swh:1:dir:92890dbe77bbe36ccba724673bc62c2764df4f5a is the directory
        containing hasmonean_kingdom.geojson. Same bbox as the browse URL test.
        """
        try:
            result = geoextent.fromRemote(
                "swh:1:dir:92890dbe77bbe36ccba724673bc62c2764df4f5a",
                bbox=True,
                tbox=False,
                download_skip_nogeo=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Same bbox as the browse URL test
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        assert bbox[0] == pytest.approx(30.9, abs=0.5)
        assert bbox[1] == pytest.approx(33.8, abs=0.5)
        assert bbox[2] == pytest.approx(33.4, abs=0.5)
        assert bbox[3] == pytest.approx(36.2, abs=0.5)

    def test_swh_download_skip_nogeo(self):
        """Verify --download-skip-nogeo filters files from root directory."""
        try:
            result = geoextent.fromRemote(
                "https://archive.softwareheritage.org/browse/origin/directory/"
                "?origin_url=https://github.com/AWMC/geodata"
                "&path=Cultural-Data/political_shading/hasmonean",
                bbox=True,
                tbox=False,
                download_skip_nogeo=True,
                max_download_size="5MB",
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        # Should still get a result since there are GeoJSON files
        assert result is not None
        assert result.get("bbox") is not None
