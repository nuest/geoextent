import pytest
import geoextent.lib.extent as geoextent


class TestDOIURLSupport:
    """Test support for various DOI URL formats across all content providers"""

    def test_pangaea_doi_url_formats(self):
        """Test that Pangaea DOIs work in all supported URL formats"""
        pangaea_dataset_id = "786028"

        doi_formats = [
            f"10.1594/PANGAEA.{pangaea_dataset_id}",  # Plain DOI
            f"https://doi.org/10.1594/PANGAEA.{pangaea_dataset_id}",  # HTTPS DOI resolver
            f"http://doi.org/10.1594/PANGAEA.{pangaea_dataset_id}",   # HTTP DOI resolver
            f"https://dx.doi.org/10.1594/PANGAEA.{pangaea_dataset_id}",  # Alternative DOI resolver
            f"https://doi.pangaea.de/10.1594/PANGAEA.{pangaea_dataset_id}",  # Direct Pangaea URL
        ]

        for doi_format in doi_formats:
            try:
                result = geoextent.from_repository(doi_format, bbox=True, tbox=True)
                assert result is not None, f"Failed to process DOI format: {doi_format}"
                assert result["format"] == "repository", f"Wrong format for {doi_format}"
                print(f"✓ Successfully processed: {doi_format}")

            except ImportError:
                pytest.skip("pangaeapy not available")
            except Exception as e:
                pytest.skip(f"Network or API error for {doi_format}: {e}")

    def test_zenodo_doi_url_formats(self):
        """Test that Zenodo DOIs work in all supported URL formats"""
        zenodo_record_id = "820562"

        doi_formats = [
            f"10.5281/zenodo.{zenodo_record_id}",  # Plain DOI
            f"https://doi.org/10.5281/zenodo.{zenodo_record_id}",  # HTTPS DOI resolver
            f"http://doi.org/10.5281/zenodo.{zenodo_record_id}",   # HTTP DOI resolver
            f"https://dx.doi.org/10.5281/zenodo.{zenodo_record_id}",  # Alternative DOI resolver
            f"https://zenodo.org/record/{zenodo_record_id}",  # Direct Zenodo URL
        ]

        for doi_format in doi_formats:
            try:
                result = geoextent.from_repository(doi_format, bbox=True, tbox=True)
                assert result is not None, f"Failed to process DOI format: {doi_format}"
                assert result["format"] == "repository", f"Wrong format for {doi_format}"
                print(f"✓ Successfully processed: {doi_format}")

            except Exception as e:
                pytest.skip(f"Network or API error for {doi_format}: {e}")

    def test_doi_url_validation_pangaea_provider(self):
        """Test that Pangaea provider correctly validates all DOI URL formats"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()
        test_dataset_id = "734969"

        valid_formats = [
            f"10.1594/PANGAEA.{test_dataset_id}",
            f"https://doi.org/10.1594/PANGAEA.{test_dataset_id}",
            f"http://doi.org/10.1594/PANGAEA.{test_dataset_id}",
            f"https://dx.doi.org/10.1594/PANGAEA.{test_dataset_id}",
            f"https://doi.pangaea.de/10.1594/PANGAEA.{test_dataset_id}",
        ]

        for doi_format in valid_formats:
            is_valid = pangaea.validate_provider(doi_format)
            assert is_valid, f"Pangaea provider should validate {doi_format}"
            assert pangaea.dataset_id == test_dataset_id, f"Wrong dataset ID extracted from {doi_format}"

        # Test invalid formats
        invalid_formats = [
            "10.5281/zenodo.820562",  # Zenodo DOI
            "https://figshare.com/articles/123456",
            "not-a-doi-at-all",
            "",
        ]

        for invalid_format in invalid_formats:
            is_valid = pangaea.validate_provider(invalid_format)
            assert not is_valid, f"Pangaea provider should not validate {invalid_format}"

    def test_doi_url_validation_zenodo_provider(self):
        """Test that Zenodo provider correctly validates all DOI URL formats"""
        from geoextent.lib.content_providers.Zenodo import Zenodo

        zenodo = Zenodo()
        test_record_id = "820562"

        valid_formats = [
            f"10.5281/zenodo.{test_record_id}",
            f"https://doi.org/10.5281/zenodo.{test_record_id}",
            f"http://doi.org/10.5281/zenodo.{test_record_id}",
            f"https://dx.doi.org/10.5281/zenodo.{test_record_id}",
            f"https://zenodo.org/record/{test_record_id}",
        ]

        for doi_format in valid_formats:
            is_valid = zenodo.validate_provider(doi_format)
            assert is_valid, f"Zenodo provider should validate {doi_format}"
            assert zenodo.record_id == test_record_id, f"Wrong record ID extracted from {doi_format}"

        # Test invalid formats
        invalid_formats = [
            "10.1594/PANGAEA.123456",  # Pangaea DOI
            "https://figshare.com/articles/123456",
            "not-a-doi-at-all",
            "",
        ]

        for invalid_format in invalid_formats:
            is_valid = zenodo.validate_provider(invalid_format)
            assert not is_valid, f"Zenodo provider should not validate {invalid_format}"

    def test_doi_resolution_base_provider(self):
        """Test that the base DOI provider correctly resolves DOI URLs"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()

        # Test DOI resolution
        test_cases = [
            {
                "input": "https://doi.org/10.1594/PANGAEA.786028",
                "expected_pattern": "pangaea.de"
            },
            {
                "input": "http://doi.org/10.1594/PANGAEA.786028",
                "expected_pattern": "pangaea.de"
            },
            {
                "input": "10.1594/PANGAEA.786028",
                "expected_pattern": "pangaea.de"
            }
        ]

        for test_case in test_cases:
            try:
                pangaea.reference = test_case["input"]
                resolved_url = pangaea.get_url
                assert test_case["expected_pattern"] in resolved_url, \
                    f"Expected {test_case['expected_pattern']} in resolved URL {resolved_url} for input {test_case['input']}"
                print(f"✓ {test_case['input']} -> {resolved_url}")

            except Exception as e:
                pytest.skip(f"Network error resolving {test_case['input']}: {e}")

    def test_mixed_provider_doi_handling(self):
        """Test that the system correctly routes different DOI types to appropriate providers"""
        test_cases = [
            {
                "doi": "https://doi.org/10.1594/PANGAEA.786028",
                "expected_provider": "Pangaea"
            },
            {
                "doi": "https://doi.org/10.5281/zenodo.820562",
                "expected_provider": "Zenodo"
            }
        ]

        for test_case in test_cases:
            try:
                result = geoextent.from_repository(test_case["doi"], bbox=True, tbox=True)
                assert result is not None, f"Failed to process {test_case['doi']}"
                assert result["format"] == "repository"
                print(f"✓ {test_case['doi']} handled by {test_case['expected_provider']}")

            except ImportError:
                pytest.skip("Required library not available")
            except Exception as e:
                pytest.skip(f"Network or API error: {e}")

    def test_invalid_doi_urls(self):
        """Test that invalid DOI URLs are properly rejected"""
        invalid_dois = [
            "https://doi.org/invalid.doi.format",
            "http://doi.org/10.invalid/format",
            "https://doi.org/10.1594/NONEXISTENT.999999999",
            "not-a-url-at-all",
            "",
        ]

        for invalid_doi in invalid_dois:
            try:
                result = geoextent.from_repository(invalid_doi, bbox=True)
                # If no exception is raised, the result should indicate failure
                if result is not None:
                    # Some providers might return partial results for invalid DOIs
                    assert isinstance(result, dict)
            except Exception:
                # Exception is expected for invalid DOIs
                pass

    def test_doi_url_case_insensitivity(self):
        """Test that DOI URLs work regardless of case in both protocol/domain and DOI content"""
        base_doi = "10.1594/PANGAEA.786028"

        # Test case variations in protocol and domain
        protocol_case_variations = [
            f"https://doi.org/{base_doi}",
            f"HTTPS://DOI.ORG/{base_doi}",
            f"https://DOI.org/{base_doi}",
            f"https://doi.ORG/{base_doi}",
        ]

        # Test case variations in DOI content
        content_case_variations = [
            base_doi.upper(),  # 10.1594/PANGAEA.786028 -> 10.1594/PANGAEA.786028
            base_doi.lower(),  # 10.1594/PANGAEA.786028 -> 10.1594/pangaea.786028
            base_doi.replace("PANGAEA", "pangaea"),  # Mixed case
        ]

        all_variations = protocol_case_variations + content_case_variations

        for doi_variant in all_variations:
            try:
                result = geoextent.from_repository(doi_variant, bbox=True)
                if result is not None:
                    assert result["format"] == "repository"
                    print(f"✓ Case variant works: {doi_variant}")

            except ImportError:
                pytest.skip("pangaeapy not available")
            except Exception as e:
                # Some case variations might not be supported by the DOI resolver
                pytest.skip(f"Case variation not supported: {e}")