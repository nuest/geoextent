"""Tests for STAC (SpatioTemporal Asset Catalog) content provider.

Tests cover:
- URL validation and collection ID extraction (no network)
- Provider metadata (no network)
- Metadata-only extraction from all 6 example URLs in issue #25 (network)

Example URLs from https://github.com/nuest/geoextent/issues/25:
1. https://geoservice.dlr.de/eoc/ogc/stac/v1/collections/FOREST_STRUCTURE_DE_COVER_P1Y
2. https://geoservice.dlr.de/eoc/ogc/stac/v1/collections/S5P_TROPOMI_L3_P1D_SO2
3. https://earth-search.aws.element84.com/v1/collections/naip
4. https://gep-supersites-stac.terradue.com/collections/csk-san-andrea-supersite
5. https://api.lantmateriet.se/stac-bild/v1/collections/orto-f2-2014
6. https://api.stac.worldpop.org/collections/CHE
"""

import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.content_providers.STAC import STAC
from conftest import NETWORK_SKIP_EXCEPTIONS

# --- Validation tests (no network, fast) ---


class TestSTACValidation:
    """Fast validation tests that do not require network access."""

    def test_stac_known_host_element84(self):
        provider = STAC()
        assert provider.validate_provider(
            "https://earth-search.aws.element84.com/v1/collections/naip"
        )
        assert provider.collection_id == "naip"

    def test_stac_known_host_dlr(self):
        provider = STAC()
        assert provider.validate_provider(
            "https://geoservice.dlr.de/eoc/ogc/stac/v1/collections/FOREST_STRUCTURE_DE_COVER_P1Y"
        )
        assert provider.collection_id == "FOREST_STRUCTURE_DE_COVER_P1Y"

    def test_stac_known_host_worldpop(self):
        provider = STAC()
        assert provider.validate_provider(
            "https://api.stac.worldpop.org/collections/CHE"
        )
        assert provider.collection_id == "CHE"

    def test_stac_known_host_terradue(self):
        provider = STAC()
        assert provider.validate_provider(
            "https://gep-supersites-stac.terradue.com/collections/csk-san-andrea-supersite"
        )
        assert provider.collection_id == "csk-san-andrea-supersite"

    def test_stac_known_host_lantmateriet(self):
        provider = STAC()
        assert provider.validate_provider(
            "https://api.lantmateriet.se/stac-bild/v1/collections/orto-f2-2014"
        )
        assert provider.collection_id == "orto-f2-2014"

    def test_stac_path_pattern_with_stac_segment(self):
        """URLs with /stac/ in path should match even for unknown hosts."""
        provider = STAC()
        assert provider.validate_provider(
            "https://example.com/api/stac/v1/collections/my-dataset"
        )
        assert provider.collection_id == "my-dataset"

    def test_stac_collection_id_extraction(self):
        test_cases = [
            (
                "https://example.com/stac/v1/collections/sentinel-2-l2a",
                "sentinel-2-l2a",
            ),
            (
                "https://example.com/collections/my_collection",
                "my_collection",
            ),
            (
                "https://example.com/stac/collections/CAPS.LOCK",
                "CAPS.LOCK",
            ),
        ]
        for url, expected_id in test_cases:
            provider = STAC()
            assert provider.validate_provider(url), f"Should match: {url}"
            assert (
                provider.collection_id == expected_id
            ), f"Expected {expected_id}, got {provider.collection_id}"

    def test_stac_invalid_identifiers(self):
        invalid = [
            "10.5281/zenodo.820562",
            "https://zenodo.org/records/820562",
            "https://example.com/api/v1/datasets/123",
            "not-a-valid-identifier",
            "",
        ]
        for identifier in invalid:
            provider = STAC()
            assert not provider.validate_provider(
                identifier
            ), f"Should reject: {identifier}"

    def test_stac_non_http_rejected(self):
        provider = STAC()
        assert not provider.validate_provider("ftp://stac.example.com/collections/foo")

    def test_stac_provider_can_be_used(self):
        provider = STAC()
        assert provider.name == "STAC"
        assert hasattr(provider, "validate_provider")
        assert hasattr(provider, "download")

    def test_stac_supports_metadata_extraction(self):
        provider = STAC()
        assert provider.supports_metadata_extraction is True

    def test_stac_provider_info(self):
        info = STAC.provider_info()
        assert info["name"] == "STAC"
        assert "stacspec.org" in info["website"]
        assert len(info["examples"]) > 0
        assert "supported_identifiers" in info


# --- Network tests (slow, metadata extraction) ---
# All 6 example URLs from issue #25


