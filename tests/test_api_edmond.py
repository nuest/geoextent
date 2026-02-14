import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.content_providers.Dataverse import Dataverse


class TestEdmondValidation:
    """Fast validation tests for Edmond provider (no network calls)."""

    TEST_DATASETS = {
        "qzgtdu": {
            "doi": "10.17617/3.QZGTDU",
            "doi_url": "https://doi.org/10.17617/3.QZGTDU",
            "landing_page": "https://edmond.mpg.de/dataset.xhtml?persistentId=doi:10.17617/3.QZGTDU",
            "api_url": "https://edmond.mpg.de/api/datasets/:persistentId?persistentId=doi:10.17617/3.QZGTDU",
            "expected_persistent_id": "doi:10.17617/3.QZGTDU",
        },
        "tcjf7b": {
            "doi": "10.17617/3.TCJF7B",
            "doi_url": "https://doi.org/10.17617/3.TCJF7B",
            "landing_page": "https://edmond.mpg.de/dataset.xhtml?persistentId=doi:10.17617/3.TCJF7B",
            "api_url": "https://edmond.mpg.de/api/datasets/:persistentId?persistentId=doi:10.17617/3.TCJF7B",
            "expected_persistent_id": "doi:10.17617/3.TCJF7B",
        },
        "u0p08l": {
            "doi": "10.17617/3.U0P08L",
            "doi_url": "https://doi.org/10.17617/3.U0P08L",
            "landing_page": "https://edmond.mpg.de/dataset.xhtml?persistentId=doi:10.17617/3.U0P08L",
            "api_url": "https://edmond.mpg.de/api/datasets/:persistentId?persistentId=doi:10.17617/3.U0P08L",
            "expected_persistent_id": "doi:10.17617/3.U0P08L",
        },
    }

    def test_edmond_provider_instantiation(self):
        """Test that Dataverse provider recognizes Edmond host."""
        provider = Dataverse()
        assert "edmond.mpg.de" in provider.known_hosts

    def test_edmond_doi_validation(self):
        """Test DOI-based validation for Edmond."""
        provider = Dataverse()
        dataset = self.TEST_DATASETS["qzgtdu"]

        assert provider.validate_provider(dataset["doi"]) is True
        assert provider.persistent_id == dataset["expected_persistent_id"]

    def test_edmond_doi_with_prefix_validation(self):
        """Test DOI with doi: prefix validation for Edmond."""
        provider = Dataverse()
        assert provider.validate_provider("doi:10.17617/3.QZGTDU") is True
        assert provider.persistent_id == "doi:10.17617/3.QZGTDU"

    def test_edmond_doi_url_validation(self):
        """Test DOI URL validation for Edmond."""
        provider = Dataverse()
        dataset = self.TEST_DATASETS["qzgtdu"]

        assert provider.validate_provider(dataset["doi_url"]) is True
        assert provider.persistent_id == dataset["expected_persistent_id"]

    def test_edmond_landing_page_url_validation(self):
        """Test landing page URL validation for Edmond."""
        provider = Dataverse()
        dataset = self.TEST_DATASETS["qzgtdu"]

        assert provider.validate_provider(dataset["landing_page"]) is True
        assert provider.host == "edmond.mpg.de"
        assert provider.persistent_id == dataset["expected_persistent_id"]

    def test_edmond_api_url_validation(self):
        """Test API URL validation for Edmond."""
        provider = Dataverse()
        dataset = self.TEST_DATASETS["qzgtdu"]

        assert provider.validate_provider(dataset["api_url"]) is True
        assert provider.host == "edmond.mpg.de"
        assert provider.persistent_id == dataset["expected_persistent_id"]

    def test_edmond_doi_pattern_recognition(self):
        """Test that Edmond DOI pattern is recognized."""
        provider = Dataverse()

        edmond_dois = [
            "10.17617/3.QZGTDU",
            "10.17617/3.TCJF7B",
            "10.17617/3.U0P08L",
            "10.17617/3.DRS2NH",
        ]

        for doi in edmond_dois:
            assert provider._is_dataverse_doi(
                doi
            ), f"Should recognize Edmond DOI: {doi}"

    def test_edmond_known_host_detection(self):
        """Test that edmond.mpg.de is detected as a known Dataverse host."""
        provider = Dataverse()
        assert provider._is_known_dataverse_host("edmond.mpg.de")
        assert provider._is_known_dataverse_host("EDMOND.MPG.DE")

    def test_edmond_invalid_identifiers(self):
        """Test that non-Edmond identifiers are not matched as Edmond."""
        provider = Dataverse()

        assert not provider._is_dataverse_doi("10.5281/zenodo.123456")
        assert not provider._is_dataverse_doi("10.17632/ybx6zp2rfp.1")

    def test_edmond_all_identifier_variants_validation(self):
        """Test that all identifier formats validate correctly."""
        dataset = self.TEST_DATASETS["qzgtdu"]
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

    def test_edmond_second_dataset_validation(self):
        """Test validation with the TCJF7B dataset."""
        dataset = self.TEST_DATASETS["tcjf7b"]
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

    def test_edmond_third_dataset_validation(self):
        """Test validation with the U0P08L dataset (shapefile)."""
        dataset = self.TEST_DATASETS["u0p08l"]
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


