import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.content_providers.Dataverse import Dataverse


class TestHeiDataValidation:
    """Fast validation tests for heiDATA provider (no network calls)."""

    TEST_DATASETS = {
        "tjnqzg": {
            "doi": "10.11588/DATA/TJNQZG",
            "doi_url": "https://doi.org/10.11588/DATA/TJNQZG",
            "landing_page": "https://heidata.uni-heidelberg.de/dataset.xhtml?persistentId=doi:10.11588/DATA/TJNQZG",
            "api_url": "https://heidata.uni-heidelberg.de/api/datasets/:persistentId?persistentId=doi:10.11588/DATA/TJNQZG",
            "expected_persistent_id": "doi:10.11588/DATA/TJNQZG",
        },
        "7llxfp": {
            "doi": "10.11588/DATA/7LLXFP",
            "doi_url": "https://doi.org/10.11588/DATA/7LLXFP",
            "landing_page": "https://heidata.uni-heidelberg.de/dataset.xhtml?persistentId=doi:10.11588/DATA/7LLXFP",
            "api_url": "https://heidata.uni-heidelberg.de/api/datasets/:persistentId?persistentId=doi:10.11588/DATA/7LLXFP",
            "expected_persistent_id": "doi:10.11588/DATA/7LLXFP",
        },
    }

    def test_heidata_provider_instantiation(self):
        """Test that Dataverse provider recognizes heiDATA host."""
        provider = Dataverse()
        assert "heidata.uni-heidelberg.de" in provider.known_hosts

    def test_heidata_doi_validation(self):
        """Test DOI-based validation for heiDATA."""
        provider = Dataverse()
        dataset = self.TEST_DATASETS["tjnqzg"]

        assert provider.validate_provider(dataset["doi"]) is True
        assert provider.persistent_id == dataset["expected_persistent_id"]

    def test_heidata_doi_with_prefix_validation(self):
        """Test DOI with doi: prefix validation for heiDATA."""
        provider = Dataverse()
        assert provider.validate_provider("doi:10.11588/DATA/TJNQZG") is True
        assert provider.persistent_id == "doi:10.11588/DATA/TJNQZG"

    def test_heidata_doi_url_validation(self):
        """Test DOI URL validation for heiDATA."""
        provider = Dataverse()
        dataset = self.TEST_DATASETS["tjnqzg"]

        assert provider.validate_provider(dataset["doi_url"]) is True
        assert provider.persistent_id == dataset["expected_persistent_id"]

    def test_heidata_landing_page_url_validation(self):
        """Test landing page URL validation for heiDATA."""
        provider = Dataverse()
        dataset = self.TEST_DATASETS["tjnqzg"]

        assert provider.validate_provider(dataset["landing_page"]) is True
        assert provider.host == "heidata.uni-heidelberg.de"
        assert provider.persistent_id == dataset["expected_persistent_id"]

    def test_heidata_api_url_validation(self):
        """Test API URL validation for heiDATA."""
        provider = Dataverse()
        dataset = self.TEST_DATASETS["tjnqzg"]

        assert provider.validate_provider(dataset["api_url"]) is True
        assert provider.host == "heidata.uni-heidelberg.de"
        assert provider.persistent_id == dataset["expected_persistent_id"]

    def test_heidata_doi_pattern_recognition(self):
        """Test that heiDATA DOI pattern is recognized."""
        provider = Dataverse()

        heidata_dois = [
            "10.11588/DATA/TJNQZG",
            "10.11588/DATA/7LLXFP",
            "10.11588/DATA/CEIWEA",
        ]

        for doi in heidata_dois:
            assert provider._is_dataverse_doi(
                doi
            ), f"Should recognize heiDATA DOI: {doi}"

    def test_heidata_known_host_detection(self):
        """Test that heidata.uni-heidelberg.de is detected as a known Dataverse host."""
        provider = Dataverse()
        assert provider._is_known_dataverse_host("heidata.uni-heidelberg.de")
        assert provider._is_known_dataverse_host("HEIDATA.UNI-HEIDELBERG.DE")

    def test_heidata_invalid_identifiers(self):
        """Test that non-heiDATA identifiers are not matched as heiDATA."""
        provider = Dataverse()

        # These should not match heiDATA DOI pattern specifically
        assert not provider._is_dataverse_doi("10.5281/zenodo.123456")
        assert not provider._is_dataverse_doi("10.17632/ybx6zp2rfp.1")

    def test_heidata_all_identifier_variants_validation(self):
        """Test that all identifier formats validate correctly."""
        dataset = self.TEST_DATASETS["tjnqzg"]
        variants = [
            dataset["doi"],
            "doi:" + dataset["doi"],
            dataset["doi_url"],
            dataset["landing_page"],
            dataset["api_url"],
        ]

        for identifier in variants:
            provider = Dataverse()
            assert (
                provider.validate_provider(identifier) is True
            ), f"Should validate identifier: {identifier}"
            assert (
                provider.persistent_id == dataset["expected_persistent_id"]
            ), f"Persistent ID mismatch for {identifier}"

    def test_heidata_second_dataset_validation(self):
        """Test validation with the second test dataset (7LLXFP)."""
        dataset = self.TEST_DATASETS["7llxfp"]
        variants = [
            dataset["doi"],
            "doi:" + dataset["doi"],
            dataset["doi_url"],
            dataset["landing_page"],
            dataset["api_url"],
        ]

        for identifier in variants:
            provider = Dataverse()
            assert (
                provider.validate_provider(identifier) is True
            ), f"Should validate identifier: {identifier}"
            assert (
                provider.persistent_id == dataset["expected_persistent_id"]
            ), f"Persistent ID mismatch for {identifier}"


