import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance
from conftest import NETWORK_SKIP_EXCEPTIONS


class TestBAWProvider:
    """Test BAW (Bundesanstalt für Wasserbau) content provider.

    Uses CSW 2.0.2 via OWSLib with ISO 19115/19139 metadata.
    Data served from Apache directory listings on dl.datenrepository.baw.de.
    """

    # Test datasets with known geographic and temporal coverage
    # Reference data retrieved from BAW CSW API on 2026-02-17
    TEST_DATASETS = {
        "trilawatt_hydro": {
            "uuid": "40936F66-3DD8-43D0-99AE-7CA5EF2E1287",
            "doi": "10.48437/7ca5ef-2e1287",
            "doi_url": "https://doi.org/10.48437/7ca5ef-2e1287",
            "landing_url": "https://datenrepository.baw.de/trefferanzeige?docuuid=40936F66-3DD8-43D0-99AE-7CA5EF2E1287",
            "title": "TrilaWatt: Hydrodynamik (2015-2022)",
            # Reference bbox [S, W, N, E] (public API format)
            "expected_bbox": [52.81, 4.01, 55.71, 9.61],
            "expected_tbox": ["2015-01-01", "2022-12-31"],
        },
        "eider_schwebstoff": {
            "uuid": "4C9E4FD1-D87A-4769-88C5-02F2DD8E37B0",
            "doi": "10.48437/02.2023.K.0601.0001",
            "doi_url": "https://doi.org/10.48437/02.2023.K.0601.0001",
            "title": "Schwebstoffmessung zur Trübungskalibrierung an der Eider 01/2022",
            # Very small bbox (~3km)
            "expected_bbox": [54.260189, 8.818816, 54.268402, 8.860301],
            "expected_tbox": ["2022-01-24", "2022-01-27"],
        },
        "trilawatt_sedi": {
            "uuid": "D9EE0DA9-DEDD-47B7-A905-929835B7FCA4",
            "doi": "10.48437/929835b7fca4",
            "title": "TrilaWatt: Sedimentologie (2015-2022)",
            "expected_bbox": [52.81, 4.01, 55.71, 9.61],
            "expected_tbox": ["2015-01-01", "2022-12-31"],
        },
    }

    def test_baw_url_validation(self):
        """Test that BAW landing page URLs are correctly validated"""
        from geoextent.lib.content_providers.BAW import BAW

        dataset = self.TEST_DATASETS["trilawatt_hydro"]

        baw = BAW()
        assert baw.validate_provider(dataset["landing_url"]) is True
        assert baw.record_uuid == dataset["uuid"]

    def test_baw_doi_validation(self):
        """Test that BAW DOIs are correctly validated and resolved"""
        from geoextent.lib.content_providers.BAW import BAW

        test_dois = [
            ("10.48437/7ca5ef-2e1287", "40936F66-3DD8-43D0-99AE-7CA5EF2E1287"),
            (
                "https://doi.org/10.48437/7ca5ef-2e1287",
                "40936F66-3DD8-43D0-99AE-7CA5EF2E1287",
            ),
            (
                "10.48437/02.2023.K.0601.0001",
                "4C9E4FD1-D87A-4769-88C5-02F2DD8E37B0",
            ),
        ]

        for doi, expected_uuid in test_dois:
            baw = BAW()
            result = baw.validate_provider(doi)
            assert result is True, f"Failed to validate DOI: {doi}"
            assert baw.record_uuid == expected_uuid, f"UUID mismatch for {doi}"

    def test_baw_invalid_identifiers(self):
        """Test that non-BAW identifiers are rejected"""
        from geoextent.lib.content_providers.BAW import BAW

        invalid_identifiers = [
            "10.5281/zenodo.820562",  # Zenodo DOI
            "10.25928/HK1000",  # BGR DOI
            "not-a-valid-identifier",
            "",
            "https://example.com/dataset/123",
            "https://figshare.com/articles/123456",
        ]

        for identifier in invalid_identifiers:
            baw = BAW()
            assert (
                baw.validate_provider(identifier) is False
            ), f"Should not validate: {identifier}"

    def test_baw_provider_can_be_used(self):
        """Test that BAW provider is available and properly configured"""
        from geoextent.lib.content_providers.BAW import BAW

        baw = BAW()
        assert baw is not None
        assert baw.name == "BAW"
        assert hasattr(baw, "validate_provider")
        assert hasattr(baw, "download")
        assert baw.supports_metadata_extraction is True

    def test_baw_provider_info(self):
        """Test that BAW provider_info returns correct metadata"""
        from geoextent.lib.content_providers.BAW import BAW

        info = BAW.provider_info()
        assert info["name"] == "BAW"
        assert "10.48437" in info["doi_prefix"]
        assert "datenrepository.baw.de" in info["website"]

    def test_baw_metadata_only_extraction(self):
        """Test BAW metadata-only extraction (no data download)"""
        dataset = self.TEST_DATASETS["eider_schwebstoff"]

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
                assert abs(bbox[0] - expected_bbox[0]) < 0.01
                assert abs(bbox[1] - expected_bbox[1]) < 0.01
                assert abs(bbox[2] - expected_bbox[2]) < 0.01
                assert abs(bbox[3] - expected_bbox[3]) < 0.01

            # Check temporal coverage
            if "tbox" in result and result["tbox"] is not None:
                tbox = result["tbox"]
                assert dataset["expected_tbox"][0] in tbox[0]
                assert dataset["expected_tbox"][1] in tbox[1]

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_baw_csw_metadata_extraction(self):
        """Test direct BAW CSW metadata extraction via OWSLib"""
        from geoextent.lib.content_providers.BAW import BAW

        baw = BAW()
        dataset = self.TEST_DATASETS["trilawatt_hydro"]

        try:
            baw.record_uuid = dataset["uuid"]
            metadata = baw._fetch_record()

            assert metadata is not None
            assert metadata["title"] == dataset["title"]

            # Check bounding box [minlon, minlat, maxlon, maxlat] (internal order)
            assert metadata["bbox"] is not None
            bbox = metadata["bbox"]
            assert abs(bbox[0] - 4.01) < tolerance  # west
            assert abs(bbox[1] - 52.81) < tolerance  # south
            assert abs(bbox[2] - 9.61) < tolerance  # east
            assert abs(bbox[3] - 55.71) < tolerance  # north

            # Check temporal extent
            assert metadata["temporal_extent"] is not None
            assert metadata["temporal_extent"]["start"] == "2015-01-01"
            assert metadata["temporal_extent"]["end"] == "2022-12-31"

            # Check distribution URLs
            assert len(metadata["distribution_urls"]) > 0
            assert any(
                "dl.datenrepository.baw.de" in url
                for url in metadata["distribution_urls"]
            )

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_baw_trilawatt_doi_extraction(self):
        """Test BAW extraction via DOI (TrilaWatt Hydrodynamik)"""
        dataset = self.TEST_DATASETS["trilawatt_hydro"]

        try:
            result = geoextent.fromRemote(
                dataset["doi"], bbox=True, tbox=True, download_data=False
            )

            assert result is not None
            assert result["format"] == "remote"

            if "bbox" in result and result["bbox"] is not None:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]

                assert abs(bbox[0] - expected_bbox[0]) < 0.5
                assert abs(bbox[1] - expected_bbox[1]) < 0.5
                assert abs(bbox[2] - expected_bbox[2]) < 0.5
                assert abs(bbox[3] - expected_bbox[3]) < 0.5

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_baw_eider_small_bbox(self):
        """Test BAW extraction with a very small bbox (Eider ~3km)"""
        dataset = self.TEST_DATASETS["eider_schwebstoff"]

        try:
            result = geoextent.fromRemote(
                dataset["doi"], bbox=True, tbox=True, download_data=False
            )

            assert result is not None

            if "bbox" in result and result["bbox"] is not None:
                bbox = result["bbox"]
                # Verify the bbox is very small (Eider measurement site)
                lat_range = bbox[2] - bbox[0]
                lon_range = bbox[3] - bbox[1]
                assert lat_range < 0.05, f"Lat range too large: {lat_range}"
                assert lon_range < 0.05, f"Lon range too large: {lon_range}"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")


