import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance


class TestOparaProvider:
    """Test TU Dresden Opara (DSpace 7.x) content provider functionality"""

    # Test datasets from TU Dresden Opara repository
    TEST_DATASETS = {
        "glacier_calving_fronts": {
            "item_uuid": "4cdf08d6-2738-4c9e-9d27-345a0647ff7c",
            "url": "https://opara.zih.tu-dresden.de/items/4cdf08d6-2738-4c9e-9d27-345a0647ff7c",
            "doi": "10.25532/OPARA-581",
            "handle": "https://opara.zih.tu-dresden.de/handle/123456789/821",
            "title": "Manually delineated glacier calving front locations",
            "description": "312 manually delineated glacier calving front positions using Landsat imagery",
            "expected_files": ["calving_front_locations.zip"],
            "has_shapefiles": True,
            "has_nested_dirs": True,
            "file_size": 2739729,  # bytes
            # Expected spatial extent based on Antarctic Peninsula glacier data
            "expected_bbox": [
                -69.51,
                -69.46,
                -58.96,
                -58.93,
            ],  # Approximate Antarctica coordinates
            "expected_crs": "4326",
        }
    }

    def test_opara_url_validation(self):
        """Test that Opara provider correctly validates different URL formats"""
        from geoextent.lib.content_providers.Opara import Opara

        provider = Opara()
        dataset = self.TEST_DATASETS["glacier_calving_fronts"]

        # Test various URL formats
        test_cases = [
            (dataset["url"], True, "Direct item URL"),
            (dataset["doi"], True, "Bare DOI"),
            (f"https://doi.org/{dataset['doi']}", True, "DOI resolver URL"),
            (f"http://dx.doi.org/{dataset['doi']}", True, "Legacy DOI resolver"),
            (dataset["handle"], True, "Handle URL"),
            (dataset["item_uuid"], True, "Direct UUID"),
            ("https://example.com/invalid", False, "Invalid URL"),
            ("10.1234/invalid.doi", False, "Invalid DOI"),
        ]

        for url, should_validate, description in test_cases:
            provider = Opara()  # Fresh instance for each test
            is_valid = provider.validate_provider(url)
            assert is_valid == should_validate, f"Failed for {description}: {url}"

            if should_validate:
                assert (
                    provider.item_uuid == dataset["item_uuid"]
                ), f"Wrong UUID extracted for {description}"

    def test_opara_metadata_retrieval(self):
        """Test metadata retrieval from Opara API"""
        from geoextent.lib.content_providers.Opara import Opara

        provider = Opara()
        dataset = self.TEST_DATASETS["glacier_calving_fronts"]

        # Validate and get metadata
        assert provider.validate_provider(dataset["doi"])
        metadata = provider._get_metadata()

        # Check basic metadata fields
        assert metadata is not None
        assert "uuid" in metadata
        assert metadata["uuid"] == dataset["item_uuid"]

        # Check that metadata contains expected structure
        assert "metadata" in metadata or "name" in metadata

    def test_opara_file_information(self):
        """Test file information retrieval from Opara API"""
        from geoextent.lib.content_providers.Opara import Opara

        provider = Opara()
        dataset = self.TEST_DATASETS["glacier_calving_fronts"]

        # Validate and get file information
        assert provider.validate_provider(dataset["doi"])
        files = provider._get_file_information()

        # Should find the ZIP file
        assert len(files) >= 1, "Should find at least one file"

        zip_file = next(
            (f for f in files if f["name"] == "calving_front_locations.zip"), None
        )
        assert zip_file is not None, "Should find the ZIP file"
        assert zip_file["size"] == dataset["file_size"], "File size should match"
        assert "url" in zip_file, "File should have download URL"
        assert zip_file["url"].startswith("https://"), "Download URL should be HTTPS"

    @pytest.mark.parametrize("reference_type", ["doi", "url", "handle", "uuid"])
    def test_opara_extraction_different_references(self, reference_type):
        """Test extraction works with different reference formats"""
        dataset = self.TEST_DATASETS["glacier_calving_fronts"]
        reference = dataset[reference_type]

        # Extract spatial extent
        result = geoextent.fromRemote(reference, bbox=True, tbox=False)

        # Verify extraction succeeded
        assert result is not None
        assert "bbox" in result

        # Check that bbox is reasonable for Antarctic Peninsula
        bbox = result["bbox"]
        assert len(bbox) == 4

        # Rough bounds check for Antarctic Peninsula region
        # Based on actual data: bbox is approximately [-69.51, -69.46, -58.96, -58.93]
        assert (
            -70 <= bbox[0] <= -58
        ), f"Western longitude {bbox[0]} out of expected range"
        assert (
            -70 <= bbox[1] <= -58
        ), f"Southern latitude {bbox[1]} out of expected range"
        assert (
            -70 <= bbox[2] <= -58
        ), f"Eastern longitude {bbox[2]} out of expected range"
        assert (
            -70 <= bbox[3] <= -58
        ), f"Northern latitude {bbox[3]} out of expected range"

    def test_opara_extraction_with_size_limit(self):
        """Test extraction with download size limits"""
        dataset = self.TEST_DATASETS["glacier_calving_fronts"]

        # Test with very small size limit (should skip files)
        result = geoextent.fromRemote(
            dataset["doi"],
            bbox=True,
            max_download_size="1MB",  # Much smaller than the 2.7MB file
        )
        # Should still return a result but may be limited
        assert result is not None

        # Test with adequate size limit
        result = geoextent.fromRemote(
            dataset["doi"],
            bbox=True,
            max_download_size="5MB",  # Larger than the 2.7MB file
        )
        assert result is not None
        assert "bbox" in result

    def test_opara_extraction_skip_nogeo(self):
        """Test extraction with geospatial file filtering"""
        dataset = self.TEST_DATASETS["glacier_calving_fronts"]

        # Test with geospatial filtering (should include ZIP files)
        result = geoextent.fromRemote(
            dataset["doi"],
            bbox=True,
            download_skip_nogeo=True,
        )

        assert result is not None
        assert "bbox" in result

    def test_opara_extraction_metadata_only(self):
        """Test metadata-only extraction mode"""
        dataset = self.TEST_DATASETS["glacier_calving_fronts"]

        # Test metadata-only mode (should not download files)
        result = geoextent.fromRemote(
            dataset["doi"],
            bbox=True,
            download_data=False,
        )

        # Should return result even in metadata-only mode
        # (though extent extraction may be limited)
        assert result is not None

    def test_opara_provider_in_provider_list(self):
        """Test that Opara provider is properly registered"""
        from geoextent.lib.extent import geoextent_from_repository

        extractor = geoextent_from_repository()
        provider_classes = extractor.content_providers

        # Check that Opara provider is in the list
        from geoextent.lib.content_providers.Opara import Opara

        assert Opara in provider_classes, "Opara provider should be registered"

    def test_opara_real_extraction_end_to_end(self):
        """End-to-end test with real Opara repository data"""
        dataset = self.TEST_DATASETS["glacier_calving_fronts"]

        # Full extraction test
        result = geoextent.fromRemote(
            dataset["doi"],
            bbox=True,
            tbox=True,
        )

        # Verify complete extraction
        assert result is not None
        assert "bbox" in result
        assert "crs" in result
        assert result["crs"] == dataset["expected_crs"]

        # Verify the result has reasonable spatial extent
        bbox = result["bbox"]
        assert len(bbox) == 4

        # Verify extraction metadata
        if "extraction_metadata" in result:
            metadata = result["extraction_metadata"]
            assert "format" in metadata
            assert metadata["format"] == "remote"
            assert "files_processed" in metadata.get("statistics", {})

    def test_opara_provider_error_handling(self):
        """Test error handling for invalid references"""
        from geoextent.lib.content_providers.Opara import Opara

        provider = Opara()

        # Test invalid UUID
        assert not provider.validate_provider("invalid-uuid-format")

        # Test invalid DOI
        assert not provider.validate_provider("10.25532/INVALID-123")

        # Test completely invalid URL
        assert not provider.validate_provider("https://example.com/invalid")

    def test_opara_geospatial_file_filtering(self):
        """Test that geospatial file filtering works correctly"""
        from geoextent.lib.content_providers.Opara import Opara

        provider = Opara()

        # Test file extension detection
        test_files = [
            {"name": "data.zip", "size": 1000, "url": "http://example.com"},
            {"name": "document.pdf", "size": 500, "url": "http://example.com"},
            {"name": "spatial.shp", "size": 2000, "url": "http://example.com"},
            {"name": "readme.txt", "size": 100, "url": "http://example.com"},
        ]

        # Filter for geospatial files only
        geo_files = provider._filter_geospatial_files(
            test_files,
            skip_non_geospatial=True,
            max_size_mb=None,
        )

        # Should keep ZIP and SHP files, skip PDF and TXT
        assert len(geo_files) == 2
        geo_names = {f["name"] for f in geo_files}
        assert "data.zip" in geo_names
        assert "spatial.shp" in geo_names
        assert "document.pdf" not in geo_names
        assert "readme.txt" not in geo_names
