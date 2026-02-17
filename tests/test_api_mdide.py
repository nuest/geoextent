import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance
from conftest import NETWORK_SKIP_EXCEPTIONS


# Test datasets with known geographic and temporal coverage
# Reference data retrieved from NOKIS CSW API
TEST_DATASETS = {
    "seegras": {
        "uuid": "00100e9d-7838-4563-9dd7-2570b0d932cb",
        "landing_url": "https://nokis.mdi-de-dienste.org/trefferanzeige?docuuid=00100e9d-7838-4563-9dd7-2570b0d932cb",
        "title": "Seegras-Vorkommen",
        # Reference bbox [S, W, N, E] (public API format)
        "expected_bbox": [54.16, 8.29, 55.05, 9.01],
        "expected_tbox": ["1994-07-14", "2023-09-30"],
        "bbox_tolerance": 0.5,
    },
    "kuestenlinie": {
        "uuid": "c7d748c9-e12f-4038-a556-b1698eb4033e",
        "landing_url": "https://nokis.mdi-de-dienste.org/trefferanzeige?docuuid=c7d748c9-e12f-4038-a556-b1698eb4033e",
        "title": "Küstenlinie",
        # Reference bbox [S, W, N, E] (public API format)
        "expected_bbox": [53.37, 6.37, 55.10, 9.01],
        "expected_tbox": None,  # No temporal extent in metadata
        "bbox_tolerance": 0.5,
    },
    "schutzgebiete": {
        "uuid": "169446e3-0dc0-41ef-b3a6-60b078fb9ed3",
        "landing_url": "https://nokis.mdi-de-dienste.org/trefferanzeige?docuuid=169446e3-0dc0-41ef-b3a6-60b078fb9ed3",
        "title": "Schutzgebiete",
        # Reference bbox [S, W, N, E] (public API format)
        "expected_bbox": [47.14, 3.62, 55.91, 15.72],
        "expected_tbox": ["2019-01-01", "2024-01-01"],
        "bbox_tolerance": 1.0,
    },
    "msrl_schadstoffe": {
        "uuid": "436f1ee4-3cfd-47cb-8f64-f3a5f2234fb0",
        "landing_url": "https://nokis.mdi-de-dienste.org/trefferanzeige?docuuid=436f1ee4-3cfd-47cb-8f64-f3a5f2234fb0",
        "title": "Schadstoffe",
        # Reference bbox [S, W, N, E] (public API format)
        "expected_bbox": [53.89, 8.18, 55.09, 11.55],
        "expected_tbox": ["2003-01-01", "2012-01-01"],
        "bbox_tolerance": 0.5,
    },
}


class TestMDIDEValidation:
    """Fast validation tests (no network)."""

    def test_mdide_url_validation(self):
        """Test that MDI-DE landing page URLs are correctly validated"""
        from geoextent.lib.content_providers.MDIDE import MDIDE

        dataset = TEST_DATASETS["seegras"]

        provider = MDIDE()
        assert provider.validate_provider(dataset["landing_url"]) is True
        assert provider.record_uuid == dataset["uuid"]

    def test_mdide_invalid_identifiers(self):
        """Test that non-MDI-DE identifiers are rejected"""
        from geoextent.lib.content_providers.MDIDE import MDIDE

        invalid_identifiers = [
            "10.5281/zenodo.820562",  # Zenodo DOI
            "10.48437/7ca5ef-2e1287",  # BAW DOI
            "10.25928/HK1000",  # BGR DOI
            "not-a-valid-identifier",
            "",
            "https://example.com/dataset/123",
            "https://figshare.com/articles/123456",
            "https://datenrepository.baw.de/trefferanzeige?docuuid=40936F66-3DD8-43D0-99AE-7CA5EF2E1287",
        ]

        for identifier in invalid_identifiers:
            provider = MDIDE()
            assert (
                provider.validate_provider(identifier) is False
            ), f"Should not validate: {identifier}"

    def test_mdide_provider_can_be_used(self):
        """Test that MDI-DE provider is available and properly configured"""
        from geoextent.lib.content_providers.MDIDE import MDIDE

        provider = MDIDE()
        assert provider is not None
        assert provider.name == "MDI-DE"
        assert hasattr(provider, "validate_provider")
        assert hasattr(provider, "download")
        assert provider.supports_metadata_extraction is True

    def test_mdide_provider_info(self):
        """Test that MDI-DE provider_info returns correct metadata"""
        from geoextent.lib.content_providers.MDIDE import MDIDE

        info = MDIDE.provider_info()
        assert info["name"] == "MDI-DE"
        assert "mdi-de.org" in info["website"]
        assert len(info["supported_identifiers"]) >= 2
        assert len(info["examples"]) >= 2

    def test_mdide_supports_metadata_extraction(self):
        """Test that supports_metadata_extraction returns True"""
        from geoextent.lib.content_providers.MDIDE import MDIDE

        provider = MDIDE()
        assert provider.supports_metadata_extraction is True

    def test_mdide_url_parsing_variants(self):
        """Test various URL format variants are parsed correctly"""
        from geoextent.lib.content_providers.MDIDE import MDIDE

        uuid = "00100e9d-7838-4563-9dd7-2570b0d932cb"
        urls = [
            f"https://nokis.mdi-de-dienste.org/trefferanzeige?docuuid={uuid}",
            f"http://nokis.mdi-de-dienste.org/trefferanzeige?docuuid={uuid}",
            f"https://nokis.mdi-de-dienste.org/trefferanzeige?docuuid={uuid}&extra=param",
        ]

        for url in urls:
            provider = MDIDE()
            assert provider.validate_provider(url) is True, f"Failed for URL: {url}"
            assert provider.record_uuid == uuid


