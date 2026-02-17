"""Tests for HALO DB (DLR) content provider.

Tests cover:
- URL validation (no network)
- Provider metadata (no network)
- Metadata-only extraction via GeoJSON search API (network)
- Temporal fallback via HTML parsing (network)
"""

import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.content_providers.HALODB import HALODB
from conftest import NETWORK_SKIP_EXCEPTIONS


# --- Validation tests (no network, fast) ---


class TestHALODBValidation:
    """Fast validation tests that do not require network access."""

    def test_halodb_url_validation(self):
        provider = HALODB()
        assert provider.validate_provider("https://halo-db.pa.op.dlr.de/dataset/745")
        assert provider.dataset_id == "745"

    def test_halodb_url_validation_other_datasets(self):
        test_cases = [
            ("https://halo-db.pa.op.dlr.de/dataset/364", "364"),
            ("https://halo-db.pa.op.dlr.de/dataset/9964", "9964"),
            ("https://halo-db.pa.op.dlr.de/dataset/1", "1"),
        ]
        for url, expected_id in test_cases:
            provider = HALODB()
            assert provider.validate_provider(url)
            assert provider.dataset_id == expected_id

    def test_halodb_invalid_identifiers(self):
        invalid = [
            "10.5281/zenodo.820562",
            "https://zenodo.org/records/820562",
            "https://halo-db.pa.op.dlr.de/mission/11",
            "https://halo-db.pa.op.dlr.de/search",
            "https://example.com/dataset/364",
            "not-a-valid-identifier",
            "",
        ]
        for identifier in invalid:
            provider = HALODB()
            assert not provider.validate_provider(
                identifier
            ), f"Should reject: {identifier}"

    def test_halodb_provider_can_be_used(self):
        provider = HALODB()
        assert provider.name == "HALO DB"
        assert hasattr(provider, "validate_provider")
        assert hasattr(provider, "download")

    def test_halodb_supports_metadata_extraction(self):
        provider = HALODB()
        assert provider.supports_metadata_extraction is True

    def test_halodb_provider_info(self):
        info = HALODB.provider_info()
        assert info["name"] == "HALO DB"
        assert "halo-db.pa.op.dlr.de" in info["website"]
        assert len(info["examples"]) > 0
        assert "supported_identifiers" in info


# --- Network tests (slow, metadata extraction) ---


class TestHALODBExtraction:
    """Network tests for HALO DB metadata extraction."""

    def test_halodb_metadata_only_extraction(self):
        """Provider sample test: dataset 745 (TACTS flight with track geometry)."""
        try:
            result = geoextent.fromRemote(
                "https://halo-db.pa.op.dlr.de/dataset/745",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Dataset 745 has a flight track (LineString) from EDMO (Germany)
        # to GVAC (Cape Verde): lat ~16-49, lon ~-23 to 12
        if result.get("bbox") is not None:
            bbox = result["bbox"]
            assert len(bbox) == 4
            # In EPSG:4326 native order: [minlat, minlon, maxlat, maxlon]
            assert bbox[0] < 20  # minlat (Cape Verde area)
            assert bbox[2] > 45  # maxlat (Germany area)

        # Should have temporal extent from departure/arrival
        if result.get("tbox") is not None:
            tbox = result["tbox"]
            assert "2012" in tbox[0]

    def test_halodb_temporal_from_html_fallback(self):
        """Dataset 364 (TECHNO mission): no flight track, temporal from HTML."""
        try:
            result = geoextent.fromRemote(
                "https://halo-db.pa.op.dlr.de/dataset/364",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        # Dataset 364 has no flight track geometry in GeoJSON, but temporal
        # extent is available from the HTML page (TECHNO mission dates)
        if result.get("tbox") is not None:
            tbox = result["tbox"]
            assert "2010" in tbox[0]

    def test_halodb_no_download_data(self):
        """With download_data=False, should still extract metadata."""
        try:
            result = geoextent.fromRemote(
                "https://halo-db.pa.op.dlr.de/dataset/745",
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
