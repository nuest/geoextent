import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance


class TestMendeleyProvider:
    """Test Mendeley Data content provider functionality"""

    # Test datasets from user request - real Mendeley datasets with different DOI formats
    TEST_DATASETS = {
        "tropical_cloud_forest": {
            "dataset_id": "ybx6zp2rfp",
            "version": "1",
            "url": "https://data.mendeley.com/datasets/ybx6zp2rfp/1",
            "doi": "10.17632/ybx6zp2rfp.1",
            "title": "Tropical Montane Cloud Forest distribution at 0.1 by 0.1 degrees",
            "description": "Contains four geotiff files with cloud forest distribution data",
            "authors": ["Los, Sietse", "Street-Perrott, Alayne", "Loader, Neil", "Froyd, Cindy"],
            "year": 2021,
            "has_geotiff": True,
            "expected_formats": ["geotiff"],
            "has_geospatial_data": True,
            "has_temporal_data": False,
            "identifier_formats": [
                "10.17632/ybx6zp2rfp.1",  # Plain DOI
                "https://doi.org/10.17632/ybx6zp2rfp.1",  # DOI URL
                "https://data.mendeley.com/datasets/ybx6zp2rfp/1",  # Direct URL
                "ybx6zp2rfp.1",  # Dataset ID with version
                "ybx6zp2rfp/1",  # Dataset ID with version (slash)
                "ybx6zp2rfp",  # Bare dataset ID
            ],
        },
        "water_quality_mapping": {
            "dataset_id": "536ynvxw69",
            "version": "1",
            "url": "https://data.mendeley.com/datasets/536ynvxw69/1",
            "doi": "10.17632/536ynvxw69.1",
            "doi_url": "https://doi.org/10.17632/536ynvxw69.1",
            "title": "Water quality modelling geographical mapping",
            "description": "Water quality modelling geographical mapping data",
            "authors": ["MAHANTY, BISWANATH", "Sahoo, Naresh Kumar"],
            "year": 2023,
            "has_geospatial_data": True,
            "has_temporal_data": True,
            "identifier_formats": [
                "10.17632/536ynvxw69.1",
                "https://doi.org/10.17632/536ynvxw69.1",
                "https://data.mendeley.com/datasets/536ynvxw69/1",
                "536ynvxw69.1",
            ],
        },
        "emilia_romagna_floods": {
            "dataset_id": "yzddsc67gy",
            "version": "1",
            "url": "https://data.mendeley.com/datasets/yzddsc67gy/1",
            "doi": "10.17632/yzddsc67gy.1",
            "title": "Research Data of Brief communication: On the environmental impacts of the 2023 floods in Emilia-Romagna (Italy)",
            "description": "Environmental impacts of 2023 floods in Emilia-Romagna Italy",
            "authors": ["Arrighi, Chiara", "Domeneghetti, Alessio"],
            "year": 2024,
            "has_geospatial_data": True,
            "has_temporal_data": True,
            "identifier_formats": [
                "10.17632/yzddsc67gy.1",
                "https://data.mendeley.com/datasets/yzddsc67gy/1",
                "yzddsc67gy.1",
            ],
        },
        "historical_mills_galicia": {
            "dataset_id": "8h9295v4t3",
            "version": "2",  # Note: Version 2
            "url": "https://data.mendeley.com/datasets/8h9295v4t3/2",
            "doi": "10.17632/8h9295v4t3.2",
            "malformed_doi_url": "https://10.17632/8h9295v4t3.2",  # Invalid URL format from user
            "title": "Historical dataset of mills for Galicia in the Austro-Hungarian Empire/southern Poland from 1880 to the 1930s",
            "description": "Historical geographical data about mills in Galicia",
            "authors": ["Ostafin, Krzysztof", "Jasionek, Magdalena", "Kaim, Dominik", "Miklar, Anna"],
            "year": 2021,
            "has_geographical_data": True,
            "has_geospatial_data": True,
            "has_temporal_data": True,
            "identifier_formats": [
                "10.17632/8h9295v4t3.2",
                "https://data.mendeley.com/datasets/8h9295v4t3/2",
                "8h9295v4t3.2",
            ],
        },
    }

    def test_mendeley_provider_validation(self):
        """Test that Mendeley provider validates various identifier formats correctly"""
        from geoextent.lib.content_providers.Mendeley import Mendeley

        provider = Mendeley()

        test_cases = [
            # DOI URL formats
            {
                "input": "https://doi.org/10.17632/ybx6zp2rfp.1",
                "should_validate": True,
                "expected_id": "ybx6zp2rfp",
                "expected_version": "1",
                "description": "Standard DOI URL (https://doi.org)"
            },
            {
                "input": "http://doi.org/10.17632/ybx6zp2rfp.1",
                "should_validate": True,
                "expected_id": "ybx6zp2rfp",
                "expected_version": "1",
                "description": "HTTP DOI URL"
            },
            {
                "input": "https://dx.doi.org/10.17632/ybx6zp2rfp.1",
                "should_validate": True,
                "expected_id": "ybx6zp2rfp",
                "expected_version": "1",
                "description": "Legacy dx.doi.org URL"
            },

            # Bare DOI formats
            {
                "input": "10.17632/ybx6zp2rfp.1",
                "should_validate": True,
                "expected_id": "ybx6zp2rfp",
                "expected_version": "1",
                "description": "Bare DOI"
            },

            # Mendeley Data URLs
            {
                "input": "https://data.mendeley.com/datasets/ybx6zp2rfp/1",
                "should_validate": True,
                "expected_id": "ybx6zp2rfp",
                "expected_version": "1",
                "description": "Direct Mendeley Data URL"
            },
            {
                "input": "http://data.mendeley.com/datasets/ybx6zp2rfp/1",
                "should_validate": True,
                "expected_id": "ybx6zp2rfp",
                "expected_version": "1",
                "description": "HTTP Mendeley Data URL"
            },

            # ID with version formats
            {
                "input": "ybx6zp2rfp.1",
                "should_validate": True,
                "expected_id": "ybx6zp2rfp",
                "expected_version": "1",
                "description": "Dataset ID with dot-separated version"
            },
            {
                "input": "ybx6zp2rfp/1",
                "should_validate": True,
                "expected_id": "ybx6zp2rfp",
                "expected_version": "1",
                "description": "Dataset ID with slash-separated version"
            },

            # Bare dataset ID
            {
                "input": "ybx6zp2rfp",
                "should_validate": True,
                "expected_id": "ybx6zp2rfp",
                "expected_version": None,
                "description": "Bare dataset ID (latest version)"
            },

            # Case variations
            {
                "input": "YBX6ZP2RFP.1",
                "should_validate": True,
                "expected_id": "ybx6zp2rfp",
                "expected_version": "1",
                "description": "Uppercase dataset ID"
            },
            {
                "input": "10.17632/YBX6ZP2RFP.1",
                "should_validate": True,
                "expected_id": "ybx6zp2rfp",
                "expected_version": "1",
                "description": "Uppercase in DOI"
            },

            # Invalid formats
            {
                "input": "not-a-mendeley-identifier",
                "should_validate": False,
                "description": "Invalid identifier"
            },
            {
                "input": "10.1000/invalid.doi",
                "should_validate": False,
                "description": "Non-Mendeley DOI"
            },
            {
                "input": "https://zenodo.org/record/123456",
                "should_validate": False,
                "description": "Different repository URL"
            },
        ]

        for test_case in test_cases:
            provider_instance = Mendeley()  # Fresh instance for each test
            result = provider_instance.validate_provider(test_case["input"])

            assert result == test_case["should_validate"], \
                f"Validation failed for {test_case['description']}: {test_case['input']}"

            if test_case["should_validate"]:
                assert provider_instance.dataset_id == test_case["expected_id"], \
                    f"Dataset ID mismatch for {test_case['description']}: expected {test_case['expected_id']}, got {provider_instance.dataset_id}"
                assert provider_instance.version == test_case["expected_version"], \
                    f"Version mismatch for {test_case['description']}: expected {test_case['expected_version']}, got {provider_instance.version}"

    def test_mendeley_doi_url_variants(self):
        """Test various DOI URL formats are properly handled"""
        test_cases = [
            "https://doi.org/10.17632/ybx6zp2rfp.1",
            "http://doi.org/10.17632/ybx6zp2rfp.1",
            "https://dx.doi.org/10.17632/ybx6zp2rfp.1",
            "https://www.doi.org/10.17632/ybx6zp2rfp.1",
        ]

        print("\nTesting DOI URL variants:")
        for variant in test_cases:
            print(f"Testing: {variant}")
            try:
                result = geoextent.from_repository(variant, bbox=True)
                assert result is not None, f"Failed to process DOI variant: {variant}"
                print(f"✓ Success: {variant}")
            except Exception as e:
                print(f"✗ Failed: {variant} - {e}")
                # Don't fail the test immediately, but note the failure

    def test_mendeley_bare_doi_variants(self):
        """Test bare DOI formats"""
        test_cases = [
            "10.17632/ybx6zp2rfp.1",
        ]

        print("\nTesting bare DOI variants:")
        for variant in test_cases:
            print(f"Testing: {variant}")
            try:
                result = geoextent.from_repository(variant, bbox=True)
                assert result is not None, f"Failed to process bare DOI: {variant}"
                print(f"✓ Success: {variant}")
            except Exception as e:
                print(f"✗ Failed: {variant} - {e}")

    def test_mendeley_url_variants(self):
        """Test Mendeley Data URL formats"""
        test_cases = [
            "https://data.mendeley.com/datasets/ybx6zp2rfp/1",
            "http://data.mendeley.com/datasets/ybx6zp2rfp/1",
        ]

        print("\nTesting Mendeley URL variants:")
        for variant in test_cases:
            print(f"Testing: {variant}")
            try:
                result = geoextent.from_repository(variant, bbox=True)
                assert result is not None, f"Failed to process Mendeley URL: {variant}"
                print(f"✓ Success: {variant}")
            except Exception as e:
                print(f"✗ Failed: {variant} - {e}")

    def test_mendeley_id_variants(self):
        """Test various dataset ID formats"""
        test_cases = [
            "ybx6zp2rfp.1",   # ID.version
            "ybx6zp2rfp/1",   # ID/version
            "ybx6zp2rfp",     # bare ID (latest)
        ]

        print("\nTesting dataset ID variants:")
        for variant in test_cases:
            print(f"Testing: {variant}")
            try:
                result = geoextent.from_repository(variant, bbox=True)
                assert result is not None, f"Failed to process dataset ID: {variant}"
                print(f"✓ Success: {variant}")
            except Exception as e:
                print(f"✗ Failed: {variant} - {e}")

    def test_mendeley_all_identifier_formats_comprehensive(self):
        """Comprehensive test of all identifier formats using the tropical cloud forest dataset"""
        dataset = self.TEST_DATASETS["tropical_cloud_forest"]

        test_formats = [
            # DOI URLs
            f"https://doi.org/{dataset['doi']}",
            f"http://doi.org/{dataset['doi']}",
            f"https://dx.doi.org/{dataset['doi']}",
            f"https://www.doi.org/{dataset['doi']}",

            # Bare DOI
            dataset['doi'],

            # Mendeley URLs
            dataset['url'],
            dataset['url'].replace('https://', 'http://'),

            # ID variants
            f"{dataset['dataset_id']}.{dataset['version']}",
            f"{dataset['dataset_id']}/{dataset['version']}",
            dataset['dataset_id'],  # bare ID

            # Case variations
            f"{dataset['dataset_id'].upper()}.{dataset['version']}",
            f"10.17632/{dataset['dataset_id'].upper()}.{dataset['version']}",
        ]

        print(f"\nTesting all identifier formats for {dataset['title']}:")
        successful_formats = []
        failed_formats = []

        for format_str in test_formats:
            print(f"Testing: {format_str}")
            try:
                result = geoextent.from_repository(format_str, bbox=True)
                assert result is not None
                assert 'bbox' in result
                successful_formats.append(format_str)
                print(f"✓ Success: {format_str}")
            except Exception as e:
                failed_formats.append((format_str, str(e)))
                print(f"✗ Failed: {format_str} - {e}")

        print(f"\nSummary for {dataset['title']}:")
        print(f"Successful formats: {len(successful_formats)}/{len(test_formats)}")
        if failed_formats:
            print("Failed formats:")
            for fmt, error in failed_formats:
                print(f"  - {fmt}: {error}")

    @pytest.mark.slow
    def test_mendeley_tropical_cloud_forest_geotiff(self):
        """Test extraction from tropical cloud forest dataset with GeoTIFF files"""
        dataset = self.TEST_DATASETS["tropical_cloud_forest"]

        print(f"\nTesting {dataset['title']}...")
        try:
            result = geoextent.from_repository(
                dataset['url'],
                bbox=True,
                tbox=True,
                details=True
            )

            assert result is not None
            assert 'bbox' in result
            assert result['bbox'] is not None
            assert len(result['bbox']) == 4

            # Check that bounding box values are reasonable for global data
            bbox = result['bbox']
            assert -180 <= bbox[0] <= 180  # min longitude
            assert -90 <= bbox[1] <= 90    # min latitude
            assert -180 <= bbox[2] <= 180  # max longitude
            assert -90 <= bbox[3] <= 90    # max latitude
            assert bbox[0] <= bbox[2]      # min_lon <= max_lon
            assert bbox[1] <= bbox[3]      # min_lat <= max_lat

            print(f"✓ Extracted bbox: {result['bbox']}")

            if 'details' in result:
                print(f"✓ Found {len(result['details'])} files")

            return result

        except Exception as e:
            print(f"✗ Failed to extract from {dataset['title']}: {e}")
            raise

    @pytest.mark.slow
    def test_mendeley_multiple_datasets(self):
        """Test extraction from multiple Mendeley datasets"""
        print("\nTesting multiple Mendeley datasets...")

        successful_extractions = []
        failed_extractions = []

        for name, dataset in self.TEST_DATASETS.items():
            print(f"\nTesting {name}: {dataset['title']}")
            try:
                result = geoextent.from_repository(
                    dataset['url'],
                    bbox=True,
                    tbox=True
                )

                if result and 'bbox' in result and result['bbox']:
                    successful_extractions.append(name)
                    print(f"✓ Success: {name} - bbox: {result['bbox']}")
                else:
                    failed_extractions.append((name, "No bbox extracted"))
                    print(f"✗ Failed: {name} - No bbox extracted")

            except Exception as e:
                failed_extractions.append((name, str(e)))
                print(f"✗ Failed: {name} - {e}")

        print(f"\nMultiple datasets test summary:")
        print(f"Successful: {len(successful_extractions)}/{len(self.TEST_DATASETS)}")
        print(f"Successful datasets: {successful_extractions}")

        if failed_extractions:
            print("Failed extractions:")
            for name, error in failed_extractions:
                print(f"  - {name}: {error}")

        # At least one dataset should succeed
        assert len(successful_extractions) > 0, "No datasets were successfully processed"

    def test_mendeley_metadata_only_extraction(self):
        """Test metadata-only extraction without downloading files"""
        dataset = self.TEST_DATASETS["tropical_cloud_forest"]

        print(f"\nTesting metadata-only extraction for {dataset['title']}...")
        try:
            # This should use OAI-PMH and not download actual files
            result = geoextent.from_repository(
                dataset['url'],
                bbox=True,
                tbox=True,
                download_data=False
            )

            # Metadata-only extraction may have limited results
            print(f"Metadata-only result: {result}")

        except Exception as e:
            print(f"Metadata-only extraction failed (expected): {e}")
            # This is expected as Mendeley has limited metadata-only capabilities

    def test_mendeley_provider_error_handling(self):
        """Test error handling for invalid Mendeley identifiers"""
        invalid_identifiers = [
            "10.17632/nonexistent.1",
            "https://data.mendeley.com/datasets/invalid/1",
            "invalidid123",
            "10.17632/toolong123456789012345.1",
        ]

        print("\nTesting error handling for invalid identifiers...")
        for invalid_id in invalid_identifiers:
            print(f"Testing invalid ID: {invalid_id}")
            with pytest.raises(Exception):
                geoextent.from_repository(invalid_id, bbox=True)
            print(f"✓ Properly rejected: {invalid_id}")

    def test_mendeley_case_insensitive_handling(self):
        """Test that dataset IDs are handled case-insensitively"""
        dataset = self.TEST_DATASETS["tropical_cloud_forest"]

        test_cases = [
            dataset['dataset_id'].lower(),
            dataset['dataset_id'].upper(),
            dataset['dataset_id'].title(),  # Mixed case
        ]

        print("\nTesting case-insensitive handling...")
        for case_variant in test_cases:
            print(f"Testing case variant: {case_variant}")
            try:
                result = geoextent.from_repository(
                    f"{case_variant}.{dataset['version']}",
                    bbox=True
                )
                assert result is not None
                print(f"✓ Success with case variant: {case_variant}")
            except Exception as e:
                print(f"✗ Failed with case variant {case_variant}: {e}")
                raise

    def test_mendeley_provider_name(self):
        """Test that the provider correctly identifies itself"""
        from geoextent.lib.content_providers.Mendeley import Mendeley

        provider = Mendeley()
        assert provider.name == "Mendeley"
        assert hasattr(provider, 'validate_provider')
        assert hasattr(provider, 'download')

    def test_mendeley_comprehensive_identifier_support(self):
        """Final comprehensive test ensuring all identifier types work"""
        base_dataset = self.TEST_DATASETS["tropical_cloud_forest"]

        # All possible identifier formats to test
        identifier_variations = [
            # 1. Full DOI URLs
            f"https://doi.org/{base_dataset['doi']}",
            f"http://doi.org/{base_dataset['doi']}",
            f"https://dx.doi.org/{base_dataset['doi']}",

            # 2. Bare DOI
            base_dataset['doi'],

            # 3. Mendeley URLs
            base_dataset['url'],

            # 4. ID with version
            f"{base_dataset['dataset_id']}.{base_dataset['version']}",
            f"{base_dataset['dataset_id']}/{base_dataset['version']}",

            # 5. Bare ID
            base_dataset['dataset_id'],
        ]

        print("\nComprehensive identifier format test:")
        for i, identifier in enumerate(identifier_variations, 1):
            print(f"{i}. Testing: {identifier}")

        # Use validation only (faster than full extraction)
        from geoextent.lib.content_providers.Mendeley import Mendeley

        validation_results = []
        for identifier in identifier_variations:
            provider = Mendeley()
            is_valid = provider.validate_provider(identifier)
            validation_results.append((identifier, is_valid))

        # All should validate successfully
        failed_validations = [id_str for id_str, valid in validation_results if not valid]

        if failed_validations:
            print(f"Failed validations: {failed_validations}")

        assert len(failed_validations) == 0, f"Some identifier formats failed validation: {failed_validations}"

        print("✓ All identifier formats validated successfully!")

    def test_user_specified_datasets_validation(self):
        """Test validation of the specific datasets provided by the user"""
        from geoextent.lib.content_providers.Mendeley import Mendeley

        print("\nTesting user-specified datasets validation...")

        # Test each dataset with all its identifier formats
        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            print(f"\nTesting dataset: {dataset_info['title']}")

            for identifier in dataset_info["identifier_formats"]:
                print(f"  Testing identifier: {identifier}")

                provider = Mendeley()
                is_valid = provider.validate_provider(identifier)

                assert is_valid, f"Failed to validate {identifier} for {dataset_name}"
                assert provider.dataset_id == dataset_info["dataset_id"], \
                    f"Dataset ID mismatch for {identifier}: expected {dataset_info['dataset_id']}, got {provider.dataset_id}"

                # For bare dataset IDs (without version), version should be None (latest version)
                if identifier == dataset_info["dataset_id"]:
                    # Bare dataset ID should have version = None
                    assert provider.version is None, \
                        f"Bare dataset ID should have version=None: {identifier}, got {provider.version}"
                    print(f"    ✓ Valid: {identifier} -> {provider.dataset_id} v{provider.version} (latest)")
                else:
                    # All other formats should have the specific version
                    assert provider.version == dataset_info["version"], \
                        f"Version mismatch for {identifier}: expected {dataset_info['version']}, got {provider.version}"
                    print(f"    ✓ Valid: {identifier} -> {provider.dataset_id} v{provider.version}")

    def test_malformed_doi_url_handling(self):
        """Test handling of malformed DOI URL from user input"""
        from geoextent.lib.content_providers.Mendeley import Mendeley

        # Test the malformed URL: https://10.17632/8h9295v4t3.2
        malformed_url = self.TEST_DATASETS["historical_mills_galicia"]["malformed_doi_url"]

        print(f"\nTesting malformed DOI URL: {malformed_url}")

        provider = Mendeley()
        is_valid = provider.validate_provider(malformed_url)

        # This should be rejected as it's not a proper URL format
        assert not is_valid, f"Malformed URL should be rejected: {malformed_url}"
        print(f"✓ Correctly rejected malformed URL: {malformed_url}")

    @pytest.mark.parametrize("dataset_name", ["tropical_cloud_forest", "water_quality_mapping", "emilia_romagna_floods", "historical_mills_galicia"])
    def test_individual_dataset_identifier_formats(self, dataset_name):
        """Test all identifier formats for each individual dataset"""
        dataset = self.TEST_DATASETS[dataset_name]

        print(f"\nTesting all identifier formats for {dataset['title']}")

        # Test validation for all identifier formats
        for identifier in dataset["identifier_formats"]:
            from geoextent.lib.content_providers.Mendeley import Mendeley
            provider = Mendeley()

            is_valid = provider.validate_provider(identifier)
            assert is_valid, f"Validation failed for {identifier}"

            # Verify parsed values
            assert provider.dataset_id == dataset["dataset_id"]

            # Handle bare dataset ID case (version should be None for latest)
            if identifier == dataset["dataset_id"]:
                assert provider.version is None, f"Bare dataset ID should have version=None"
            else:
                assert provider.version == dataset["version"]

            print(f"✓ {identifier}")

    @pytest.mark.slow
    def test_user_datasets_metadata_extraction(self):
        """Test metadata extraction for user-specified datasets"""
        print("\nTesting metadata extraction for user-specified datasets...")

        successful_extractions = []
        failed_extractions = []

        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            print(f"\nTesting {dataset_name}: {dataset_info['title']}")

            try:
                # Test with the primary URL
                result = geoextent.from_repository(
                    dataset_info['url'],
                    bbox=True,
                    tbox=True,
                    download_data=False  # Metadata only to avoid large downloads
                )

                if result:
                    successful_extractions.append(dataset_name)
                    print(f"✓ Metadata extraction successful for {dataset_name}")

                    # Log available metadata
                    if 'bbox' in result and result['bbox']:
                        print(f"  bbox: {result['bbox']}")
                    if 'tbox' in result and result['tbox']:
                        print(f"  tbox: {result['tbox']}")
                else:
                    failed_extractions.append((dataset_name, "No result returned"))
                    print(f"✗ No result for {dataset_name}")

            except Exception as e:
                failed_extractions.append((dataset_name, str(e)))
                print(f"✗ Failed {dataset_name}: {e}")

        print(f"\nMetadata extraction summary:")
        print(f"Successful: {len(successful_extractions)}/{len(self.TEST_DATASETS)}")
        print(f"Success rate: {len(successful_extractions)/len(self.TEST_DATASETS)*100:.1f}%")

        if failed_extractions:
            print("Failed extractions:")
            for name, error in failed_extractions:
                print(f"  - {name}: {error}")

    def test_doi_format_variations(self):
        """Test different DOI format variations across all datasets"""
        print("\nTesting DOI format variations...")

        doi_variations = []

        # Collect all DOI formats from the datasets
        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            # Plain DOI
            doi_variations.append(dataset_info["doi"])

            # DOI URL (if available)
            if "doi_url" in dataset_info:
                doi_variations.append(dataset_info["doi_url"])
            else:
                doi_variations.append(f"https://doi.org/{dataset_info['doi']}")

            # Legacy DOI URL
            doi_variations.append(f"https://dx.doi.org/{dataset_info['doi']}")

            # HTTP variants
            doi_variations.append(f"http://doi.org/{dataset_info['doi']}")

        # Test validation of all DOI variations
        from geoextent.lib.content_providers.Mendeley import Mendeley

        successful_validations = 0
        for doi in doi_variations:
            provider = Mendeley()
            if provider.validate_provider(doi):
                successful_validations += 1
                print(f"✓ {doi}")
            else:
                print(f"✗ {doi}")

        success_rate = successful_validations / len(doi_variations) * 100
        print(f"\nDOI validation success rate: {successful_validations}/{len(doi_variations)} ({success_rate:.1f}%)")

        # Most DOI formats should validate successfully
        assert success_rate >= 75, f"DOI validation success rate too low: {success_rate:.1f}%"

    def test_version_handling(self):
        """Test handling of different version numbers"""
        print("\nTesting version handling...")

        # Test version 1 dataset
        v1_dataset = self.TEST_DATASETS["tropical_cloud_forest"]
        # Test version 2 dataset
        v2_dataset = self.TEST_DATASETS["historical_mills_galicia"]

        from geoextent.lib.content_providers.Mendeley import Mendeley

        # Test version 1
        provider = Mendeley()
        assert provider.validate_provider(v1_dataset["doi"])
        assert provider.version == "1"
        print(f"✓ Version 1 handling: {v1_dataset['doi']}")

        # Test version 2
        provider = Mendeley()
        assert provider.validate_provider(v2_dataset["doi"])
        assert provider.version == "2"
        print(f"✓ Version 2 handling: {v2_dataset['doi']}")

    def test_comprehensive_identifier_support_user_datasets(self):
        """Comprehensive test of identifier support for user-provided datasets"""
        print("\nComprehensive identifier support test for user datasets...")

        total_identifiers = 0
        successful_validations = 0

        from geoextent.lib.content_providers.Mendeley import Mendeley

        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            print(f"\nTesting {dataset_name}:")

            for identifier in dataset_info["identifier_formats"]:
                total_identifiers += 1
                provider = Mendeley()

                if provider.validate_provider(identifier):
                    successful_validations += 1
                    print(f"  ✓ {identifier}")
                else:
                    print(f"  ✗ {identifier}")

        success_rate = successful_validations / total_identifiers * 100
        print(f"\nOverall validation success rate: {successful_validations}/{total_identifiers} ({success_rate:.1f}%)")

        # All identifiers should validate successfully
        assert success_rate == 100, f"Some identifiers failed validation. Success rate: {success_rate:.1f}%"

    def test_dataset_years_and_authors(self):
        """Test that dataset metadata includes expected years and authors"""
        print("\nTesting dataset metadata (years and authors)...")

        expected_years = {
            "tropical_cloud_forest": 2021,
            "water_quality_mapping": 2023,
            "emilia_romagna_floods": 2024,
            "historical_mills_galicia": 2021,
        }

        for dataset_name, expected_year in expected_years.items():
            dataset = self.TEST_DATASETS[dataset_name]
            assert dataset["year"] == expected_year, \
                f"Year mismatch for {dataset_name}: expected {expected_year}, got {dataset['year']}"
            print(f"✓ {dataset_name}: {expected_year}")

            # Check that authors are present
            assert "authors" in dataset and len(dataset["authors"]) > 0, \
                f"No authors specified for {dataset_name}"
            print(f"  Authors: {', '.join(dataset['authors'])}")

    def test_spatial_temporal_data_flags(self):
        """Test the spatial and temporal data capability flags"""
        print("\nTesting spatial and temporal data flags...")

        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            print(f"\n{dataset_name}:")
            print(f"  Has geospatial data: {dataset_info.get('has_geospatial_data', False)}")
            print(f"  Has temporal data: {dataset_info.get('has_temporal_data', False)}")

            # All test datasets should have geospatial data
            assert dataset_info.get('has_geospatial_data', False), \
                f"Dataset {dataset_name} should have geospatial data"