class TestSTACExtraction:
    """Network tests for STAC metadata extraction.

    Each test covers one of the example URLs from issue #25.
    """

    def test_stac_metadata_only_extraction(self):
        """Provider sample test: Element84 NAIP collection.

        bbox: [-160, 17, -67, 50], temporal: [2010-01-01, 2022-12-31]
        """
        try:
            result = geoextent.fromRemote(
                "https://earth-search.aws.element84.com/v1/collections/naip",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Spatial: NAIP covers continental US + territories
        # STAC bbox [west, south, east, north] = [-160, 17, -67, 50]
        # EPSG:4326 native order: [minlat, minlon, maxlat, maxlon]
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        assert bbox[0] == pytest.approx(17, abs=0.5)  # minlat
        assert bbox[1] == pytest.approx(-160, abs=0.5)  # minlon
        assert bbox[2] == pytest.approx(50, abs=0.5)  # maxlat
        assert bbox[3] == pytest.approx(-67, abs=0.5)  # maxlon

        # Temporal
        assert result.get("tbox") is not None
        tbox = result["tbox"]
        assert "2010" in tbox[0]

    def test_stac_dlr_forest_structure(self):
        """DLR Forest Structure collection (open-ended temporal range).

        bbox: [5.87, 47.27, 15.04, 55.06], temporal: [2017-01-01, null]
        """
        try:
            result = geoextent.fromRemote(
                "https://geoservice.dlr.de/eoc/ogc/stac/v1/collections/FOREST_STRUCTURE_DE_COVER_P1Y",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Spatial: Germany extent
        # STAC bbox [west, south, east, north] = [5.87, 47.27, 15.04, 55.06]
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        assert bbox[0] == pytest.approx(47.27, abs=0.5)  # minlat
        assert bbox[1] == pytest.approx(5.87, abs=0.5)  # minlon
        assert bbox[2] == pytest.approx(55.06, abs=0.5)  # maxlat
        assert bbox[3] == pytest.approx(15.04, abs=0.5)  # maxlon

        # Temporal: open-ended (starts 2017, end is null)
        assert result.get("tbox") is not None
        tbox = result["tbox"]
        assert "2017" in tbox[0]

    def test_stac_dlr_tropomi(self):
        """DLR S5P TROPOMI SO2 collection.

        Second DLR example from issue #25.
        """
        try:
            result = geoextent.fromRemote(
                "https://geoservice.dlr.de/eoc/ogc/stac/v1/collections/S5P_TROPOMI_L3_P1D_SO2",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Spatial: global dataset
        # STAC bbox [west, south, east, north] = [-180, -90, 180, 90]
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        assert bbox[0] == pytest.approx(-90, abs=0.5)  # minlat
        assert bbox[1] == pytest.approx(-180, abs=0.5)  # minlon
        assert bbox[2] == pytest.approx(90, abs=0.5)  # maxlat
        assert bbox[3] == pytest.approx(180, abs=0.5)  # maxlon

        # Temporal: starts 2023-08-01, open-ended
        assert result.get("tbox") is not None
        tbox = result["tbox"]
        assert "2023" in tbox[0]

    def test_stac_terradue_csk(self):
        """Terradue CSK San Andrea Supersite collection.

        bbox: [-125.72, 31.51, -112.89, 42.00]
        """
        try:
            result = geoextent.fromRemote(
                "https://gep-supersites-stac.terradue.com/collections/csk-san-andrea-supersite",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Spatial: California/San Andreas Fault area
        # STAC bbox [west, south, east, north] = [-125.72, 31.51, -112.89, 42.00]
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        assert bbox[0] == pytest.approx(31.51, abs=0.5)  # minlat
        assert bbox[1] == pytest.approx(-125.72, abs=0.5)  # minlon
        assert bbox[2] == pytest.approx(42.00, abs=0.5)  # maxlat
        assert bbox[3] == pytest.approx(-112.89, abs=0.5)  # maxlon

    def test_stac_lantmateriet_ortofoto(self):
        """Lantmateriet Swedish ortofoto collection.

        bbox: [17.91, 56.86, 19.41, 58.45]
        """
        try:
            result = geoextent.fromRemote(
                "https://api.lantmateriet.se/stac-bild/v1/collections/orto-f2-2014",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Spatial: Southern Sweden (Gotland area)
        # STAC bbox [west, south, east, north] = [17.91, 56.86, 19.41, 58.45]
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        assert bbox[0] == pytest.approx(56.86, abs=0.5)  # minlat
        assert bbox[1] == pytest.approx(17.91, abs=0.5)  # minlon
        assert bbox[2] == pytest.approx(58.45, abs=0.5)  # maxlat
        assert bbox[3] == pytest.approx(19.41, abs=0.5)  # maxlon

    def test_stac_worldpop_che(self):
        """WorldPop Switzerland (CHE) collection.

        bbox: [5.96, 45.82, 10.49, 47.81]
        """
        try:
            result = geoextent.fromRemote(
                "https://api.stac.worldpop.org/collections/CHE",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Spatial: Switzerland
        # STAC bbox [west, south, east, north] = [5.96, 45.82, 10.49, 47.81]
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        assert bbox[0] == pytest.approx(45.82, abs=0.5)  # minlat
        assert bbox[1] == pytest.approx(5.96, abs=0.5)  # minlon
        assert bbox[2] == pytest.approx(47.81, abs=0.5)  # maxlat
        assert bbox[3] == pytest.approx(10.49, abs=0.5)  # maxlon

        # Temporal: WorldPop projections (2015-2030)
        if result.get("tbox") is not None:
            tbox = result["tbox"]
            assert "2015" in tbox[0] or "2020" in tbox[0]

    def test_stac_no_download_data(self):
        """With download_data=False, should still extract metadata."""
        try:
            result = geoextent.fromRemote(
                "https://earth-search.aws.element84.com/v1/collections/naip",
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result.get("bbox") is not None