class TestHeiDataExtraction:
    """Network-dependent tests for heiDATA provider."""

    def test_heidata_metadata_only_extraction(self):
        """Test metadata-only extraction from heiDATA (provider_sample smoke test).

        Dataset: 3D Point Cloud from Nakadake Sanroku Kiln Site Center, Japan
        heiDATA exposes geospatial metadata via Dataverse API.
        """
        result = geoextent.fromRemote(
            "10.11588/DATA/TJNQZG",
            bbox=True,
            tbox=True,
            download_data=False,
        )

        assert result is not None
        assert result["format"] == "remote"

    def test_heidata_geotiff_extraction(self):
        """Test full extraction of GeoTIFF data from heiDATA.

        Dataset: Water tank detection in Rio de Janeiro (7LLXFP)
        Contains a small GeoTIFF (266 KB) covering Rio de Janeiro area.
        Expected bbox: ~-43.8W to ~-43.1W, ~-23.1S to ~-22.7S
        """
        result = geoextent.fromRemote(
            "10.11588/DATA/7LLXFP",
            bbox=True,
            tbox=True,
            download_data=True,
            max_download_size="5MB",
        )

        assert result is not None
        assert result["format"] == "remote"
        assert "bbox" in result

        bbox = result["bbox"]
        assert len(bbox) == 4
        # Rio de Janeiro: roughly -23.1 to -22.7°S, -43.8 to -43.1°W
        assert -24.0 <= bbox[0] <= -22.0, f"South latitude {bbox[0]} out of range"
        assert -44.0 <= bbox[1] <= -42.0, f"West longitude {bbox[1]} out of range"
        assert -24.0 <= bbox[2] <= -22.0, f"North latitude {bbox[2]} out of range"
        assert -44.0 <= bbox[3] <= -42.0, f"East longitude {bbox[3]} out of range"

        assert result.get("crs") == "4326"

    def test_heidata_identifier_variants_extraction(self):
        """Test that DOI and DOI URL produce the same extraction result."""
        variants = [
            "10.11588/DATA/7LLXFP",
            "https://doi.org/10.11588/DATA/7LLXFP",
        ]

        results = []
        for identifier in variants:
            result = geoextent.fromRemote(
                identifier,
                bbox=True,
                download_data=True,
                max_download_size="5MB",
            )
            assert result is not None, f"Failed for identifier: {identifier}"
            assert result["format"] == "remote", f"Wrong format for: {identifier}"
            assert "bbox" in result, f"No bbox for identifier: {identifier}"
            results.append(result["bbox"])

        # Both variants should produce the same bounding box
        for i in range(4):
            assert (
                abs(results[0][i] - results[1][i]) < 0.001
            ), f"Coordinate {i} differs between variants: {results[0][i]} vs {results[1][i]}"
