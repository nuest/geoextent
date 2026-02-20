"""Tests for NFDI4Earth Knowledge Hub provider integration.

Tests cover:
- URL validation for OneStop4All and Cordra URLs (no network)
- Metadata-only extraction from SPARQL endpoint
- WKT geometry parsing (POLYGON)
- Temporal extent handling
- Follow delegation to external providers via landingPage
- Integration with --no-follow
"""

import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.content_providers.NFDI4Earth import NFDI4Earth
from conftest import NETWORK_SKIP_EXCEPTIONS

# Tolerance for coordinate comparisons
_TOL = 0.5


# --- Validation tests (no network, fast) ---


class TestNFDI4EarthValidation:
    """Fast validation tests that do not require network access."""

    def test_nfdi4earth_onestop4all_url_validation(self):
        provider = NFDI4Earth()
        assert provider.validate_provider(
            "https://onestop4all.nfdi4earth.de/result/dthb-82b6552d-2b8e-4800-b955-ea495efc28af"
        )
        assert provider.cordra_id == "n4e/dthb-82b6552d-2b8e-4800-b955-ea495efc28af"
        assert (
            provider.cordra_iri
            == "https://cordra.knowledgehub.nfdi4earth.de/objects/n4e/dthb-82b6552d-2b8e-4800-b955-ea495efc28af"
        )

    def test_nfdi4earth_onestop4all_trailing_slash_validation(self):
        provider = NFDI4Earth()
        assert provider.validate_provider(
            "https://onestop4all.nfdi4earth.de/result/dthb-82b6552d-2b8e-4800-b955-ea495efc28af/"
        )
        assert provider.cordra_id == "n4e/dthb-82b6552d-2b8e-4800-b955-ea495efc28af"

    def test_nfdi4earth_cordra_url_validation(self):
        provider = NFDI4Earth()
        assert provider.validate_provider(
            "https://cordra.knowledgehub.nfdi4earth.de/objects/n4e/dthb-82b6552d-2b8e-4800-b955-ea495efc28af"
        )
        assert provider.cordra_id == "n4e/dthb-82b6552d-2b8e-4800-b955-ea495efc28af"

    def test_nfdi4earth_cordra_test_instance_url_validation(self):
        provider = NFDI4Earth()
        assert provider.validate_provider(
            "https://cordra.knowledgehub.test.n4e.geo.tu-dresden.de/objects/n4e/dthb-abcd1234"
        )
        assert provider.cordra_id == "n4e/dthb-abcd1234"

    def test_nfdi4earth_invalid_identifiers(self):
        provider = NFDI4Earth()
        assert not provider.validate_provider("https://zenodo.org/records/820562")
        assert not provider.validate_provider("10.5281/zenodo.820562")
        assert not provider.validate_provider("https://deims.org/dataset/abc-123")
        assert not provider.validate_provider("not-a-url")
        assert not provider.validate_provider(
            "https://knowledgehub.nfdi4earth.de/something"
        )

    def test_nfdi4earth_supports_metadata_extraction(self):
        provider = NFDI4Earth()
        assert provider.supports_metadata_extraction is True

    def test_nfdi4earth_provider_info(self):
        info = NFDI4Earth.provider_info()
        assert info is not None
        assert info["name"] == "NFDI4Earth"


# --- External reference extraction tests (no network, fast) ---


class TestNFDI4EarthExternalReferences:
    """Fast tests for _extract_external_references() -- no network required."""

    def test_extract_external_references_landing_page_url(self):
        provider = NFDI4Earth()
        metadata = {"landing_page": "https://www.geoportal.de/Metadata/abc-123"}
        refs = provider._extract_external_references(metadata)
        assert refs == ["https://www.geoportal.de/Metadata/abc-123"]

    def test_extract_external_references_doi_url(self):
        provider = NFDI4Earth()
        metadata = {"landing_page": "https://doi.org/10.5281/zenodo.12345"}
        refs = provider._extract_external_references(metadata)
        assert refs == ["https://doi.org/10.5281/zenodo.12345"]

    def test_extract_external_references_none(self):
        provider = NFDI4Earth()
        metadata = {"landing_page": None}
        refs = provider._extract_external_references(metadata)
        assert refs == []

    def test_extract_external_references_missing_key(self):
        provider = NFDI4Earth()
        metadata = {}
        refs = provider._extract_external_references(metadata)
        assert refs == []


# --- Network tests (auto-marked slow via conftest) ---


class TestNFDI4EarthExtraction:
    """Network tests for NFDI4Earth metadata extraction."""

    def test_nfdi4earth_metadata_only_extraction(self):
        """Provider sample test: Schiffsdichte 2013, spatial only."""
        try:
            result = geoextent.fromRemote(
                "https://onestop4all.nfdi4earth.de/result/dthb-82b6552d-2b8e-4800-b955-ea495efc28af/",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert result["crs"] == "4326"
        # WKT: POLYGON((3 60, 3 53, 15 53, 15 60, 3 60))
        # Default output is [minlat, minlon, maxlat, maxlon]
        bbox = result["bbox"]
        assert bbox[0] == pytest.approx(53, abs=_TOL)  # minlat
        assert bbox[1] == pytest.approx(3, abs=_TOL)  # minlon
        assert bbox[2] == pytest.approx(60, abs=_TOL)  # maxlat
        assert bbox[3] == pytest.approx(15, abs=_TOL)  # maxlon

    def test_nfdi4earth_berlin_dataset(self):
        """FNP Berlin: spatial only, Berlin area polygon."""
        try:
            result = geoextent.fromRemote(
                "https://onestop4all.nfdi4earth.de/result/dthb-92a8e490-3d32-46cc-853a-50c0d43a187f/",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        # Berlin area: lat ~[52.33, 52.69], lon ~[13.08, 13.77]
        bbox = result["bbox"]
        assert bbox[0] == pytest.approx(52.33, abs=_TOL)  # minlat
        assert bbox[1] == pytest.approx(13.08, abs=_TOL)  # minlon
        assert bbox[2] == pytest.approx(52.69, abs=_TOL)  # maxlat
        assert bbox[3] == pytest.approx(13.77, abs=_TOL)  # maxlon

    def test_nfdi4earth_with_temporal(self):
        """ESA Antarctic Ice Sheet: spatial + temporal 1994-2021."""
        try:
            result = geoextent.fromRemote(
                "https://onestop4all.nfdi4earth.de/result/dthb-7b3bddd5af4945c2ac508a6d25537f0a/",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert "tbox" in result
        assert result["tbox"][0].startswith("1994")
        assert result["tbox"][1].startswith("2021")

    def test_nfdi4earth_cordra_url_extraction(self):
        """Same dataset via direct Cordra URL."""
        try:
            result = geoextent.fromRemote(
                "https://cordra.knowledgehub.nfdi4earth.de/objects/n4e/dthb-82b6552d-2b8e-4800-b955-ea495efc28af",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        bbox = result["bbox"]
        assert bbox[0] == pytest.approx(53, abs=_TOL)
        assert bbox[1] == pytest.approx(3, abs=_TOL)

    def test_nfdi4earth_no_follow_uses_own_metadata(self):
        """With follow=False, should use own SPARQL metadata."""
        try:
            result = geoextent.fromRemote(
                "https://onestop4all.nfdi4earth.de/result/dthb-82b6552d-2b8e-4800-b955-ea495efc28af/",
                bbox=True,
                tbox=True,
                follow=False,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert "followed" not in result