class TestMDIDEMetadata:
    """Phase 1: Metadata-only tests (slow/network)."""

    def test_mdide_metadata_only_extraction(self):
        """Provider sample test: seegras UUID with download_data=False"""
        dataset = TEST_DATASETS["seegras"]

        try:
            result = geoextent.fromRemote(
                dataset["uuid"], bbox=True, tbox=True, download_data=False
            )

            assert result is not None
            assert result["format"] == "remote"

            # Check geographic coverage
            if "bbox" in result and result["bbox"] is not None:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]

                assert len(bbox) == 4
                assert abs(bbox[0] - expected_bbox[0]) < dataset["bbox_tolerance"]
                assert abs(bbox[1] - expected_bbox[1]) < dataset["bbox_tolerance"]
                assert abs(bbox[2] - expected_bbox[2]) < dataset["bbox_tolerance"]
                assert abs(bbox[3] - expected_bbox[3]) < dataset["bbox_tolerance"]

            # Check temporal coverage
            if "tbox" in result and result["tbox"] is not None:
                tbox = result["tbox"]
                assert dataset["expected_tbox"][0] in tbox[0]
                assert dataset["expected_tbox"][1] in tbox[1]

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_mdide_csw_metadata_all_datasets(self):
        """Test direct _fetch_record() for all 4 datasets"""
        from geoextent.lib.content_providers.MDIDE import MDIDE

        for name, dataset in TEST_DATASETS.items():
            try:
                provider = MDIDE()
                provider.record_uuid = dataset["uuid"]
                metadata = provider._fetch_record()

                assert metadata is not None, f"No metadata for {name}"
                assert metadata["title"] is not None, f"No title for {name}"
                assert dataset["title"].lower() in metadata["title"].lower(), (
                    f"Title mismatch for {name}: expected '{dataset['title']}' "
                    f"in '{metadata['title']}'"
                )

                # Check bounding box [minlon, minlat, maxlon, maxlat] (internal order)
                assert metadata["bbox"] is not None, f"No bbox for {name}"
                bbox = metadata["bbox"]
                # expected_bbox is [S, W, N, E] → internal [W, S, E, N]
                expected = dataset["expected_bbox"]
                tol = dataset["bbox_tolerance"]
                assert abs(bbox[0] - expected[1]) < tol, f"W mismatch for {name}"
                assert abs(bbox[1] - expected[0]) < tol, f"S mismatch for {name}"
                assert abs(bbox[2] - expected[3]) < tol, f"E mismatch for {name}"
                assert abs(bbox[3] - expected[2]) < tol, f"N mismatch for {name}"

                # Check temporal extent
                if dataset["expected_tbox"] is not None:
                    assert (
                        metadata["temporal_extent"] is not None
                    ), f"Expected temporal extent for {name}"
                    assert (
                        dataset["expected_tbox"][0]
                        in metadata["temporal_extent"]["start"]
                    )
                    assert (
                        dataset["expected_tbox"][1]
                        in metadata["temporal_extent"]["end"]
                    )

            except NETWORK_SKIP_EXCEPTIONS as e:
                pytest.skip(f"Network error for {name}: {e}")

    def test_mdide_no_temporal_extent(self):
        """Test dataset 2 (kuestenlinie) which has no temporal extent in metadata"""
        from geoextent.lib.content_providers.MDIDE import MDIDE

        dataset = TEST_DATASETS["kuestenlinie"]

        try:
            provider = MDIDE()
            provider.record_uuid = dataset["uuid"]
            metadata = provider._fetch_record()

            assert metadata is not None
            assert metadata["bbox"] is not None
            assert metadata["temporal_extent"] is None

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_mdide_landing_url_extraction(self):
        """Test full fromRemote() with landing page URL"""
        dataset = TEST_DATASETS["seegras"]

        try:
            result = geoextent.fromRemote(
                dataset["landing_url"],
                bbox=True,
                tbox=True,
                download_data=False,
            )

            assert result is not None
            assert result["format"] == "remote"

            if "bbox" in result and result["bbox"] is not None:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]
                tol = dataset["bbox_tolerance"]

                assert abs(bbox[0] - expected_bbox[0]) < tol
                assert abs(bbox[1] - expected_bbox[1]) < tol
                assert abs(bbox[2] - expected_bbox[2]) < tol
                assert abs(bbox[3] - expected_bbox[3]) < tol

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")


