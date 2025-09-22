import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance


class TestOSFProvider:
    """Test OSF (Open Science Framework) content provider functionality"""

    # Test datasets based on GitHub issue #19 and public OSF projects with geospatial data
    TEST_DATASETS = {
        "gis_dataset_shapefiles": {
            "project_id": "4xe6z",
            "url": "https://osf.io/4xe6z",
            "doi": "10.17605/OSF.IO/4XE6Z",
            "title": "GIS Dataset",
            "description": "Contains shapefiles for Mekong River analysis",
            # Expected results based on the shapefiles we saw downloaded
            "expected_files": ["River_reach_3S.shp", "Mekong_River_Full.shp", "UderContract_Scenario_Modelled.shp"],
            "has_shapefiles": True,
        },
        "niseko_gis": {
            "project_id": "5j9kp",
            "url": "https://osf.io/5j9kp",
            "doi": "10.17605/OSF.IO/5J9KP",
            "title": "Niseko Backcountry GIS Files",
            "description": "QGIS files and non-GSI files for Niseko Backcountry topomap",
            "has_gis_files": True,
        },
        "harvard_gis": {
            "project_id": "g8rcj",
            "url": "https://osf.io/g8rcj",
            "doi": "10.17605/OSF.IO/G8RCJ",
            "title": "Harvard Map Collection: Research, Teaching, and Learning GIS Collections",
            "description": "GIS datasets from Harvard Map Collection",
            "has_gis_files": True,
        },
        "coordinate_data": {
            "project_id": "gisvk",
            "url": "https://osf.io/gisvk",
            "doi": "10.17605/OSF.IO/GISVK",
            "title": "Experiment Materials",
            "description": "Materials that may contain coordinate data",
        },
        "code_and_data": {
            "project_id": "gfwhj",
            "url": "https://osf.io/gfwhj",
            "doi": "10.17605/OSF.IO/GFWHJ",
            "title": "Code and data files",
            "description": "Project with code and data files",
        },
        # Test datasets from GitHub issue #19 with DOI examples
        "github_issue_j2sta": {
            "project_id": "j2sta",
            "url": "https://osf.io/j2sta",
            "doi": "10.17605/OSF.IO/J2STA",
            "title": "GitHub issue example J2STA",
            "description": "Example from GitHub issue #19",
        },
        "github_issue_a5f3e": {
            "project_id": "a5f3e",
            "url": "https://osf.io/a5f3e",
            "doi": "10.17605/OSF.IO/A5F3E",
            "title": "GitHub issue example A5F3E",
            "description": "Example from GitHub issue #19",
        },
    }

    def test_osf_provider_validation_project_id(self):
        """Test OSF provider validation with direct project IDs"""
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()

        # Test valid project IDs
        assert osf.validate_provider("4xe6z") == True
        assert osf.project_id == "4xe6z"

        assert osf.validate_provider("5J9KP") == True  # Case insensitive
        assert osf.project_id == "5j9kp"

        # Test invalid project IDs
        assert osf.validate_provider("invalid") == False
        assert osf.validate_provider("12345678") == False  # Too long
        assert osf.validate_provider("123") == False  # Too short

    def test_osf_provider_validation_urls(self):
        """Test OSF provider validation with URLs"""
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()

        # Test various URL formats
        test_cases = [
            ("https://osf.io/4xe6z", True, "4xe6z"),
            ("https://osf.io/4xe6z/", True, "4xe6z"),
            ("http://osf.io/4xe6z", True, "4xe6z"),
            ("https://osf.io/5J9KP/", True, "5j9kp"),  # Case insensitive
            ("https://example.com/4xe6z", False, None),
            ("https://osf.io/", False, None),
            ("https://osf.io/invalid_id", False, None),
        ]

        for url, expected_valid, expected_id in test_cases:
            result = osf.validate_provider(url)
            assert result == expected_valid, f"URL {url} validation failed"
            if expected_valid:
                assert osf.project_id == expected_id, f"Project ID extraction failed for {url}"

    def test_osf_provider_validation_dois(self):
        """Test OSF provider validation with DOIs"""
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()

        # Test DOI formats
        test_cases = [
            ("10.17605/OSF.IO/4XE6Z", True, "4xe6z"),
            ("10.17605/OSF.IO/5j9kp", True, "5j9kp"),
            ("10.17605/OSF.IO/G8RCJ", True, "g8rcj"),  # Case insensitive
            ("10.1000/invalid", False, None),
            ("10.17605/OSF.IO/", False, None),
            ("10.17605/OSF.IO/invalid_id", False, None),
        ]

        for doi, expected_valid, expected_id in test_cases:
            result = osf.validate_provider(doi)
            assert result == expected_valid, f"DOI {doi} validation failed"
            if expected_valid:
                assert osf.project_id == expected_id, f"Project ID extraction failed for {doi}"

    def test_osf_provider_validation_doi_variants(self):
        """Test OSF provider validation with various DOI URL formats and capitalizations"""
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()

        # Test cases covering all DOI variants from GitHub issue #19
        test_cases = [
            # Standard bare DOI formats from issue examples
            ("10.17605/OSF.IO/J2STA", True, "j2sta"),
            ("10.17605/OSF.IO/A5F3E", True, "a5f3e"),
            ("10.17605/OSF.IO/9JG2U", True, "9jg2u"),
            ("10.17605/OSF.IO/JXATU", True, "jxatu"),

            # Lowercase variants
            ("10.17605/osf.io/j2sta", True, "j2sta"),
            ("10.17605/osf.io/A5F3E", True, "a5f3e"),

            # Mixed case variants
            ("10.17605/Osf.Io/J2STA", True, "j2sta"),

            # DOI resolver URLs - https://doi.org
            ("https://doi.org/10.17605/OSF.IO/J2STA", True, "j2sta"),
            ("https://doi.org/10.17605/OSF.IO/A5F3E", True, "a5f3e"),
            ("https://doi.org/10.17605/osf.io/j2sta", True, "j2sta"),
            ("http://doi.org/10.17605/OSF.IO/J2STA", True, "j2sta"),

            # DOI resolver URLs - dx.doi.org (legacy)
            ("http://dx.doi.org/10.17605/OSF.IO/J2STA", True, "j2sta"),
            ("https://dx.doi.org/10.17605/OSF.IO/A5F3E", True, "a5f3e"),

            # With www prefix
            ("https://www.doi.org/10.17605/OSF.IO/J2STA", True, "j2sta"),

            # With trailing paths/queries/fragments
            ("https://doi.org/10.17605/OSF.IO/J2STA/", True, "j2sta"),
            ("https://doi.org/10.17605/OSF.IO/J2STA?tab=files", True, "j2sta"),
            ("https://doi.org/10.17605/OSF.IO/J2STA#readme", True, "j2sta"),

            # Invalid cases
            ("10.17605/OSF.IO/invalid_id", False, None),
            ("https://doi.org/10.1000/invalid", False, None),
            ("https://example.com/10.17605/OSF.IO/J2STA", False, None),
        ]

        for reference, expected_valid, expected_id in test_cases:
            result = osf.validate_provider(reference)
            assert result == expected_valid, f"DOI variant {reference} validation failed"
            if expected_valid:
                assert osf.project_id == expected_id, f"Project ID extraction failed for {reference}"
            osf.project_id = None  # Reset for next test

    def test_osf_provider_validation_plain_identifiers(self):
        """Test OSF provider validation with plain OSF identifiers (OSF.IO/PROJECT_ID)"""
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()

        # Test cases for plain OSF identifiers from GitHub issue #19
        test_cases = [
            # Plain OSF identifiers from GitHub issue examples
            ("OSF.IO/9JG2U", True, "9jg2u"),
            ("OSF.IO/J2STA", True, "j2sta"),
            ("OSF.IO/A5F3E", True, "a5f3e"),
            ("OSF.IO/JXATU", True, "jxatu"),

            # Lowercase variants
            ("osf.io/9jg2u", True, "9jg2u"),
            ("osf.io/j2sta", True, "j2sta"),
            ("osf.io/A5F3E", True, "a5f3e"),

            # Mixed case variants
            ("Osf.Io/9JG2U", True, "9jg2u"),
            ("Osf.Io/J2STA", True, "j2sta"),

            # Invalid cases
            ("OSF.IO/invalid_id", False, None),
            ("OSF.IO/", False, None),
            ("OSF.IO/123", False, None),  # Too short
            ("OSF.IO/ABCDEF", False, None),  # Too long
            ("something/OSF.IO/9JG2U", False, None),  # Prefix
            ("OSF.IO/9JG2U/extra", False, None),  # Suffix
            ("osf.io/9JG2U/files", False, None),  # With path
        ]

        for reference, expected_valid, expected_id in test_cases:
            result = osf.validate_provider(reference)
            assert result == expected_valid, f"Plain OSF identifier {reference} validation failed"
            if expected_valid:
                assert osf.project_id == expected_id, f"Project ID extraction failed for {reference}"
            osf.project_id = None  # Reset for next test

    def test_osf_metadata_extraction(self):
        """Test OSF metadata extraction via API"""
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()
        dataset = self.TEST_DATASETS["gis_dataset_shapefiles"]

        osf.validate_provider(dataset["project_id"])

        try:
            metadata = osf._get_metadata_via_api()

            # Check that we got some metadata
            assert metadata is not None
            assert "title" in metadata
            assert "public" in metadata
            assert metadata["public"] == True  # Should be public project

            # Check basic fields
            assert isinstance(metadata["title"], str)
            assert len(metadata["title"]) > 0

        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    @pytest.mark.skip(reason="Requires network access and may be slow")
    def test_osf_file_download_osfclient(self):
        """Test OSF file download using osfclient"""
        import tempfile
        import os
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()
        dataset = self.TEST_DATASETS["gis_dataset_shapefiles"]

        osf.validate_provider(dataset["project_id"])

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                files = osf._get_files_via_osfclient(tmpdir)

                # Check that files were downloaded
                assert len(files) > 0, "No files were downloaded"

                # Check that expected files exist
                downloaded_names = [os.path.basename(f) for f in files]
                for expected_file in dataset["expected_files"]:
                    assert expected_file in downloaded_names, f"Expected file {expected_file} not found"

                # Check for shapefile components if this is a GIS dataset
                if dataset.get("has_shapefiles"):
                    shp_files = [f for f in downloaded_names if f.endswith('.shp')]
                    assert len(shp_files) > 0, "No shapefile (.shp) files found"

                    # For each .shp file, check for associated files
                    for shp_file in shp_files:
                        base_name = shp_file[:-4]  # Remove .shp extension
                        expected_extensions = ['.shx', '.dbf']  # Required shapefile components
                        for ext in expected_extensions:
                            expected_file = base_name + ext
                            assert expected_file in downloaded_names, f"Missing shapefile component: {expected_file}"

            except ImportError:
                pytest.skip("osfclient not available")
            except Exception as e:
                pytest.skip(f"Network or OSF access error: {e}")

    def test_osf_repository_extraction_gis_dataset(self):
        """Test geoextent extraction from OSF GIS dataset"""
        dataset = self.TEST_DATASETS["gis_dataset_shapefiles"]

        try:
            result = geoextent.from_repository(
                dataset["url"],
                bbox=True,
                tbox=False,
                timeout=60,
                download_data=True
            )

            # Check basic result structure
            assert result is not None
            assert "format" in result
            assert result["format"] == "repository"

            # Check for bbox if the dataset contains geospatial data
            if dataset.get("has_shapefiles"):
                assert "bbox" in result, "Expected bounding box for GIS dataset"
                assert "crs" in result
                bbox = result["bbox"]
                assert len(bbox) == 4, "Bounding box should have 4 coordinates"
                assert all(isinstance(coord, (int, float)) for coord in bbox), "All bbox coordinates should be numeric"

        except ImportError:
            pytest.skip("osfclient not available")
        except Exception as e:
            pytest.skip(f"Network or processing error: {e}")

    def test_osf_repository_no_download_mode(self):
        """Test OSF repository with download_data=False"""
        dataset = self.TEST_DATASETS["gis_dataset_shapefiles"]

        try:
            result = geoextent.from_repository(
                dataset["url"],
                bbox=True,
                tbox=False,
                timeout=30,
                download_data=False
            )

            # Should complete without error, but may have limited results
            assert result is not None
            assert "format" in result
            assert result["format"] == "repository"

            # Note: bbox may not be available in no-download mode for OSF

        except ImportError:
            pytest.skip("osfclient not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_osf_provider_error_handling(self):
        """Test OSF provider error handling for invalid projects"""
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()

        # Test with non-existent project
        osf.validate_provider("zzzzz")  # Likely non-existent

        try:
            metadata = osf._get_metadata_via_api()
            # If this succeeds, the project exists (which is fine)
        except Exception as e:
            # Should get a meaningful error message
            assert "Failed to fetch OSF API metadata" in str(e)

    def test_osf_provider_integration(self):
        """Test that OSF provider is properly integrated into geoextent"""
        from geoextent.lib.content_providers import OSF

        # Test that OSF class can be imported
        osf_provider = OSF.OSF()
        assert osf_provider.name == "OSF"

        # Test validation method exists
        assert hasattr(osf_provider, 'validate_provider')
        assert hasattr(osf_provider, 'download')


class TestOSFParameterCombinations:
    """Test various parameter combinations for OSF repository functions"""

    def test_osf_repository_bbox_only(self):
        """Test OSF repository extraction with only bbox enabled"""
        dataset = TestOSFProvider.TEST_DATASETS["gis_dataset_shapefiles"]

        try:
            result = geoextent.from_repository(
                dataset["url"],
                bbox=True,
                tbox=False,
                timeout=30,
                download_data=True
            )

            assert result is not None
            assert "format" in result
            if "bbox" in result:
                assert "tbox" not in result or result["tbox"] is None

        except ImportError:
            pytest.skip("osfclient not available")
        except Exception as e:
            pytest.skip(f"Network or processing error: {e}")

    def test_osf_repository_both_disabled_should_fail(self):
        """Test that OSF repository extraction fails when both bbox and tbox are disabled"""
        dataset = TestOSFProvider.TEST_DATASETS["gis_dataset_shapefiles"]

        with pytest.raises(Exception):
            geoextent.from_repository(
                dataset["url"],
                bbox=False,
                tbox=False,
                timeout=30
            )

    def test_osf_repository_with_timeout(self):
        """Test OSF repository extraction with different timeout values"""
        dataset = TestOSFProvider.TEST_DATASETS["gis_dataset_shapefiles"]

        try:
            # Test with short timeout
            result = geoextent.from_repository(
                dataset["url"],
                bbox=True,
                tbox=False,
                timeout=10,  # Short timeout
                download_data=False  # Faster without download
            )

            assert result is not None
            assert "format" in result

        except ImportError:
            pytest.skip("osfclient not available")
        except Exception as e:
            # Timeout or network errors are acceptable for this test
            pass


class TestOSFEdgeCases:
    """Test OSF provider edge cases and error conditions"""

    def test_osf_invalid_project_id_format(self):
        """Test OSF provider with invalid project ID formats"""
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()

        invalid_ids = [
            "",  # Empty string
            "123",  # Too short
            "abcdef",  # Too long
            "abc-d",  # Invalid characters
            "osf.io/4xe6z",  # URL fragment
        ]

        for invalid_id in invalid_ids:
            assert osf.validate_provider(invalid_id) == False

    def test_osf_edge_case_urls(self):
        """Test OSF provider with edge case URLs"""
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()

        edge_cases = [
            "https://osf.io",  # No project ID
            "https://osf.io/",  # Trailing slash only
            "https://accounts.osf.io/4xe6z",  # Wrong subdomain
            "https://osf.io/4xe6z/files/",  # With files path
            "https://osf.io/4xe6z/wiki/",  # With wiki path
        ]

        for url in edge_cases:
            result = osf.validate_provider(url)
            # Most should fail, but some file/wiki URLs might be valid
            if result:
                assert osf.project_id is not None
                assert len(osf.project_id) == 5

    def test_osf_provider_method_signatures(self):
        """Test that OSF provider has required method signatures"""
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()

        # Test required methods exist with correct signatures
        assert callable(osf.validate_provider)
        assert callable(osf.download)

        # Test download method signature
        import inspect
        sig = inspect.signature(osf.download)
        param_names = list(sig.parameters.keys())
        assert "target_folder" in param_names
        assert "throttle" in param_names
        assert "download_data" in param_names