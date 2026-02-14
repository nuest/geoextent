import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.content_providers.Dataverse import Dataverse


class TestIoerDataValidation:
    """Fast validation tests for ioerDATA provider (no network calls)."""

    TEST_DATASETS = {
        "vdmuww": {
            "doi": "10.71830/VDMUWW",
            "doi_url": "https://doi.org/10.71830/VDMUWW",
            "landing_page": "https://data.fdz.ioer.de/dataset.xhtml?persistentId=doi:10.71830/VDMUWW",
            "api_url": "https://data.fdz.ioer.de/api/datasets/:persistentId?persistentId=doi:10.71830/VDMUWW",
            "expected_persistent_id": "doi:10.71830/VDMUWW",
        },
    }

    def test_ioer_data_provider_instantiation(self):
        """Test that Dataverse provider recognizes ioerDATA host."""
        provider = Dataverse()
        assert "data.fdz.ioer.de" in provider.known_hosts

    def test_ioer_data_doi_validation(self):
        """Test DOI-based validation for ioerDATA."""
        provider = Dataverse()
        dataset = self.TEST_DATASETS["vdmuww"]

        assert provider.validate_provider(dataset["doi"]) is True
        assert provider.persistent_id == dataset["expected_persistent_id"]

    def test_ioer_data_doi_with_prefix_validation(self):
        """Test DOI with doi: prefix validation for ioerDATA."""
        provider = Dataverse()
        assert provider.validate_provider("doi:10.71830/VDMUWW") is True
        assert provider.persistent_id == "doi:10.71830/VDMUWW"

    def test_ioer_data_doi_url_validation(self):
        """Test DOI URL validation for ioerDATA."""
        provider = Dataverse()
        dataset = self.TEST_DATASETS["vdmuww"]

        assert provider.validate_provider(dataset["doi_url"]) is True
        assert provider.persistent_id == dataset["expected_persistent_id"]

    def test_ioer_data_landing_page_url_validation(self):
        """Test landing page URL validation for ioerDATA."""
        provider = Dataverse()
        dataset = self.TEST_DATASETS["vdmuww"]

        assert provider.validate_provider(dataset["landing_page"]) is True
        assert provider.host == "data.fdz.ioer.de"
        assert provider.persistent_id == dataset["expected_persistent_id"]

    def test_ioer_data_api_url_validation(self):
        """Test API URL validation for ioerDATA."""
        provider = Dataverse()
        dataset = self.TEST_DATASETS["vdmuww"]

        assert provider.validate_provider(dataset["api_url"]) is True
        assert provider.host == "data.fdz.ioer.de"
        assert provider.persistent_id == dataset["expected_persistent_id"]

    def test_ioer_data_doi_pattern_recognition(self):
        """Test that ioerDATA DOI pattern is recognized."""
        provider = Dataverse()

        ioer_dois = [
            "10.71830/VDMUWW",
            "10.71830/ABCDEF",
            "10.71830/XYZ123",
        ]

        for doi in ioer_dois:
            assert provider._is_dataverse_doi(
                doi
            ), f"Should recognize ioerDATA DOI: {doi}"

    def test_ioer_data_known_host_detection(self):
        """Test that data.fdz.ioer.de is detected as a known Dataverse host."""
        provider = Dataverse()
        assert provider._is_known_dataverse_host("data.fdz.ioer.de")
        assert provider._is_known_dataverse_host("DATA.FDZ.IOER.DE")

    def test_ioer_data_invalid_identifiers(self):
        """Test that non-ioerDATA identifiers are not matched as ioerDATA."""
        provider = Dataverse()

        # These should not match ioerDATA DOI pattern specifically
        assert not provider._is_dataverse_doi("10.5281/zenodo.123456")
        assert not provider._is_dataverse_doi("10.17632/ybx6zp2rfp.1")

    def test_ioer_data_all_identifier_variants_validation(self):
        """Test that all identifier formats validate correctly."""
        dataset = self.TEST_DATASETS["vdmuww"]
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


class TestIoerDataExtraction:
    """Network-dependent tests for ioerDATA provider."""

    def test_ioer_data_metadata_only_extraction(self):
        """Test metadata-only extraction from ioerDATA (provider_sample smoke test).

        ioerDATA (Dataverse) does not expose geospatial metadata in a way
        geoextent can use, so metadata-only returns a minimal result.
        """
        result = geoextent.fromRemote(
            "10.71830/VDMUWW",
            bbox=True,
            tbox=True,
            download_data=False,
        )

        assert result is not None
        assert result["format"] == "remote"

    def test_ioer_data_geotiff_extraction(self):
        """Test full extraction of GeoTIFF data from ioerDATA.

        Dataset: Locals vs Tourists in Germany (VDMUWW)
        Contains 2 public GeoTIFFs (~2.8MB combined) covering Germany (~47-55°N, ~5-15°E).
        The 17MB PNG (no CRS) is automatically skipped by bbox validation.
        A size limit excludes the 60MB code release ZIP.
        Restricted parquet files are automatically skipped.
        """
        result = geoextent.fromRemote(
            "10.71830/VDMUWW",
            bbox=True,
            tbox=True,
            download_data=True,
            max_download_size="20MB",
        )

        assert result is not None
        assert result["format"] == "remote"
        assert "bbox" in result

        bbox = result["bbox"]
        assert len(bbox) == 4
        # Germany: roughly 47-55°N, 5-15°E
        assert 45.0 <= bbox[0] <= 50.0, f"South latitude {bbox[0]} out of range"
        assert 4.0 <= bbox[1] <= 8.0, f"West longitude {bbox[1]} out of range"
        assert 53.0 <= bbox[2] <= 57.0, f"North latitude {bbox[2]} out of range"
        assert 13.0 <= bbox[3] <= 17.0, f"East longitude {bbox[3]} out of range"

        assert result.get("crs") == "4326"

    def test_ioer_data_identifier_variants_extraction(self):
        """Test that DOI and DOI URL produce the same extraction result."""
        variants = [
            "10.71830/VDMUWW",
            "https://doi.org/10.71830/VDMUWW",
        ]

        results = []
        for identifier in variants:
            result = geoextent.fromRemote(
                identifier,
                bbox=True,
                download_data=True,
                max_download_size="20MB",
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

    def test_ioer_data_restricted_files_skipped(self):
        """Test that restricted files are skipped during download.

        The VDMUWW dataset has 2 restricted parquet.zip files (~218MB).
        With a 5MB limit, the 2 GeoTIFFs (~2.8MB combined) + README (14KB) fit.
        The PNG (17MB) exceeds the budget.
        """
        result = geoextent.fromRemote(
            "10.71830/VDMUWW",
            bbox=True,
            download_data=True,
            max_download_size="5MB",
        )

        assert result is not None
        assert result["format"] == "remote"
        # With 5MB limit, the 2 GeoTIFFs (~2.8MB combined) should fit
        assert "bbox" in result