class TestMDIDEDirectDownload:
    """Phase 2: Direct download tests (slow/network)."""

    def test_mdide_direct_download_seegras(self):
        """Test dataset 1 (seegras): pre-built CSV/Shapefile download URLs"""
        dataset = TEST_DATASETS["seegras"]

        try:
            result = geoextent.fromRemote(
                dataset["uuid"], bbox=True, tbox=True, download_data=True
            )

            assert result is not None
            assert result["format"] == "remote"

            # Should have bbox from downloaded data or metadata
            if "bbox" in result and result["bbox"] is not None:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]
                tol = dataset["bbox_tolerance"]

                assert abs(bbox[0] - expected_bbox[0]) < tol
                assert abs(bbox[1] - expected_bbox[1]) < tol
                assert abs(bbox[2] - expected_bbox[2]) < tol
                assert abs(bbox[3] - expected_bbox[3]) < tol

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_mdide_direct_download_msrl_gml(self):
        """Test dataset 4 (MSRL Schadstoffe): pre-built GML download URLs"""
        dataset = TEST_DATASETS["msrl_schadstoffe"]

        try:
            result = geoextent.fromRemote(
                dataset["uuid"], bbox=True, tbox=True, download_data=True
            )

            assert result is not None
            assert result["format"] == "remote"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")


class TestMDIDEWFSDownload:
    """Phase 3: WFS download tests (slow/network)."""

    def test_mdide_wfs_download_kuestenlinie(self):
        """Test dataset 2: WFS download from mdi-de-dienste.org GeoServer"""
        dataset = TEST_DATASETS["kuestenlinie"]

        try:
            result = geoextent.fromRemote(
                dataset["uuid"], bbox=True, tbox=False, download_data=True
            )

            assert result is not None
            assert result["format"] == "remote"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_mdide_wfs_download_bfn_schutzgebiete(self):
        """Test dataset 3: WFS download from geodienste.bfn.de"""
        dataset = TEST_DATASETS["schutzgebiete"]

        try:
            result = geoextent.fromRemote(
                dataset["uuid"], bbox=True, tbox=True, download_data=True
            )

            assert result is not None
            assert result["format"] == "remote"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")


class TestMDIDEParameterCombinations:
    """Test MDI-DE with various parameter combinations."""

    def test_mdide_bbox_only(self):
        """Test MDI-DE extraction with only bbox enabled"""
        dataset = TEST_DATASETS["seegras"]

        try:
            result = geoextent.fromRemote(
                dataset["uuid"], bbox=True, tbox=False, download_data=False
            )
            assert result is not None
            assert result["format"] == "remote"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_mdide_tbox_only(self):
        """Test MDI-DE extraction with only tbox enabled"""
        dataset = TEST_DATASETS["seegras"]

        try:
            result = geoextent.fromRemote(
                dataset["uuid"], bbox=False, tbox=True, download_data=False
            )
            assert result is not None
            assert result["format"] == "remote"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")


class TestMDIDEEdgeCases:
    """Test MDI-DE edge cases and error handling."""

    def test_mdide_malformed_identifiers(self):
        """Test MDI-DE with malformed identifiers"""
        from geoextent.lib.content_providers.MDIDE import MDIDE

        malformed = [
            "not-a-uuid",
            "12345",
            "https://other-portal.com/dataset/123",
            "",
        ]

        for identifier in malformed:
            provider = MDIDE()
            result = provider.validate_provider(identifier)
            assert result is False, f"Should not validate: {identifier}"
