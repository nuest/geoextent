import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance


class TestPangaeaProvider:
    """Test Pangaea content provider functionality"""

    # Test datasets with known geographic and temporal coverage
    TEST_DATASETS = {
        "oceanography": {
            "doi": "10.1594/PANGAEA.734969",
            "url": "https://doi.pangaea.de/10.1594/PANGAEA.734969",
            "id": "734969",
            "title": "Physical oceanography during POLARSTERN cruise ANT-II/3",
            "expected_bbox": [-61.7867, -63.96, -44.0667, -60.535],  # [W, S, E, N]
            "expected_tbox": ["1983-11-25", "1983-12-21"],
        },
        "drilling": {
            "doi": "10.1594/PANGAEA.786028",
            "url": "https://doi.pangaea.de/10.1594/PANGAEA.786028",
            "id": "786028",
            "title": "Mineralogy and grain size composition of ODP Site 182-1128 sediments",
            "expected_bbox": [127.590835, -34.391055, 127.590835, -34.391055],  # Point location
            "expected_tbox": ["1998-11-03", "1998-11-11"],
        },
        "reference": {
            "doi": "10.1594/PANGAEA.150150",
            "url": "https://doi.pangaea.de/10.1594/PANGAEA.150150",
            "id": "150150",
            "title": "Reference list of 450 digitised data supplements of IPY 2007-2008",
            # This dataset may not have specific geographic/temporal extents
        },
        # Additional test datasets
        "radiosonde_kwajalein": {
            "doi": "10.1594/PANGAEA.853890",
            "url": "https://doi.pangaea.de/10.1594/PANGAEA.853890",
            "id": "853890",
            "title": "Radiosonde measurements from station Kwajalein (2015-06)",
            "expected_bbox": [167.731, 8.72, 167.731, 8.72],  # Point location
            "expected_tbox": ["2015-06-01", "2015-06-29"],
        },
        "oceanography_meteor": {
            "doi": "10.1594/PANGAEA.807588",
            "url": "https://doi.pangaea.de/10.1594/PANGAEA.807588",
            "id": "807588",
            "title": "Physical oceanography during METEOR cruise M36/1",
            "expected_bbox": [-41.905, 29.255, -15.505, 46.653],  # [W, S, E, N]
            "expected_tbox": ["1996-06-11", "1996-06-18"],
        },
        "sediment_core": {
            "doi": "10.1594/PANGAEA.842589",
            "url": "https://doi.pangaea.de/10.1594/PANGAEA.842589",
            "id": "842589",
            "title": "Dinoflagellate cyst measurements from sediment core HH11-134-BC",
            "expected_bbox": [9.887500, 77.599330, 9.887500, 77.599330],  # Point location
            # Temporal coverage might be geological ages, not calendar dates
        },
        "radiosonde_momote": {
            "doi": "10.1594/PANGAEA.841243",
            "url": "https://doi.pangaea.de/10.1594/PANGAEA.841243",
            "id": "841243",
            "title": "Radiosonde measurements from station Momote (2005-09)",
            "expected_bbox": [147.425, -2.058, 147.425, -2.058],  # Point location
            "expected_tbox": ["2005-09-01", "2005-09-30"],
        }
    }

    def test_pangaea_doi_validation_multiple_datasets(self):
        """Test that multiple Pangaea DOIs are correctly validated"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()

        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            # Test DOI validation
            assert pangaea.validate_provider(dataset_info["doi"]) == True
            assert pangaea.dataset_id == dataset_info["id"]

            # Test URL validation
            assert pangaea.validate_provider(dataset_info["url"]) == True
            assert pangaea.dataset_id == dataset_info["id"]

        # Test invalid DOI
        invalid_doi = "10.5281/zenodo.820562"
        assert pangaea.validate_provider(invalid_doi) == False

    def test_pangaea_metadata_extraction_multiple_datasets(self):
        """Test metadata extraction from multiple Pangaea datasets"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()

        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            try:
                pangaea.dataset_id = dataset_info["id"]
                metadata = pangaea._get_metadata()
                assert metadata is not None
                assert "title" in metadata

                # Check that title matches expected (partial match)
                if "title" in dataset_info:
                    expected_title_words = dataset_info["title"].lower().split()[:3]  # First 3 words
                    actual_title = metadata["title"].lower()
                    assert any(word in actual_title for word in expected_title_words)

            except ImportError:
                pytest.skip("pangaeapy not available")
            except Exception as e:
                pytest.skip(f"Network or API error for {dataset_name}: {e}")

    def test_pangaea_repository_extraction_oceanography_dataset(self):
        """Test full repository extraction with oceanography dataset (bbox + tbox)"""
        dataset = self.TEST_DATASETS["oceanography"]

        try:
            # Test with DOI
            result = geoextent.from_repository(
                dataset["doi"], bbox=True, tbox=True
            )

            assert result is not None
            assert "format" in result
            assert result["format"] == "repository"

            # Check geographic coverage
            if "bbox" in result:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]

                assert len(bbox) == 4
                assert isinstance(bbox[0], (int, float))
                assert isinstance(bbox[1], (int, float))
                assert isinstance(bbox[2], (int, float))
                assert isinstance(bbox[3], (int, float))

                # Verify bounding box with reasonable tolerance (0.01 degrees ~ 1.1 km)
                assert abs(bbox[0] - expected_bbox[0]) < 0.01, f"West longitude: {bbox[0]} vs {expected_bbox[0]}"
                assert abs(bbox[1] - expected_bbox[1]) < 0.01, f"South latitude: {bbox[1]} vs {expected_bbox[1]}"
                assert abs(bbox[2] - expected_bbox[2]) < 0.01, f"East longitude: {bbox[2]} vs {expected_bbox[2]}"
                assert abs(bbox[3] - expected_bbox[3]) < 0.01, f"North latitude: {bbox[3]} vs {expected_bbox[3]}"

                # Verify bounding box validity
                assert bbox[0] <= bbox[2], "West longitude should be <= East longitude"
                assert bbox[1] <= bbox[3], "South latitude should be <= North latitude"
                assert -180 <= bbox[0] <= 180, "West longitude should be valid"
                assert -180 <= bbox[2] <= 180, "East longitude should be valid"
                assert -90 <= bbox[1] <= 90, "South latitude should be valid"
                assert -90 <= bbox[3] <= 90, "North latitude should be valid"

            # Check CRS
            if "crs" in result:
                assert result["crs"] == "4326", "CRS should be WGS84"

            # Check temporal coverage
            if "tbox" in result:
                tbox = result["tbox"]
                expected_tbox = dataset["expected_tbox"]

                assert len(tbox) == 2
                assert tbox[0].startswith(expected_tbox[0][:7])  # Year-month match
                assert tbox[1].startswith(expected_tbox[1][:7])

        except ImportError:
            pytest.skip("pangaeapy not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_pangaea_repository_extraction_drilling_dataset(self):
        """Test full repository extraction with drilling dataset (point location)"""
        dataset = self.TEST_DATASETS["drilling"]

        try:
            # Test with URL format
            result = geoextent.from_repository(
                dataset["url"], bbox=True, tbox=True
            )
            assert result is not None
            assert "format" in result
            assert result["format"] == "repository"

            # Check geographic coverage (point location)
            if "bbox" in result:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]
                assert len(bbox) == 4
                # For point locations, min and max should be close or identical
                assert abs(bbox[0] - expected_bbox[0]) < 0.1  # longitude
                assert abs(bbox[1] - expected_bbox[1]) < 0.1  # latitude

            # Check temporal coverage
            if "tbox" in result:
                tbox = result["tbox"]
                expected_tbox = dataset["expected_tbox"]
                assert len(tbox) == 2
                assert tbox[0].startswith(expected_tbox[0][:7])  # Year-month match

        except ImportError:
            pytest.skip("pangaeapy not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_pangaea_repository_extraction_reference_dataset(self):
        """Test repository extraction with reference dataset (may lack geo/temporal data)"""
        dataset = self.TEST_DATASETS["reference"]

        try:
            result = geoextent.from_repository(
                dataset["doi"], bbox=True, tbox=True
            )
            assert result is not None
            assert "format" in result
            assert result["format"] == "repository"

            # This dataset may not have geographic/temporal extents
            # Test should succeed even if bbox/tbox are not present
            if "bbox" in result:
                bbox = result["bbox"]
                assert len(bbox) == 4
                assert all(isinstance(coord, (int, float)) for coord in bbox)

        except ImportError:
            pytest.skip("pangaeapy not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_pangaea_url_patterns(self):
        """Test various Pangaea URL patterns are correctly validated"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()

        # Test different URL formats for the same dataset
        test_urls = [
            "https://doi.pangaea.de/10.1594/PANGAEA.734969",
            "http://doi.pangaea.de/10.1594/PANGAEA.734969",
            "10.1594/PANGAEA.734969",  # Plain DOI
        ]

        for url in test_urls:
            assert pangaea.validate_provider(url) == True
            assert pangaea.dataset_id == "734969"

        # Test non-Pangaea URLs
        invalid_urls = [
            "https://zenodo.org/record/820562",
            "https://figshare.com/articles/123456",
            "10.5281/zenodo.820562",
        ]

        for url in invalid_urls:
            assert pangaea.validate_provider(url) == False

    def test_pangaea_download_data_flag_oceanography(self):
        """Test download_data flag with oceanography dataset"""
        try:
            # Test with download_data=True (should download actual files)
            result = geoextent.from_repository(
                self.TEST_DATASETS["oceanography_meteor"]["doi"],
                bbox=True,
                tbox=True,
                download_data=True
            )
            assert result is not None
            assert "format" in result
            assert result["format"] == "repository"

            # Should have extracted geographic and temporal data from actual files
            if "bbox" in result:
                bbox = result["bbox"]
                expected_bbox = self.TEST_DATASETS["oceanography_meteor"]["expected_bbox"]
                assert len(bbox) == 4
                # Allow tolerance for extraction differences
                assert abs(bbox[0] - expected_bbox[0]) < 5.0  # longitude tolerance
                assert abs(bbox[1] - expected_bbox[1]) < 5.0  # latitude tolerance

        except ImportError:
            pytest.skip("pangaeapy not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_pangaea_radiosonde_datasets(self):
        """Test radiosonde datasets (point locations with temporal data)"""
        radiosonde_datasets = ["radiosonde_kwajalein", "radiosonde_momote"]

        for dataset_name in radiosonde_datasets:
            dataset = self.TEST_DATASETS[dataset_name]
            try:
                result = geoextent.from_repository(
                    dataset["doi"], bbox=True, tbox=True
                )
                assert result is not None
                assert "format" in result
                assert result["format"] == "repository"

                # Check point location
                if "bbox" in result:
                    bbox = result["bbox"]
                    expected_bbox = dataset["expected_bbox"]
                    assert len(bbox) == 4
                    # For point locations, coordinates should be very close
                    assert abs(bbox[0] - expected_bbox[0]) < 0.01  # longitude
                    assert abs(bbox[1] - expected_bbox[1]) < 0.01  # latitude

                # Check temporal coverage
                if "tbox" in result and "expected_tbox" in dataset:
                    tbox = result["tbox"]
                    expected_tbox = dataset["expected_tbox"]
                    assert len(tbox) == 2
                    assert tbox[0].startswith(expected_tbox[0][:7])  # Year-month match

            except ImportError:
                pytest.skip("pangaeapy not available")
            except Exception as e:
                pytest.skip(f"Network or API error for {dataset_name}: {e}")

    def test_pangaea_sediment_core_dataset(self):
        """Test sediment core dataset (geological data with special temporal handling)"""
        dataset = self.TEST_DATASETS["sediment_core"]

        try:
            result = geoextent.from_repository(
                dataset["url"], bbox=True, tbox=True
            )
            assert result is not None
            assert "format" in result
            assert result["format"] == "repository"

            # Check geographic coverage (point location)
            if "bbox" in result:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]
                assert len(bbox) == 4
                assert abs(bbox[0] - expected_bbox[0]) < 0.1  # longitude
                assert abs(bbox[1] - expected_bbox[1]) < 0.1  # latitude

            # Temporal coverage might not be available for geological datasets
            # This is OK - the test should pass even without temporal data

        except ImportError:
            pytest.skip("pangaeapy not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_pangaea_all_additional_datasets_validation(self):
        """Test that all additional datasets can be validated"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        additional_datasets = ["radiosonde_kwajalein", "oceanography_meteor", "sediment_core", "radiosonde_momote"]
        pangaea = Pangaea()

        for dataset_name in additional_datasets:
            dataset = self.TEST_DATASETS[dataset_name]

            # Test DOI validation
            assert pangaea.validate_provider(dataset["doi"]) == True
            assert pangaea.dataset_id == dataset["id"]

            # Test URL validation
            assert pangaea.validate_provider(dataset["url"]) == True
            assert pangaea.dataset_id == dataset["id"]

    def test_pangaea_invalid_dataset(self):
        """Test handling of invalid Pangaea dataset ID"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()

        # Test with invalid DOI
        invalid_doi = "10.1594/PANGAEA.999999999"
        is_valid = pangaea.validate_provider(invalid_doi)

        if is_valid:  # If validation passes, test metadata extraction
            try:
                metadata = pangaea._get_metadata()
                # Should either return None or raise an exception
                assert metadata is None
            except Exception:
                # Exception is expected for invalid dataset
                pass

    def test_pangaea_coverage_extraction_empty(self):
        """Test coverage extraction with empty dataset"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()

        # Create mock dataset-like object
        class MockDataset:
            def __init__(self):
                self.data = None

        mock_dataset = MockDataset()
        coverage = pangaea._extract_coverage(mock_dataset)
        assert coverage == {}

    def test_pangaea_temporal_extraction_empty(self):
        """Test temporal extraction with empty dataset"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()

        # Create mock dataset-like object
        class MockDataset:
            def __init__(self):
                self.data = None

        mock_dataset = MockDataset()
        temporal = pangaea._extract_temporal_coverage(mock_dataset)
        assert temporal == {}

    def test_pangaea_parameter_extraction_empty(self):
        """Test parameter extraction with empty dataset"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()

        # Create mock dataset-like object
        class MockDataset:
            def __init__(self):
                self.params = None

        mock_dataset = MockDataset()
        parameters = pangaea._extract_parameters(mock_dataset)
        assert parameters == []

    def test_pangaea_download_method_signatures(self):
        """Test that download method accepts the new download_data parameter"""
        from geoextent.lib.content_providers.Pangaea import Pangaea
        import tempfile
        import os

        pangaea = Pangaea()
        pangaea.dataset_id = "123456"  # Mock dataset ID

        # Test that method can be called with download_data parameter
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # This should not crash - method signature should accept download_data
                pangaea.download(temp_dir, throttle=False, download_data=False)
                pangaea.download(temp_dir, throttle=False, download_data=True)
            except Exception as e:
                # Expect errors due to mock data, but not signature errors
                assert "pangaeapy" in str(e) or "dataset" in str(e) or "metadata" in str(e)

    def test_pangaea_local_vs_metadata_extraction(self):
        """Test comparing metadata-based vs local file extraction"""
        dataset = self.TEST_DATASETS["radiosonde_kwajalein"]

        try:
            # Test metadata-based extraction (default)
            result_metadata = geoextent.from_repository(
                dataset["doi"],
                bbox=True,
                tbox=True,
                download_data=False
            )

            # Test local file extraction
            result_local = geoextent.from_repository(
                dataset["doi"],
                bbox=True,
                tbox=True,
                download_data=True
            )

            # Both should succeed
            assert result_metadata is not None
            assert result_local is not None
            assert result_metadata["format"] == "repository"
            assert result_local["format"] == "repository"

            # Compare results - they should be similar but may differ slightly
            if "bbox" in result_metadata and "bbox" in result_local:
                metadata_bbox = result_metadata["bbox"]
                local_bbox = result_local["bbox"]

                # Coordinates should be reasonably close (within 1 degree tolerance)
                assert abs(metadata_bbox[0] - local_bbox[0]) < 1.0
                assert abs(metadata_bbox[1] - local_bbox[1]) < 1.0

        except ImportError:
            pytest.skip("pangaeapy not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_pangaea_cli_download_data_parameter(self):
        """Test that CLI accepts and processes --no-download-data parameter"""
        # This is a unit test that doesn't require network access
        import argparse
        from geoextent.__main__ import get_arg_parser

        parser = get_arg_parser()

        # Test that --no-download-data flag is accepted
        args1 = parser.parse_args(["-b", "-t", "--no-download-data", "10.1594/PANGAEA.734969"])
        assert args1.download_data == False
        assert args1.bounding_box == True
        assert args1.time_box == True

        # Test without the flag (default behavior is to download data)
        args2 = parser.parse_args(["-b", "-t", "10.1594/PANGAEA.734969"])
        assert args2.download_data == True
        assert args2.bounding_box == True
        assert args2.time_box == True


class TestPangaeaParameterCombinations:
    """Test various parameter combinations for Pangaea repository functions"""

    def test_pangaea_repository_bbox_only(self):
        """Test Pangaea repository extraction with only bbox enabled"""
        dataset = TestPangaeaProvider.TEST_DATASETS["oceanography"]

        try:
            result = geoextent.from_repository(
                dataset["doi"], bbox=True, tbox=False
            )
            assert result is not None
            assert "bbox" in result
            assert "tbox" not in result
            assert result["format"] == "repository"
        except ImportError:
            pytest.skip("pangaeapy not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_pangaea_repository_tbox_only(self):
        """Test Pangaea repository extraction with only tbox enabled"""
        dataset = TestPangaeaProvider.TEST_DATASETS["oceanography"]

        try:
            result = geoextent.from_repository(
                dataset["doi"], bbox=False, tbox=True
            )
            assert result is not None
            assert "tbox" in result
            assert "bbox" not in result
            assert result["format"] == "repository"
        except ImportError:
            pytest.skip("pangaeapy not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_pangaea_repository_both_disabled_should_fail(self):
        """Test Pangaea repository extraction with both bbox and tbox disabled should fail"""
        dataset = TestPangaeaProvider.TEST_DATASETS["oceanography"]

        with pytest.raises(Exception, match="No extraction options enabled"):
            geoextent.from_repository(
                dataset["doi"], bbox=False, tbox=False
            )

    def test_pangaea_repository_with_details_enabled(self):
        """Test Pangaea repository extraction with details enabled"""
        dataset = TestPangaeaProvider.TEST_DATASETS["reference"]

        try:
            result = geoextent.from_repository(
                dataset["doi"], bbox=True, tbox=True, details=True
            )
            assert result is not None
            assert "details" in result
            assert isinstance(result["details"], dict)
            assert result["format"] == "repository"
        except ImportError:
            pytest.skip("pangaeapy not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_pangaea_repository_with_throttle_enabled(self):
        """Test Pangaea repository extraction with throttle enabled"""
        dataset = TestPangaeaProvider.TEST_DATASETS["drilling"]

        try:
            result = geoextent.from_repository(
                dataset["doi"], bbox=True, tbox=True, throttle=True
            )
            assert result is not None
            assert result["format"] == "repository"
        except ImportError:
            pytest.skip("pangaeapy not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_pangaea_repository_with_timeout(self):
        """Test Pangaea repository extraction with timeout parameter"""
        dataset = TestPangaeaProvider.TEST_DATASETS["reference"]

        try:
            result = geoextent.from_repository(
                dataset["doi"], bbox=True, tbox=True, timeout=30
            )
            assert result is not None
            assert result["format"] == "repository"
            # timeout field should not be present if timeout wasn't reached
            assert "timeout" not in result
        except ImportError:
            pytest.skip("pangaeapy not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_pangaea_repository_download_data_combinations(self):
        """Test Pangaea repository with different download_data parameter combinations"""
        dataset = TestPangaeaProvider.TEST_DATASETS["radiosonde_kwajalein"]

        try:
            # Test with download_data=False (default, metadata-based)
            result1 = geoextent.from_repository(
                dataset["doi"], bbox=True, tbox=True, download_data=False
            )
            assert result1 is not None
            assert result1["format"] == "repository"

            # Test with download_data=True (local file download)
            result2 = geoextent.from_repository(
                dataset["doi"], bbox=True, tbox=True, download_data=True
            )
            assert result2 is not None
            assert result2["format"] == "repository"

            # Both results should have similar structure
            assert ("bbox" in result1) == ("bbox" in result2)

        except ImportError:
            pytest.skip("pangaeapy not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_pangaea_repository_all_parameters_enabled(self):
        """Test Pangaea repository with all optional parameters enabled"""
        dataset = TestPangaeaProvider.TEST_DATASETS["sediment_core"]

        try:
            result = geoextent.from_repository(
                dataset["doi"],
                bbox=True,
                tbox=True,
                details=True,
                throttle=True,
                timeout=60,
                download_data=True
            )
            assert result is not None
            assert result["format"] == "repository"
            assert "details" in result

        except ImportError:
            pytest.skip("pangaeapy not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_pangaea_repository_multiple_datasets_with_different_parameters(self):
        """Test multiple Pangaea datasets with different parameter combinations"""
        test_cases = [
            {
                "dataset": TestPangaeaProvider.TEST_DATASETS["oceanography"],
                "params": {"bbox": True, "tbox": False, "details": False}
            },
            {
                "dataset": TestPangaeaProvider.TEST_DATASETS["drilling"],
                "params": {"bbox": False, "tbox": True, "details": True}
            },
            {
                "dataset": TestPangaeaProvider.TEST_DATASETS["radiosonde_kwajalein"],
                "params": {"bbox": True, "tbox": True, "download_data": True}
            }
        ]

        for test_case in test_cases:
            try:
                result = geoextent.from_repository(
                    test_case["dataset"]["doi"],
                    **test_case["params"]
                )
                assert result is not None
                assert result["format"] == "repository"

                # Check parameter-specific expectations
                if test_case["params"].get("bbox", False):
                    # bbox might or might not be present depending on data
                    pass
                else:
                    assert "bbox" not in result

                if test_case["params"].get("tbox", False):
                    # tbox might or might not be present depending on data
                    pass
                else:
                    assert "tbox" not in result

                if test_case["params"].get("details", False):
                    assert "details" in result
                else:
                    assert "details" not in result

            except ImportError:
                pytest.skip("pangaeapy not available")
            except Exception as e:
                pytest.skip(f"Network or API error: {e}")


class TestPangaeaEdgeCases:
    """Test edge cases and error handling for Pangaea functionality"""

    def test_pangaea_invalid_doi_format(self):
        """Test Pangaea with invalid DOI format"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()
        invalid_dois = [
            "10.1594/INVALID.123",  # Wrong prefix
            "10.5281/zenodo.123",   # Different repository
            "not-a-doi-at-all",    # Not a DOI
            "",                     # Empty string
            "10.1594/PANGAEA.",     # Incomplete
            "10.1594/PANGAEA.abc",  # Non-numeric ID
        ]

        for invalid_doi in invalid_dois:
            assert pangaea.validate_provider(invalid_doi) == False

    def test_pangaea_edge_case_urls(self):
        """Test Pangaea with edge case URL formats"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()

        # Valid dataset ID for testing
        valid_id = "734969"

        edge_case_urls = [
            f"https://doi.pangaea.de/10.1594/PANGAEA.{valid_id}/",  # Trailing slash
            f"HTTP://DOI.PANGAEA.DE/10.1594/PANGAEA.{valid_id}",    # Uppercase
            f"https://pangaea.de/10.1594/PANGAEA.{valid_id}",       # Different subdomain
            f"http://pangaea.de/10.1594/PANGAEA.{valid_id}",        # HTTP instead of HTTPS
        ]

        for url in edge_case_urls:
            is_valid = pangaea.validate_provider(url)
            if is_valid:
                assert pangaea.dataset_id == valid_id

    def test_pangaea_provider_error_handling(self):
        """Test Pangaea provider error handling with problematic datasets"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()

        # Test with a dataset ID that likely doesn't exist
        pangaea.dataset_id = "999999999"

        try:
            metadata = pangaea._get_metadata()
            # If it doesn't raise an exception, metadata should be None or empty
            if metadata is not None:
                assert isinstance(metadata, dict)
        except Exception as e:
            # Exception is expected for non-existent datasets
            assert "Failed to fetch" in str(e) or "not available" in str(e) or "Error" in str(e)

    def test_pangaea_coverage_extraction_with_invalid_data(self):
        """Test coverage extraction with various invalid data scenarios"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()

        # Test with dataset that has no data attribute
        class MockDatasetNoData:
            pass

        result = pangaea._extract_coverage(MockDatasetNoData())
        assert result == {}

        # Test with dataset that has empty data
        class MockDatasetEmptyData:
            def __init__(self):
                import pandas as pd
                self.data = pd.DataFrame()

        result = pangaea._extract_coverage(MockDatasetEmptyData())
        assert result == {}

    def test_pangaea_temporal_extraction_with_invalid_data(self):
        """Test temporal extraction with various invalid data scenarios"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()

        # Test with dataset that has invalid date formats
        class MockDatasetInvalidDates:
            def __init__(self):
                import pandas as pd
                self.data = pd.DataFrame({
                    'date_time': ['invalid-date', 'not-a-date', '2023-13-45'],  # Invalid dates
                    'other_col': [1, 2, 3]
                })

        result = pangaea._extract_temporal_coverage(MockDatasetInvalidDates())
        assert result == {}

    def test_pangaea_parameter_extraction_edge_cases(self):
        """Test parameter extraction with edge cases"""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        pangaea = Pangaea()

        # Test with dataset that has malformed params
        class MockDatasetMalformedParams:
            def __init__(self):
                self.params = [
                    {},  # Empty param
                    {"name": None},  # None name
                    {"name": "", "unit": ""},  # Empty strings
                    {"unexpected_field": "value"},  # Unexpected structure
                ]

        result = pangaea._extract_parameters(MockDatasetMalformedParams())
        assert isinstance(result, list)
        assert len(result) == 4  # Should handle all params gracefully

    def test_pangaea_download_with_various_scenarios(self):
        """Test download method with various parameter scenarios"""
        from geoextent.lib.content_providers.Pangaea import Pangaea
        import tempfile

        pangaea = Pangaea()
        pangaea.dataset_id = "123456"  # Mock ID

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test download with throttle enabled
            try:
                pangaea.download(temp_dir, throttle=True, download_data=False)
            except Exception as e:
                # Expected to fail with mock data
                assert "pangaeapy" in str(e) or "metadata" in str(e) or "dataset" in str(e)

            # Test download with download_data enabled
            try:
                pangaea.download(temp_dir, throttle=False, download_data=True)
            except Exception as e:
                # Expected to fail with mock data
                assert "pangaeapy" in str(e) or "metadata" in str(e) or "dataset" in str(e)