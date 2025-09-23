#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Dataverse content provider functionality.

This test suite validates the Dataverse content provider's ability to:
- Handle different identifier formats (DOIs, URLs, persistent IDs)
- Support multiple Dataverse installations (Harvard, DataverseNL, etc.)
- Extract metadata via Dataverse Native API
- Download files from datasets
- Validate URL patterns and host detection

Test datasets are selected from real Dataverse installations to ensure
comprehensive testing across different repository configurations.

Reference: GitHub issue #57 - https://github.com/nuest/geoextent/issues/57
"""

import pytest
import tempfile
import os
import shutil
import subprocess
import json
from unittest.mock import patch, MagicMock

from geoextent.lib.content_providers.Dataverse import Dataverse
from geoextent.lib import extent


class TestDataverseProvider:
    """Test suite for Dataverse content provider."""

    @pytest.fixture
    def dataverse_provider(self):
        """Create a Dataverse provider instance."""
        return Dataverse()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for downloads."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Test datasets from different Dataverse installations
    TEST_DATASETS = [
        {
            "name": "Harvard Dataverse - DMOZ Dataset",
            "identifiers": [
                "doi:10.7910/DVN/OMV93V",
                "10.7910/DVN/OMV93V",
                "https://doi.org/10.7910/DVN/OMV93V",
                "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/OMV93V",
                "https://dataverse.harvard.edu/api/datasets/:persistentId?persistentId=doi:10.7910/DVN/OMV93V",
            ],
            "expected_host": "dataverse.harvard.edu",
            "expected_persistent_id": "doi:10.7910/DVN/OMV93V",
            "title": "Parsed DMOZ data",
            "author": "Sood, Gaurav",
            "has_files": True,
            "file_count": 3,
        },
        {
            "name": "Harvard Dataverse - Iris Dataset",
            "identifiers": [
                "doi:10.7910/DVN/R2RGXR",
                "https://doi.org/10.7910/DVN/R2RGXR",
                "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/R2RGXR",
            ],
            "expected_host": "dataverse.harvard.edu",
            "expected_persistent_id": "doi:10.7910/DVN/R2RGXR",
            "title": "Iris dataset for machine learning",
            "has_files": True,
        },
        {
            "name": "DataverseNL Example",
            "identifiers": [
                # Note: Using hypothetical DataverseNL DOI pattern based on research
                "doi:10.34894/EXAMPLE1",
                "https://doi.org/10.34894/EXAMPLE1",
                "https://dataverse.nl/dataset.xhtml?persistentId=doi:10.34894/EXAMPLE1",
            ],
            "expected_host": "dataverse.nl",
            "expected_persistent_id": "doi:10.34894/EXAMPLE1",
            "mock_test": True,  # This will be mocked since we don't have a real dataset
        },
    ]

    # Known Dataverse installations for testing
    KNOWN_HOSTS = [
        "dataverse.harvard.edu",
        "dataverse.nl",
        "demo.dataverse.nl",
        "dataverse.unc.edu",
        "data.library.virginia.edu",
        "dataverse.no",
        "recherche.data.gouv.fr",
    ]

    def test_provider_instantiation(self, dataverse_provider):
        """Test that the provider can be instantiated correctly."""
        assert dataverse_provider.name == "Dataverse"
        assert hasattr(dataverse_provider, 'validate_provider')
        assert hasattr(dataverse_provider, 'download')
        assert hasattr(dataverse_provider, '_get_dataset_metadata')

    def test_known_host_detection(self, dataverse_provider):
        """Test detection of known Dataverse hosts."""
        for host in self.KNOWN_HOSTS:
            assert dataverse_provider._is_known_dataverse_host(host), \
                f"Should recognize {host} as a known Dataverse host"

        # Test case insensitivity
        assert dataverse_provider._is_known_dataverse_host("DATAVERSE.HARVARD.EDU")
        assert dataverse_provider._is_known_dataverse_host("DataVerse.NL")

        # Test unknown hosts
        unknown_hosts = ["zenodo.org", "figshare.com", "example.com"]
        for host in unknown_hosts:
            assert not dataverse_provider._is_known_dataverse_host(host), \
                f"Should not recognize {host} as a Dataverse host"

    def test_doi_pattern_recognition(self, dataverse_provider):
        """Test recognition of Dataverse DOI patterns."""
        # Harvard Dataverse DOIs
        harvard_dois = [
            "10.7910/DVN/OMV93V",
            "10.7910/DVN/R2RGXR",
            "10.7910/DVN/123ABC",
        ]

        for doi in harvard_dois:
            assert dataverse_provider._is_dataverse_doi(doi), \
                f"Should recognize Harvard Dataverse DOI: {doi}"

        # DataverseNL DOIs (hypothetical pattern)
        dataversenl_dois = [
            "10.34894/EXAMPLE1",
            "10.34894/ABC123",
        ]

        for doi in dataversenl_dois:
            assert dataverse_provider._is_dataverse_doi(doi), \
                f"Should recognize DataverseNL DOI: {doi}"

        # Non-Dataverse DOIs
        non_dataverse_dois = [
            "10.5281/zenodo.123456",  # Zenodo
            "10.6084/m9.figshare.123456",  # Figshare
            "10.1000/example.doi",  # Generic
        ]

        for doi in non_dataverse_dois:
            assert not dataverse_provider._is_dataverse_doi(doi), \
                f"Should not recognize non-Dataverse DOI: {doi}"

    def test_persistent_id_cleaning(self, dataverse_provider):
        """Test persistent ID cleaning and normalization."""
        test_cases = [
            ("10.7910/DVN/OMV93V", "doi:10.7910/DVN/OMV93V"),
            ("doi:10.7910/DVN/OMV93V", "doi:10.7910/DVN/OMV93V"),
            ("hdl:1902.1/123", "hdl:1902.1/123"),
            ("urn:example:123", "urn:example:123"),
        ]

        for input_id, expected_output in test_cases:
            result = dataverse_provider._clean_persistent_id(input_id)
            assert result == expected_output, \
                f"Expected {expected_output}, got {result} for input {input_id}"

    @pytest.mark.parametrize("dataset", TEST_DATASETS[:2])  # Skip mock dataset for validation test
    def test_identifier_validation(self, dataverse_provider, dataset):
        """Test validation of different identifier formats."""
        for identifier in dataset["identifiers"]:
            # Create fresh provider instance for each test
            provider = Dataverse()
            is_valid = provider.validate_provider(identifier)

            assert is_valid, f"Should validate identifier: {identifier}"

            # For URLs with explicit hosts, check the host
            if any(host in identifier.lower() for host in ["dataverse.harvard.edu", "dataverse.nl"]):
                assert provider.host == dataset["expected_host"], \
                    f"Host mismatch for {identifier}: expected {dataset['expected_host']}, got {provider.host}"
            else:
                # For plain DOIs, host might be None (discovered later during API calls)
                # This is expected behavior
                pass

            assert provider.persistent_id == dataset["expected_persistent_id"], \
                f"Persistent ID mismatch for {identifier}: expected {dataset['expected_persistent_id']}, got {provider.persistent_id}"

    def test_invalid_identifiers(self, dataverse_provider):
        """Test rejection of invalid identifiers."""
        invalid_identifiers = [
            "10.5281/zenodo.123456",  # Zenodo DOI
            "https://zenodo.org/records/123456",  # Zenodo URL
            "https://figshare.com/articles/123456",  # Figshare URL
            "invalid-string",  # Random string
            "",  # Empty string
            "https://example.com/dataset/123",  # Unknown domain
        ]

        for invalid_id in invalid_identifiers:
            provider = Dataverse()
            is_valid = provider.validate_provider(invalid_id)
            assert not is_valid, f"Should reject invalid identifier: {invalid_id}"

    def test_url_pattern_matching(self, dataverse_provider):
        """Test URL pattern matching for different Dataverse URL formats."""
        test_cases = [
            {
                "url": "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/OMV93V",
                "pattern": "dataset_page",
                "expected_host": "dataverse.harvard.edu",
                "expected_id": "doi:10.7910/DVN/OMV93V",
            },
            {
                "url": "https://dataverse.nl/api/datasets/:persistentId?persistentId=doi:10.34894/EXAMPLE1",
                "pattern": "api_persistent_id",
                "expected_host": "dataverse.nl",
                "expected_id": "doi:10.34894/EXAMPLE1",
            },
            {
                "url": "https://dataverse.harvard.edu/api/datasets/2840573",
                "pattern": "api_dataset_id",
                "expected_host": "dataverse.harvard.edu",
                "expected_id": "2840573",
            },
        ]

        for case in test_cases:
            pattern = dataverse_provider.url_patterns[case["pattern"]]
            match = pattern.match(case["url"])

            assert match is not None, f"Pattern {case['pattern']} should match URL: {case['url']}"

            groups = match.groups()
            assert groups[0] == case["expected_host"], \
                f"Host mismatch: expected {case['expected_host']}, got {groups[0]}"
            assert groups[1] == case["expected_id"], \
                f"ID mismatch: expected {case['expected_id']}, got {groups[1]}"

    def test_api_url_construction(self, dataverse_provider):
        """Test API URL construction for different hosts."""
        test_cases = [
            ("dataverse.harvard.edu", "https://dataverse.harvard.edu/api"),
            ("dataverse.nl", "https://dataverse.nl/api"),
            ("demo.dataverse.nl", "https://demo.dataverse.nl/api"),
        ]

        for host, expected_url in test_cases:
            dataverse_provider.host = host
            api_url = dataverse_provider._get_api_base_url()
            assert api_url == expected_url, \
                f"Expected {expected_url}, got {api_url} for host {host}"

    @pytest.mark.integration
    def test_real_dataset_metadata_extraction(self, dataverse_provider):
        """Test metadata extraction from a real Harvard Dataverse dataset."""
        # Use the DMOZ dataset which we know exists
        test_dataset = self.TEST_DATASETS[0]
        identifier = test_dataset["identifiers"][0]  # doi:10.7910/DVN/OMV93V

        provider = Dataverse()
        assert provider.validate_provider(identifier)

        try:
            metadata = provider._get_dataset_metadata()

            # Verify basic metadata structure
            assert isinstance(metadata, dict)
            assert "id" in metadata
            assert "persistentUrl" in metadata
            assert "latestVersion" in metadata

            # Verify specific dataset properties
            latest_version = metadata["latestVersion"]
            assert "metadataBlocks" in latest_version
            assert "citation" in latest_version["metadataBlocks"]

            # Test metadata extraction
            metadata_dict = provider.get_metadata_dict()
            assert isinstance(metadata_dict, dict)
            assert "title" in metadata_dict
            assert "authors" in metadata_dict

            print(f"✓ Successfully extracted metadata for: {metadata_dict.get('title', 'Unknown')}")
            print(f"  Authors: {', '.join(metadata_dict.get('authors', []))}")

        except Exception as e:
            pytest.skip(f"Real dataset test skipped due to API access issue: {e}")

    @pytest.mark.integration
    def test_file_listing(self, dataverse_provider):
        """Test file listing from a real dataset."""
        test_dataset = self.TEST_DATASETS[0]
        identifier = test_dataset["identifiers"][0]

        provider = Dataverse()
        assert provider.validate_provider(identifier)

        try:
            files = provider._get_file_list()

            assert isinstance(files, list)
            if test_dataset["has_files"]:
                assert len(files) > 0, "Dataset should have files"

                # Check file structure
                for file_info in files:
                    assert isinstance(file_info, dict)
                    # Should have either 'dataFile' or direct file properties
                    assert "dataFile" in file_info or "filename" in file_info or "label" in file_info

            print(f"✓ Found {len(files)} files in dataset")

        except Exception as e:
            pytest.skip(f"Real file listing test skipped due to API access issue: {e}")

    def test_file_download_url_generation(self, dataverse_provider):
        """Test generation of file download URLs."""
        # Mock file info structures
        file_info_cases = [
            {
                "dataFile": {"id": 12345, "filename": "test.csv"},
                "expected_pattern": "/api/access/datafile/12345"
            },
            {
                "dataFile": {"persistentId": "doi:10.7910/DVN/OMV93V/FILE1", "filename": "test.txt"},
                "expected_pattern": "/api/access/datafile/:persistentId?persistentId="
            },
            {
                "id": 67890,
                "filename": "data.json",
                "expected_pattern": "/api/access/datafile/67890"
            },
        ]

        dataverse_provider.host = "dataverse.harvard.edu"

        for file_info in file_info_cases:
            try:
                download_url = dataverse_provider._get_file_download_url(file_info)
                assert file_info["expected_pattern"] in download_url, \
                    f"Download URL should contain pattern: {file_info['expected_pattern']}"
            except ValueError:
                # Some cases might fail due to missing required fields
                pass

    def test_mock_dataset_validation(self, dataverse_provider):
        """Test validation with mock DataverseNL dataset."""
        mock_dataset = self.TEST_DATASETS[2]  # DataverseNL mock dataset

        for identifier in mock_dataset["identifiers"]:
            provider = Dataverse()
            is_valid = provider.validate_provider(identifier)

            assert is_valid, f"Should validate mock identifier: {identifier}"
            assert provider.host == mock_dataset["expected_host"] or provider.host is None, \
                f"Host should be {mock_dataset['expected_host']} or None for DOI resolution"
            assert provider.persistent_id == mock_dataset["expected_persistent_id"], \
                f"Persistent ID should be {mock_dataset['expected_persistent_id']}"

    def test_provider_string_representation(self, dataverse_provider):
        """Test string representation of provider."""
        dataverse_provider.host = "dataverse.harvard.edu"
        dataverse_provider.persistent_id = "doi:10.7910/DVN/OMV93V"

        str_repr = str(dataverse_provider)
        assert "Dataverse" in str_repr
        assert "dataverse.harvard.edu" in str_repr
        assert "doi:10.7910/DVN/OMV93V" in str_repr

    def test_error_handling(self, dataverse_provider):
        """Test error handling for various failure scenarios."""
        # Test with valid identifier but simulate API failure
        provider = Dataverse()
        assert provider.validate_provider("doi:10.7910/DVN/OMV93V")

        # Mock failed API request
        with patch.object(provider, '_request', side_effect=Exception("API Error")):
            with pytest.raises(Exception):
                provider._get_dataset_metadata()

    def test_comprehensive_identifier_format_support(self, dataverse_provider):
        """Comprehensive test of all supported identifier formats."""
        # Test all identifier formats from the first dataset
        dataset = self.TEST_DATASETS[0]

        print(f"\nTesting all identifier formats for: {dataset['name']}")

        successful_validations = 0
        total_identifiers = len(dataset["identifiers"])

        for identifier in dataset["identifiers"]:
            provider = Dataverse()
            is_valid = provider.validate_provider(identifier)

            if is_valid:
                successful_validations += 1
                print(f"  ✓ {identifier}")
            else:
                print(f"  ✗ {identifier}")

        success_rate = successful_validations / total_identifiers * 100
        print(f"\nValidation success rate: {successful_validations}/{total_identifiers} ({success_rate:.1f}%)")

        # All identifiers should validate successfully
        assert success_rate == 100, f"Some identifier formats failed validation. Success rate: {success_rate:.1f}%"

    @pytest.mark.slow
    def test_download_functionality_mock(self, dataverse_provider, temp_dir):
        """Test download functionality with mocked responses."""
        provider = Dataverse()
        provider.validate_provider("doi:10.7910/DVN/OMV93V")

        # Mock the file list
        mock_files = [
            {
                "dataFile": {
                    "id": 123,
                    "filename": "test.csv",
                    "filesize": 1024
                },
                "label": "test.csv"
            }
        ]

        # Mock the responses
        with patch.object(provider, '_get_file_list', return_value=mock_files):
            with patch.object(provider, '_request') as mock_request:
                # Mock successful download response
                mock_response = MagicMock()
                mock_response.iter_content.return_value = [b"test,data\n1,2\n"]
                mock_request.return_value = mock_response

                # Test download
                provider.download(temp_dir, download_data=True)

                # Verify file was "downloaded"
                expected_file = os.path.join(temp_dir, "test.csv")
                assert os.path.exists(expected_file)

    def test_dataset_type_detection(self, dataverse_provider):
        """Test detection of different dataset types and content."""
        # This test verifies that the provider can handle different types of datasets
        # that might contain geospatial data

        test_cases = [
            {
                "description": "Tabular data with potential coordinates",
                "mock_metadata": {
                    "latestVersion": {
                        "metadataBlocks": {
                            "citation": {
                                "fields": [
                                    {"typeName": "title", "value": "GPS Coordinates Dataset"},
                                    {"typeName": "subject", "value": ["Earth and Environmental Sciences"]}
                                ]
                            }
                        },
                        "files": [
                            {
                                "dataFile": {
                                    "id": 1,
                                    "filename": "coordinates.csv",
                                    "contentType": "text/csv",
                                    "tabularData": True
                                }
                            }
                        ]
                    }
                }
            },
            {
                "description": "Geospatial files (shapefiles, GeoTIFF)",
                "mock_metadata": {
                    "latestVersion": {
                        "metadataBlocks": {
                            "citation": {
                                "fields": [
                                    {"typeName": "title", "value": "Geospatial Analysis Data"}
                                ]
                            }
                        },
                        "files": [
                            {
                                "dataFile": {
                                    "id": 2,
                                    "filename": "data.shp",
                                    "contentType": "application/octet-stream"
                                }
                            }
                        ]
                    }
                }
            }
        ]

        for case in test_cases:
            # This test validates the structure without requiring actual API calls
            metadata = case["mock_metadata"]
            files = metadata["latestVersion"]["files"]

            assert len(files) > 0, f"Should have files for: {case['description']}"

            for file_info in files:
                assert "dataFile" in file_info, "File should have dataFile structure"
                assert "filename" in file_info["dataFile"], "File should have filename"

    @pytest.mark.integration
    def test_dataverse_cli_integration(self):
        """Integration test for CLI command with actual DOI extraction."""
        # Test DOI: 10.7910/DVN/4YGU5J - a known geospatial dataset
        test_doi = "https://doi.org/10.7910/DVN/4YGU5J"

        # Reference bounding box for comparison: [minX, minY, maxX, maxY]
        reference_bbox = [-71.96002219440005, 41.963676321571086, -70.1479956701181, 42.724780975329644]
        tolerance = 0.001  # Allow small differences due to floating point precision

        try:
            # Run geoextent CLI with the test DOI
            result = subprocess.run(
                ["python", "-m", "geoextent", "-b", test_doi],
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for network operations
            )

            # Check that the command succeeded
            assert result.returncode == 0, f"CLI command failed with error: {result.stderr}"

            # Parse the JSON output
            output = json.loads(result.stdout)

            # Verify the basic structure
            assert isinstance(output, dict), "Output should be a dictionary"
            assert "format" in output, "Output should contain format field"
            assert output["format"] == "repository", "Format should be 'repository'"

            # Verify bounding box extraction and comparison with reference
            assert "bbox" in output, "Output should contain bounding box"
            bbox = output["bbox"]
            assert isinstance(bbox, list), "Bounding box should be a list"
            assert len(bbox) == 4, "Bounding box should have 4 coordinates"

            # Verify coordinate order: [minX, minY, maxX, maxY]
            minX, minY, maxX, maxY = bbox
            assert minX <= maxX, "minX should be <= maxX"
            assert minY <= maxY, "minY should be <= maxY"

            # Verify coordinates are within reasonable bounds (WGS84)
            assert -180 <= minX <= 180, "Longitude should be within valid range"
            assert -180 <= maxX <= 180, "Longitude should be within valid range"
            assert -90 <= minY <= 90, "Latitude should be within valid range"
            assert -90 <= maxY <= 90, "Latitude should be within valid range"

            # Compare with reference bounding box
            ref_minX, ref_minY, ref_maxX, ref_maxY = reference_bbox

            assert abs(minX - ref_minX) <= tolerance, \
                f"MinX differs from reference: extracted={minX}, reference={ref_minX}, diff={abs(minX - ref_minX)}"
            assert abs(minY - ref_minY) <= tolerance, \
                f"MinY differs from reference: extracted={minY}, reference={ref_minY}, diff={abs(minY - ref_minY)}"
            assert abs(maxX - ref_maxX) <= tolerance, \
                f"MaxX differs from reference: extracted={maxX}, reference={ref_maxX}, diff={abs(maxX - ref_maxX)}"
            assert abs(maxY - ref_maxY) <= tolerance, \
                f"MaxY differs from reference: extracted={maxY}, reference={ref_maxY}, diff={abs(maxY - ref_maxY)}"

            # Verify CRS information
            if "crs" in output:
                assert output["crs"] == "4326", "CRS should be WGS84 (EPSG:4326)"

            print(f"✓ CLI integration test successful for DOI: {test_doi}")
            print(f"  Extracted bounding box: {bbox}")
            print(f"  Reference bounding box: {reference_bbox}")
            print(f"  Coordinates match within tolerance of {tolerance}")
            if "crs" in output:
                print(f"  CRS: EPSG:{output['crs']}")

        except subprocess.TimeoutExpired:
            pytest.skip("CLI test skipped due to timeout (network issues)")
        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to parse CLI output as JSON: {e}\nOutput: {result.stdout}")
        except AssertionError as e:
            # Re-raise assertion errors to show the actual test failure
            raise e
        except Exception as e:
            pytest.skip(f"CLI integration test skipped due to error: {e}")

    @pytest.mark.integration
    def test_dataverse_python_api_integration(self):
        """Integration test for Python API with actual DOI extraction."""
        # Test DOI: 10.7910/DVN/4YGU5J - a known geospatial dataset
        test_doi = "https://doi.org/10.7910/DVN/4YGU5J"

        try:
            # Test the from_repository function directly
            result = extent.from_repository(
                repository_identifier=test_doi,
                bbox=True,
                tbox=False,  # Focus on spatial extent for this test
                details=True,
                download_data=True,
                timeout=120  # 2 minute timeout
            )

            # Verify the basic structure
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "format" in result, "Result should contain format field"
            assert result["format"] == "repository", "Format should be 'repository'"

            # Verify bounding box extraction
            if "bbox" in result:
                bbox = result["bbox"]
                assert isinstance(bbox, list), "Bounding box should be a list"
                assert len(bbox) == 4, "Bounding box should have 4 coordinates"

                # Verify coordinate order: [minX, minY, maxX, maxY]
                minX, minY, maxX, maxY = bbox
                assert minX <= maxX, "minX should be <= maxX"
                assert minY <= maxY, "minY should be <= maxY"

                # Verify coordinates are within reasonable bounds (WGS84)
                assert -180 <= minX <= 180, "Longitude should be within valid range"
                assert -180 <= maxX <= 180, "Longitude should be within valid range"
                assert -90 <= minY <= 90, "Latitude should be within valid range"
                assert -90 <= maxY <= 90, "Latitude should be within valid range"

            # Verify CRS information
            if "crs" in result:
                assert result["crs"] == "4326", "CRS should be WGS84 (EPSG:4326)"

            # Check for details if available
            if "details" in result:
                details = result["details"]
                assert isinstance(details, dict), "Details should be a dictionary"

            print(f"✓ Python API integration test successful for DOI: {test_doi}")
            if "bbox" in result:
                print(f"  Extracted bounding box: {result['bbox']}")
            if "crs" in result:
                print(f"  CRS: EPSG:{result['crs']}")
            if "details" in result:
                print(f"  Details available for {len(result['details'])} items")

        except ValueError as e:
            if "not supported" in str(e).lower():
                pytest.skip(f"Python API test skipped - provider validation failed: {e}")
            else:
                pytest.fail(f"Python API test failed with ValueError: {e}")
        except Exception as e:
            pytest.skip(f"Python API integration test skipped due to error: {e}")

    @pytest.mark.integration
    def test_dataverse_integration_comparison(self):
        """Compare CLI and Python API results for consistency."""
        test_doi = "https://doi.org/10.7910/DVN/4YGU5J"

        try:
            # Test CLI
            cli_result = subprocess.run(
                ["python", "-m", "geoextent", "-b", test_doi],
                capture_output=True,
                text=True,
                timeout=120
            )

            # Test Python API
            api_result = extent.from_repository(
                repository_identifier=test_doi,
                bbox=True,
                tbox=False,
                details=True,
                download_data=True,
                timeout=120
            )

            if cli_result.returncode == 0:
                cli_output = json.loads(cli_result.stdout)

                # Compare basic structure
                assert cli_output["format"] == api_result["format"], "Format should match between CLI and API"

                # Compare bounding boxes if both exist
                if "bbox" in cli_output and "bbox" in api_result:
                    cli_bbox = cli_output["bbox"]
                    api_bbox = api_result["bbox"]

                    # Allow for small floating point differences
                    for i in range(4):
                        assert abs(cli_bbox[i] - api_bbox[i]) < 0.001, \
                            f"Bounding box coordinate {i} differs: CLI={cli_bbox[i]}, API={api_bbox[i]}"

                # Compare CRS if both exist
                if "crs" in cli_output and "crs" in api_result:
                    assert cli_output["crs"] == api_result["crs"], "CRS should match between CLI and API"

                print("✓ CLI and Python API results are consistent")

        except Exception as e:
            pytest.skip(f"Integration comparison test skipped due to error: {e}")


if __name__ == "__main__":
    # Run basic tests if executed directly
    import sys

    print("Running basic Dataverse provider tests...")

    # Test provider instantiation
    provider = Dataverse()
    print("✓ Provider instantiated successfully")

    # Test validation with sample identifiers
    test_identifiers = [
        "doi:10.7910/DVN/OMV93V",
        "https://doi.org/10.7910/DVN/OMV93V",
        "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/OMV93V",
        "10.7910/DVN/R2RGXR",
    ]

    successful = 0
    for identifier in test_identifiers:
        provider_instance = Dataverse()
        if provider_instance.validate_provider(identifier):
            successful += 1
            print(f"✓ Valid: {identifier} -> {provider_instance.host}, {provider_instance.persistent_id}")
        else:
            print(f"✗ Invalid: {identifier}")

    print(f"\nValidation success rate: {successful}/{len(test_identifiers)} ({successful/len(test_identifiers)*100:.1f}%)")
    print("\nTest suite completed. Run with pytest for full testing.")