class TestBAWParameterCombinations:
    """Test BAW with various parameter combinations"""

    def test_baw_bbox_only(self):
        """Test BAW extraction with only bbox enabled"""
        try:
            result = geoextent.fromRemote(
                "4C9E4FD1-D87A-4769-88C5-02F2DD8E37B0",
                bbox=True,
                tbox=False,
                download_data=False,
            )
            assert result is not None
            assert result["format"] == "remote"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_baw_tbox_only(self):
        """Test BAW extraction with only tbox enabled"""
        try:
            result = geoextent.fromRemote(
                "4C9E4FD1-D87A-4769-88C5-02F2DD8E37B0",
                bbox=False,
                tbox=True,
                download_data=False,
            )
            assert result is not None
            assert result["format"] == "remote"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_baw_with_details(self):
        """Test BAW extraction with details enabled"""
        try:
            result = geoextent.fromRemote(
                "4C9E4FD1-D87A-4769-88C5-02F2DD8E37B0",
                bbox=True,
                tbox=True,
                details=True,
                download_data=False,
            )
            assert result is not None
            assert result["format"] == "remote"
            assert "details" in result
            assert isinstance(result["details"], dict)

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")


class TestBAWEdgeCases:
    """Test BAW edge cases and error handling"""

    def test_baw_malformed_identifiers(self):
        """Test BAW with malformed identifiers"""
        from geoextent.lib.content_providers.BAW import BAW

        malformed = [
            "not-a-uuid",
            "12345",
            "https://other-portal.com/dataset/123",
            "",
        ]

        for identifier in malformed:
            baw = BAW()
            result = baw.validate_provider(identifier)
            assert result is False, f"Should not validate: {identifier}"

    def test_baw_doi_pattern_recognition(self):
        """Test BAW DOI pattern matching (fast, no network)"""
        from geoextent.lib.content_providers.BAW import BAW
        import re

        # Verify the DOI prefix pattern matches
        doi_pattern = r"(?:https?://(?:dx\.)?doi\.org/)?10\.48437/[\w.\-_]+"
        valid_dois = [
            "10.48437/7ca5ef-2e1287",
            "10.48437/02.2023.K.0601.0001",
            "10.48437/929835b7fca4",
            "10.48437/bcf493-86393b",
        ]

        for doi in valid_dois:
            assert re.match(
                doi_pattern, doi, re.IGNORECASE
            ), f"DOI pattern should match: {doi}"

        # Non-BAW DOIs should not match
        invalid_dois = [
            "10.5281/zenodo.820562",
            "10.25928/HK1000",
        ]

        for doi in invalid_dois:
            assert not re.match(
                doi_pattern, doi, re.IGNORECASE
            ), f"DOI pattern should not match: {doi}"