class TestEdmondExtraction:
    """Network-dependent tests for Edmond provider."""

    def test_edmond_metadata_only_extraction(self):
        """Test metadata-only extraction from Edmond (provider_sample smoke test).

        Dataset: Training and validation samples for mapping peat extent (QZGTDU)
        Small CSV with longitude/latitude columns, 214 KB.
        """
        result = geoextent.fromRemote(
            "10.17617/3.QZGTDU",
            bbox=True,
            tbox=True,
            download_data=False,
        )

        assert result is not None
        assert result["format"] == "remote"

    def test_edmond_csv_extraction(self):
        """Test full extraction of CSV data from Edmond.

        Dataset: Training and validation samples for mapping peat extent (QZGTDU)
        CSV with longitude/latitude columns, 4656 points in eastern Colombia.
        Expected bbox: ~-77W to -67W, ~-4S to 7N
        """
        result = geoextent.fromRemote(
            "10.17617/3.QZGTDU",
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
        # Eastern Colombia: roughly -4 to 7°N, -77 to -67°W
        assert -6.0 <= bbox[0] <= 0.0, f"South latitude {bbox[0]} out of range"
        assert -80.0 <= bbox[1] <= -65.0, f"West longitude {bbox[1]} out of range"
        assert 5.0 <= bbox[2] <= 10.0, f"North latitude {bbox[2]} out of range"
        assert -70.0 <= bbox[3] <= -60.0, f"East longitude {bbox[3]} out of range"

        assert result.get("crs") == "4326"

    def test_edmond_netcdf_extraction(self):
        """Test full extraction of NetCDF data from Edmond.

        Dataset: PM2.5 Related Premature Mortality in Colombia (TCJF7B)
        ZIP with 11 NetCDF files covering Colombia.
        Expected bbox: ~-81W to -66W, ~-2S to 13N
        """
        result = geoextent.fromRemote(
            "10.17617/3.TCJF7B",
            bbox=True,
            tbox=True,
            download_data=True,
            max_download_size="10MB",
        )

        assert result is not None
        assert result["format"] == "remote"
        assert "bbox" in result

        bbox = result["bbox"]
        assert len(bbox) == 4
        # Colombia: roughly -2 to 13°N, -81 to -66°W
        assert -5.0 <= bbox[0] <= 0.0, f"South latitude {bbox[0]} out of range"
        assert -85.0 <= bbox[1] <= -75.0, f"West longitude {bbox[1]} out of range"
        assert 10.0 <= bbox[2] <= 15.0, f"North latitude {bbox[2]} out of range"
        assert -70.0 <= bbox[3] <= -60.0, f"East longitude {bbox[3]} out of range"

        assert result.get("crs") == "4326"

    def test_edmond_identifier_variants_extraction(self):
        """Test that DOI and DOI URL produce the same extraction result."""
        variants = [
            "10.17617/3.QZGTDU",
            "https://doi.org/10.17617/3.QZGTDU",
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
