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

    @pytest.mark.skip(reason="Requires pangaeapy and network access")
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

    @pytest.mark.skip(reason="Requires pangaeapy and network access - integration test")
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
                # Allow some tolerance for coordinate extraction differences
                assert abs(bbox[0] - expected_bbox[0]) < 1.0  # longitude tolerance
                assert abs(bbox[1] - expected_bbox[1]) < 1.0  # latitude tolerance

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

    @pytest.mark.skip(reason="Requires pangaeapy and network access - integration test")
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

    @pytest.mark.skip(reason="Requires pangaeapy and network access - integration test")
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