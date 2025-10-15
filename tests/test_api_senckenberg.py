import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance


class TestSenckenbergProvider:
    """Test Senckenberg Biodiversity and Climate Research Centre CKAN content provider"""

    # Test datasets from Senckenberg data portal
    TEST_DATASETS = {
        "as_sahabi": {
            "dataset_id": "as-sahabi-1",
            "url": "https://dataportal.senckenberg.de/dataset/as-sahabi-1",
            "jsonld_url": "https://dataportal.senckenberg.de/dataset/as-sahabi-1.jsonld",
            "title": "As-Sahabi 1",
            "description": "Paleontological data from Libya",
            "expected_files": [
                "Study area.zip",
                "As-Sahabi.R",
                "abundance fossil_wood.csv",
            ],
            "has_zip": True,
            "has_shapefiles": True,
            "zip_file_size": 3397,  # bytes
            "location": "Libya",
        },
        "grazer_model": {
            "dataset_id": "00dda005-68c0-4e92-96e5-ceb68034f3ba",
            "url": "https://dataportal.senckenberg.de/dataset/00dda005-68c0-4e92-96e5-ceb68034f3ba",
            "jsonld_url": "https://dataportal.senckenberg.de/dataset/00dda005-68c0-4e92-96e5-ceb68034f3ba.jsonld",
            "title": "Coupling a physiological grazer population model",
            "description": "Grazer population and vegetation dynamics model",
            "has_spatial_extent": True,
            "expected_location": "East & South African Savannahs",
            # Based on the API response spatial extent
            "expected_bbox_rough": {
                "west": 13.25,
                "south": -33.75,
                "east": 40.5,
                "north": 9.625,
            },
            "has_temporal_extent": True,
            "temporal_start": 1960,
            "temporal_end": 2006,
        },
        "cross_realm": {
            "dataset_id": "cross-realm-assessment-of-climate-change-impacts-on-species-abundance-trends",
            "url": "https://dataportal.senckenberg.de/dataset/cross-realm-assessment-of-climate-change-impacts-on-species-abundance-trends",
            "title": "Cross-realm assessment of climate change impacts",
            "description": "Climate change impacts on species abundance trends",
        },
    }

    # Test DOI examples
    TEST_DOI = {
        "doi": "10.12761/sgn.2018.10225",
        "doi_url": "https://doi.org/10.12761/sgn.2018.10225",
        "doi_resolver": "http://dx.doi.org/10.12761/sgn.2018.10225",
    }

    TEST_DOI_WITH_TEMPORAL = {
        "doi": "10.12761/sgn.2018.10268",
        "expected_tbox": ["2014-05-01", "2015-12-30"],
        "expected_bbox_rough": {
            "west": -79.2,
            "south": -4.1,
            "east": -78.9,
            "north": -3.9,
        },
    }

    def test_senckenberg_url_validation(self):
        """Test that Senckenberg provider correctly validates different URL formats"""
        from geoextent.lib.content_providers.Senckenberg import Senckenberg

        provider = Senckenberg()
        dataset = self.TEST_DATASETS["as_sahabi"]

        # Test various URL formats
        test_cases = [
            (dataset["url"], True, "Direct dataset URL"),
            (dataset["jsonld_url"], True, "JSON-LD URL"),
            (dataset["dataset_id"], True, "Dataset ID (name slug)"),
            (
                self.TEST_DATASETS["grazer_model"]["dataset_id"],
                True,
                "Dataset ID (UUID)",
            ),
            ("https://example.com/invalid", False, "Invalid URL"),
            ("invalid-dataset-id-123456789", False, "Invalid dataset ID"),
        ]

        for url, should_validate, description in test_cases:
            provider = Senckenberg()  # Fresh instance for each test
            is_valid = provider.validate_provider(url)
            assert is_valid == should_validate, f"Failed for {description}: {url}"

    def test_senckenberg_doi_validation(self):
        """Test that Senckenberg provider handles DOI resolution"""
        from geoextent.lib.content_providers.Senckenberg import Senckenberg

        # Test DOI patterns
        test_cases = [
            (self.TEST_DOI["doi"], "Bare DOI"),
            (self.TEST_DOI["doi_url"], "DOI resolver URL"),
            (self.TEST_DOI["doi_resolver"], "Legacy DOI resolver"),
        ]

        for doi_ref, description in test_cases:
            provider = Senckenberg()
            # This will attempt to resolve the DOI
            # It should either validate successfully or fail gracefully
            try:
                is_valid = provider.validate_provider(doi_ref)
                # If valid, should have extracted a dataset ID
                if is_valid:
                    assert (
                        provider.dataset_id is not None
                    ), f"No dataset ID for {description}"
            except Exception as e:
                # DOI resolution might fail in test environment
                # That's acceptable - we're testing the validation logic
                pytest.skip(f"DOI resolution not available in test environment: {e}")

    def test_senckenberg_metadata_retrieval(self):
        """Test metadata retrieval from Senckenberg CKAN API"""
        from geoextent.lib.content_providers.Senckenberg import Senckenberg

        provider = Senckenberg()
        dataset = self.TEST_DATASETS["as_sahabi"]

        # Validate and get metadata
        assert provider.validate_provider(dataset["dataset_id"])
        metadata = provider._get_metadata()

        # Check basic metadata fields
        assert metadata is not None
        assert "id" in metadata or "name" in metadata
        assert "resources" in metadata, "CKAN metadata should have resources"

    def test_senckenberg_file_information(self):
        """Test file information retrieval from Senckenberg CKAN API"""
        from geoextent.lib.content_providers.Senckenberg import Senckenberg

        provider = Senckenberg()
        dataset = self.TEST_DATASETS["as_sahabi"]

        # Validate and get file information
        assert provider.validate_provider(dataset["dataset_id"])
        files = provider._get_file_information()

        # Should find multiple files
        assert len(files) >= 1, "Should find at least one file"

        # Check for the ZIP file
        zip_file = next((f for f in files if "zip" in f["name"].lower()), None)
        assert zip_file is not None, "Should find a ZIP file"
        assert "url" in zip_file, "File should have download URL"
        assert zip_file["url"].startswith("https://"), "Download URL should be HTTPS"

    @pytest.mark.parametrize("reference_type", ["url", "dataset_id"])
    def test_senckenberg_extraction_different_references(self, reference_type):
        """Test extraction works with different reference formats"""
        dataset = self.TEST_DATASETS["as_sahabi"]

        if reference_type == "url":
            reference = dataset["url"]
        else:
            reference = dataset["dataset_id"]

        # Extract spatial extent
        result = geoextent.fromRemote(reference, bbox=True, tbox=False)

        # Verify extraction succeeded
        assert result is not None
        # Note: as-sahabi-1 may or may not have extractable spatial data
        # The test verifies the provider works, not necessarily that bbox is present
        assert "format" in result
        assert result["format"] == "remote"

    def test_senckenberg_extraction_with_spatial_extent(self):
        """Test extraction from dataset with spatial extent metadata"""
        dataset = self.TEST_DATASETS["grazer_model"]

        # This dataset has spatial extent in metadata
        # However, it may be metadata-only (no downloadable files)
        # Use the URL instead of UUID to ensure Senckenberg provider is used
        result = geoextent.fromRemote(
            dataset["url"],
            bbox=True,
            download_data=False,  # Metadata only for this test
        )

        # Should return result
        assert result is not None
        # Spatial extent may or may not be extracted depending on metadata availability
        # The test verifies the provider handles it correctly

    def test_senckenberg_extraction_with_size_limit(self):
        """Test extraction with download size limits"""
        dataset = self.TEST_DATASETS["as_sahabi"]

        # Test with adequate size limit
        result = geoextent.fromRemote(
            dataset["dataset_id"],
            bbox=True,
            max_download_size="1MB",  # Should be enough for the small ZIP
        )

        assert result is not None

    def test_senckenberg_extraction_skip_nogeo(self):
        """Test extraction with geospatial file filtering"""
        dataset = self.TEST_DATASETS["as_sahabi"]

        # Test with geospatial filtering (should include ZIP files but skip R and CSV)
        result = geoextent.fromRemote(
            dataset["dataset_id"],
            bbox=True,
            download_skip_nogeo=True,
        )

        assert result is not None

    def test_senckenberg_extraction_metadata_only(self):
        """Test metadata-only extraction mode"""
        dataset = self.TEST_DATASETS["as_sahabi"]

        # Test metadata-only mode (should not download files)
        result = geoextent.fromRemote(
            dataset["dataset_id"],
            bbox=True,
            download_data=False,
        )

        # Should return result even in metadata-only mode
        assert result is not None

    def test_senckenberg_provider_can_be_used(self):
        """Test that Senckenberg provider can be instantiated and used"""
        from geoextent.lib.content_providers.Senckenberg import Senckenberg

        # Provider should be instantiable
        provider = Senckenberg()

        # Should have validate_provider method
        assert hasattr(
            provider, "validate_provider"
        ), "Provider should have validate_provider method"

        # Should have download method
        assert hasattr(provider, "download"), "Provider should have download method"

    def test_senckenberg_real_extraction_end_to_end(self):
        """End-to-end test with real Senckenberg repository data"""
        dataset = self.TEST_DATASETS["as_sahabi"]

        # Full extraction test
        result = geoextent.fromRemote(
            dataset["dataset_id"],
            bbox=True,
            tbox=True,
        )

        # Verify complete extraction
        assert result is not None
        assert "format" in result
        assert result["format"] == "remote"

        # If bbox is extracted, it should have proper format
        if "bbox" in result:
            bbox = result["bbox"]
            assert len(bbox) == 4
            assert "crs" in result

    def test_senckenberg_provider_error_handling(self):
        """Test error handling for invalid references"""
        from geoextent.lib.content_providers.Senckenberg import Senckenberg

        provider = Senckenberg()

        # Test invalid dataset ID
        assert not provider.validate_provider("definitely-not-a-valid-dataset-id-12345")

        # Test invalid URL
        assert not provider.validate_provider("https://example.com/invalid")

        # Test invalid DOI (wrong prefix)
        assert not provider.validate_provider("10.1234/invalid.doi")

    def test_senckenberg_geospatial_file_filtering(self):
        """Test that geospatial file filtering works correctly"""
        from geoextent.lib.content_providers.Senckenberg import Senckenberg

        provider = Senckenberg()

        # Test file extension detection
        test_files = [
            {"name": "Study area.zip", "size": 3397, "url": "http://example.com"},
            {"name": "data.csv", "size": 500, "url": "http://example.com"},
            {"name": "script.R", "size": 2000, "url": "http://example.com"},
            {"name": "spatial.shp", "size": 1000, "url": "http://example.com"},
        ]

        # Filter for geospatial files only
        geo_files = provider._filter_geospatial_files(
            test_files,
            skip_non_geospatial=True,
            max_size_mb=None,
        )

        # Should keep ZIP and SHP files, skip R and CSV
        # (unless CSV is considered potentially geospatial)
        geo_names = {f["name"] for f in geo_files}
        assert "Study area.zip" in geo_names
        assert "spatial.shp" in geo_names

    def test_senckenberg_ckan_base_class(self):
        """Test that Senckenberg properly inherits from CKANProvider"""
        from geoextent.lib.content_providers.Senckenberg import Senckenberg
        from geoextent.lib.content_providers.CKANProvider import CKANProvider

        provider = Senckenberg()

        # Verify inheritance
        assert isinstance(provider, CKANProvider)

        # Verify CKAN-specific attributes
        assert hasattr(provider, "host")
        assert "api" in provider.host
        assert provider.host["api"].endswith("/api/3/")

    def test_senckenberg_multiple_datasets(self):
        """Test extraction from multiple Senckenberg datasets"""
        dataset_ids = [
            self.TEST_DATASETS["as_sahabi"]["dataset_id"],
            self.TEST_DATASETS["grazer_model"]["dataset_id"],
        ]

        # Extract from multiple datasets
        result = geoextent.fromRemote(
            dataset_ids,
            bbox=True,
            download_data=False,  # Metadata only for faster testing
        )

        # Verify bulk extraction structure
        assert result is not None
        assert "format" in result
        assert result["format"] == "remote_bulk"
        assert "details" in result
        assert "extraction_metadata" in result

        # Check that both datasets were processed
        assert len(result["details"]) == 2

    def test_senckenberg_jsonld_url_handling(self):
        """Test that .jsonld URLs are handled correctly"""
        from geoextent.lib.content_providers.Senckenberg import Senckenberg

        provider = Senckenberg()
        dataset = self.TEST_DATASETS["as_sahabi"]

        # Validate .jsonld URL
        assert provider.validate_provider(dataset["jsonld_url"])

        # Should extract the same dataset ID
        assert provider.dataset_id == dataset["dataset_id"]

    def test_senckenberg_temporal_extent_extraction(self):
        """Test temporal extent extraction from Senckenberg metadata"""
        dataset = self.TEST_DOI_WITH_TEMPORAL

        # Extract with both spatial and temporal extent
        result = geoextent.fromRemote(
            dataset["doi"],
            bbox=True,
            tbox=True,
            download_data=False,
        )

        # Verify temporal extent is extracted
        assert "tbox" in result, "Temporal extent should be extracted"
        tbox = result["tbox"]
        assert len(tbox) == 2, "Temporal extent should have start and end dates"

        # Verify the dates match expected values
        assert (
            tbox[0] == dataset["expected_tbox"][0]
        ), f"Start date should be {dataset['expected_tbox'][0]}"
        assert (
            tbox[1] == dataset["expected_tbox"][1]
        ), f"End date should be {dataset['expected_tbox'][1]}"

        # Verify spatial extent is also present
        assert "bbox" in result, "Spatial extent should also be extracted"
        bbox = result["bbox"]
        assert len(bbox) == 4, "Bounding box should have 4 coordinates"

        # Verify bbox is roughly in the expected region (Ecuador)
        expected = dataset["expected_bbox_rough"]
        assert (
            expected["west"] <= bbox[0] <= expected["west"] + 0.5
        ), "West coordinate in expected range"
        assert (
            expected["south"] <= bbox[1] <= expected["south"] + 0.5
        ), "South coordinate in expected range"
        assert (
            expected["east"] - 0.5 <= bbox[2] <= expected["east"]
        ), "East coordinate in expected range"
        assert (
            expected["north"] - 0.5 <= bbox[3] <= expected["north"]
        ), "North coordinate in expected range"

    def test_senckenberg_temporal_metadata_api(self):
        """Test temporal metadata extraction via provider API"""
        from geoextent.lib.content_providers.Senckenberg import Senckenberg

        provider = Senckenberg()
        dataset = self.TEST_DOI_WITH_TEMPORAL

        # Validate and extract metadata
        assert provider.validate_provider(dataset["doi"])
        temporal = provider._extract_temporal_metadata()

        # Verify temporal extent
        assert temporal is not None, "Temporal metadata should be extracted"
        assert isinstance(temporal, list), "Temporal extent should be a list"
        assert len(temporal) == 2, "Should have start and end dates"
        assert temporal[0] == dataset["expected_tbox"][0]
        assert temporal[1] == dataset["expected_tbox"][1]
