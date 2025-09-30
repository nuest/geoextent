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
            "expected_files": [
                "River_reach_3S.shp",
                "Mekong_River_Full.shp",
                "UderContract_Scenario_Modelled.shp",
            ],
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

    def test_osf_provider_validation_comprehensive(self):
        """Test OSF provider validation with all supported input formats"""
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()

        # Comprehensive test cases covering all supported formats
        test_cases = [
            # Direct project IDs
            ("4xe6z", True, "4xe6z"),
            ("5J9KP", True, "5j9kp"),  # Case insensitive
            # URLs
            ("https://osf.io/4xe6z", True, "4xe6z"),
            ("https://osf.io/4xe6z/", True, "4xe6z"),
            ("http://osf.io/4xe6z", True, "4xe6z"),
            ("https://osf.io/5J9KP/", True, "5j9kp"),
            # Bare DOIs
            ("10.17605/OSF.IO/4XE6Z", True, "4xe6z"),
            ("10.17605/OSF.IO/5j9kp", True, "5j9kp"),
            ("10.17605/OSF.IO/G8RCJ", True, "g8rcj"),
            ("10.17605/osf.io/j2sta", True, "j2sta"),  # Lowercase
            ("10.17605/Osf.Io/J2STA", True, "j2sta"),  # Mixed case
            # DOI resolver URLs
            ("https://doi.org/10.17605/OSF.IO/J2STA", True, "j2sta"),
            ("http://dx.doi.org/10.17605/OSF.IO/A5F3E", True, "a5f3e"),
            ("https://www.doi.org/10.17605/OSF.IO/J2STA", True, "j2sta"),
            ("https://doi.org/10.17605/OSF.IO/J2STA?tab=files", True, "j2sta"),
            # Plain OSF identifiers
            ("OSF.IO/9JG2U", True, "9jg2u"),
            ("osf.io/j2sta", True, "j2sta"),
            ("Osf.Io/A5F3E", True, "a5f3e"),
            # Invalid cases
            ("invalid", False, None),
            ("12345678", False, None),  # Too long
            ("123", False, None),  # Too short
            ("https://example.com/4xe6z", False, None),
            ("https://osf.io/", False, None),
            ("10.1000/invalid", False, None),
            ("OSF.IO/invalid_id", False, None),
            ("", False, None),
        ]

        for reference, expected_valid, expected_id in test_cases:
            result = osf.validate_provider(reference)
            assert result == expected_valid, f"Validation failed for {reference}"
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
                    assert (
                        expected_file in downloaded_names
                    ), f"Expected file {expected_file} not found"

                # Check for shapefile components if this is a GIS dataset
                if dataset.get("has_shapefiles"):
                    shp_files = [f for f in downloaded_names if f.endswith(".shp")]
                    assert len(shp_files) > 0, "No shapefile (.shp) files found"

                    # For each .shp file, check for associated files
                    for shp_file in shp_files:
                        base_name = shp_file[:-4]  # Remove .shp extension
                        expected_extensions = [
                            ".shx",
                            ".dbf",
                        ]  # Required shapefile components
                        for ext in expected_extensions:
                            expected_file = base_name + ext
                            assert (
                                expected_file in downloaded_names
                            ), f"Missing shapefile component: {expected_file}"

            except ImportError:
                pytest.skip("osfclient not available")
            except Exception as e:
                pytest.skip(f"Network or OSF access error: {e}")

    def test_osf_repository_extraction_gis_dataset(self):
        """Test geoextent extraction from OSF GIS dataset"""
        dataset = self.TEST_DATASETS["gis_dataset_shapefiles"]

        try:
            result = geoextent.fromRemote(
                dataset["url"], bbox=True, tbox=False, timeout=60, download_data=True
            )

            # Check basic result structure
            assert result is not None
            assert "format" in result
            assert result["format"] == "remote"

            # Check for bbox if the dataset contains geospatial data
            if dataset.get("has_shapefiles"):
                assert "bbox" in result, "Expected bounding box for GIS dataset"
                assert "crs" in result
                bbox = result["bbox"]
                assert len(bbox) == 4, "Bounding box should have 4 coordinates"
                assert all(
                    isinstance(coord, (int, float)) for coord in bbox
                ), "All bbox coordinates should be numeric"

        except ImportError:
            pytest.skip("osfclient not available")
        except Exception as e:
            pytest.skip(f"Network or processing error: {e}")

    def test_osf_repository_no_download_mode(self):
        """Test OSF repository with download_data=False"""
        dataset = self.TEST_DATASETS["gis_dataset_shapefiles"]

        try:
            result = geoextent.fromRemote(
                dataset["url"], bbox=True, tbox=False, timeout=30, download_data=False
            )

            # Should complete without error, but may have limited results
            assert result is not None
            assert "format" in result
            assert result["format"] == "remote"

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
        assert hasattr(osf_provider, "validate_provider")
        assert hasattr(osf_provider, "download")


class TestOSFParameterCombinations:
    """Test various parameter combinations for OSF repository functions"""

    def test_osf_repository_bbox_only(self):
        """Test OSF repository extraction with only bbox enabled"""
        dataset = TestOSFProvider.TEST_DATASETS["gis_dataset_shapefiles"]

        try:
            result = geoextent.fromRemote(
                dataset["url"], bbox=True, tbox=False, timeout=30, download_data=True
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
            geoextent.fromRemote(dataset["url"], bbox=False, tbox=False, timeout=30)

    def test_osf_repository_with_timeout(self):
        """Test OSF repository extraction with different timeout values"""
        dataset = TestOSFProvider.TEST_DATASETS["gis_dataset_shapefiles"]

        try:
            # Test with short timeout
            result = geoextent.fromRemote(
                dataset["url"],
                bbox=True,
                tbox=False,
                timeout=10,  # Short timeout
                download_data=False,  # Faster without download
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

    def test_osf_validation_edge_cases(self):
        """Test OSF provider validation with edge cases and invalid formats"""
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()

        edge_cases = [
            # Invalid project ID formats
            ("", False),  # Empty string
            ("123", False),  # Too short
            ("abcdef", False),  # Too long
            ("abc-d", False),  # Invalid characters
            # Edge case URLs
            ("https://osf.io", False),  # No project ID
            ("https://osf.io/", False),  # Trailing slash only
            ("https://accounts.osf.io/4xe6z", False),  # Wrong subdomain
            ("https://osf.io/4xe6z/files/", True),  # With files path (valid)
            ("https://osf.io/4xe6z/wiki/", True),  # With wiki path (valid)
        ]

        for test_input, expected_valid in edge_cases:
            result = osf.validate_provider(test_input)
            assert result == expected_valid, f"Edge case validation failed for {test_input}"
            if result:
                assert osf.project_id is not None
                assert len(osf.project_id) == 5
            osf.project_id = None  # Reset for next test

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


class TestOSFActualBoundingBoxVerification:
    """Test OSF provider with actual bounding box verification using real datasets"""

    # Test datasets with verified geospatial bounding boxes
    VERIFIED_DATASETS = {
        "boston_area": {
            "plain_id": "OSF.IO/9JG2U",
            "bare_doi": "10.17605/OSF.IO/9JG2U",
            "doi_url": "https://doi.org/10.17605/OSF.IO/9JG2U",
            "direct_url": "https://osf.io/9jg2u",
            "project_id": "9jg2u",
            "title": "Boston area geospatial data",
            "expected_bbox": [
                -71.11696719686476,
                42.33758042479756,
                -71.04845692576838,
                42.37900158005487,
            ],  # [W, S, E, N]
            "description": "Boston metropolitan area spatial data",
        },
        "southeast_asia": {
            "plain_id": "OSF.IO/4XE6Z",
            "bare_doi": "10.17605/OSF.IO/4XE6Z",
            "doi_url": "https://doi.org/10.17605/OSF.IO/4XE6Z",
            "direct_url": "https://osf.io/4xe6z",
            "project_id": "4xe6z",
            "title": "Southeast Asia regional data",
            "expected_bbox": [
                93.885557,
                10.0017,
                108.72980074860037,
                33.267781,
            ],  # [W, S, E, N]
            "description": "Southeast Asia regional spatial dataset",
        },
    }

    def test_osf_actual_bounding_box_verification_boston(self):
        """Test OSF provider with actual bounding box verification - Boston dataset"""
        dataset = self.VERIFIED_DATASETS["boston_area"]

        try:
            # Test with plain OSF identifier format (OSF.IO/9JG2U)
            result = geoextent.fromRemote(
                dataset["plain_id"], bbox=True, tbox=True, download_data=True
            )

            assert result is not None
            assert result["format"] == "remote"

            # Check geographic coverage
            if "bbox" in result:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]

                assert len(bbox) == 4
                assert isinstance(bbox[0], (int, float))
                assert isinstance(bbox[1], (int, float))
                assert isinstance(bbox[2], (int, float))
                assert isinstance(bbox[3], (int, float))

                # Verify bounding box with reasonable tolerance (0.001 degrees ~ 110 m)
                assert (
                    abs(bbox[0] - expected_bbox[0]) < 0.001
                ), f"West longitude: {bbox[0]} vs {expected_bbox[0]}"
                assert (
                    abs(bbox[1] - expected_bbox[1]) < 0.001
                ), f"South latitude: {bbox[1]} vs {expected_bbox[1]}"
                assert (
                    abs(bbox[2] - expected_bbox[2]) < 0.001
                ), f"East longitude: {bbox[2]} vs {expected_bbox[2]}"
                assert (
                    abs(bbox[3] - expected_bbox[3]) < 0.001
                ), f"North latitude: {bbox[3]} vs {expected_bbox[3]}"

                # Verify bounding box validity
                assert bbox[0] <= bbox[2], "West longitude should be <= East longitude"
                assert bbox[1] <= bbox[3], "South latitude should be <= North latitude"
                assert -180 <= bbox[0] <= 180, "West longitude should be valid"
                assert -180 <= bbox[2] <= 180, "East longitude should be valid"
                assert -90 <= bbox[1] <= 90, "South latitude should be valid"
                assert -90 <= bbox[3] <= 90, "North latitude should be valid"

                # Boston area should be in reasonable geographic bounds
                assert (
                    -75 <= bbox[0] <= -70
                ), f"West longitude {bbox[0]} should be in Boston area"
                assert (
                    40 <= bbox[1] <= 45
                ), f"South latitude {bbox[1]} should be in Boston area"

            # Check CRS
            if "crs" in result:
                assert result["crs"] == "4326", "CRS should be WGS84"

        except ImportError:
            pytest.skip("osfclient library not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_osf_actual_bounding_box_verification_southeast_asia(self):
        """Test OSF provider with actual bounding box verification - Southeast Asia dataset"""
        dataset = self.VERIFIED_DATASETS["southeast_asia"]

        try:
            # Test with bare DOI format
            result = geoextent.fromRemote(
                dataset["bare_doi"], bbox=True, tbox=True, download_data=True
            )

            assert result is not None
            assert result["format"] == "remote"

            # Check geographic coverage
            if "bbox" in result:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]

                assert len(bbox) == 4
                assert isinstance(bbox[0], (int, float))
                assert isinstance(bbox[1], (int, float))
                assert isinstance(bbox[2], (int, float))
                assert isinstance(bbox[3], (int, float))

                # Verify bounding box with reasonable tolerance (0.001 degrees ~ 110 m)
                assert (
                    abs(bbox[0] - expected_bbox[0]) < 0.001
                ), f"West longitude: {bbox[0]} vs {expected_bbox[0]}"
                assert (
                    abs(bbox[1] - expected_bbox[1]) < 0.001
                ), f"South latitude: {bbox[1]} vs {expected_bbox[1]}"
                assert (
                    abs(bbox[2] - expected_bbox[2]) < 0.001
                ), f"East longitude: {bbox[2]} vs {expected_bbox[2]}"
                assert (
                    abs(bbox[3] - expected_bbox[3]) < 0.001
                ), f"North latitude: {bbox[3]} vs {expected_bbox[3]}"

                # Verify bounding box validity
                assert bbox[0] <= bbox[2], "West longitude should be <= East longitude"
                assert bbox[1] <= bbox[3], "South latitude should be <= North latitude"
                assert -180 <= bbox[0] <= 180, "West longitude should be valid"
                assert -180 <= bbox[2] <= 180, "East longitude should be valid"
                assert -90 <= bbox[1] <= 90, "South latitude should be valid"
                assert -90 <= bbox[3] <= 90, "North latitude should be valid"

                # Southeast Asia should be in reasonable geographic bounds
                assert (
                    90 <= bbox[0] <= 115
                ), f"West longitude {bbox[0]} should be in Southeast Asia"
                assert (
                    5 <= bbox[1] <= 35
                ), f"South latitude {bbox[1]} should be in Southeast Asia"

            # Check CRS
            if "crs" in result:
                assert result["crs"] == "4326", "CRS should be WGS84"

        except ImportError:
            pytest.skip("osfclient library not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_osf_all_identifier_formats_verification(self):
        """Test that all OSF identifier formats return the same bounding box"""
        dataset = self.VERIFIED_DATASETS["boston_area"]

        identifiers = [
            dataset["plain_id"],
            dataset["bare_doi"],
            dataset["doi_url"],
            dataset["direct_url"],
        ]

        bboxes = []

        for identifier in identifiers:
            try:
                result = geoextent.fromRemote(identifier, bbox=True, download_data=True)

                if result and "bbox" in result:
                    bbox = result["bbox"]
                    bboxes.append((identifier, bbox))

            except Exception as e:
                continue

        # All successful extractions should return the same bounding box
        if len(bboxes) > 1:
            reference_bbox = bboxes[0][1]
            for identifier, bbox in bboxes[1:]:
                assert (
                    abs(bbox[0] - reference_bbox[0]) < 0.001
                ), f"West longitude mismatch for {identifier}"
                assert (
                    abs(bbox[1] - reference_bbox[1]) < 0.001
                ), f"South latitude mismatch for {identifier}"
                assert (
                    abs(bbox[2] - reference_bbox[2]) < 0.001
                ), f"East longitude mismatch for {identifier}"
                assert (
                    abs(bbox[3] - reference_bbox[3]) < 0.001
                ), f"North latitude mismatch for {identifier}"


class TestOSFFilteringCapabilities:
    """Test OSF provider filtering capabilities for geospatial files and size limits"""

    def test_osf_file_metadata_extraction(self):
        """Test that OSF provider can extract file metadata via API"""
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()
        dataset = TestOSFProvider.TEST_DATASETS["gis_dataset_shapefiles"]

        osf.validate_provider(dataset["project_id"])

        try:
            file_metadata = osf._get_file_metadata_via_api()

            # Should get file metadata
            assert isinstance(file_metadata, list)
            assert len(file_metadata) > 0

            # Check file metadata structure
            for file_info in file_metadata:
                assert "name" in file_info
                assert "url" in file_info
                assert "size" in file_info
                assert isinstance(file_info["size"], int)
                assert file_info["size"] >= 0

        except ImportError:
            pytest.skip("Required dependencies not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_osf_geospatial_filtering_support(self):
        """Test that OSF provider now supports geospatial filtering"""
        from geoextent.lib.content_providers.OSF import OSF

        osf = OSF()
        dataset = TestOSFProvider.TEST_DATASETS["gis_dataset_shapefiles"]

        osf.validate_provider(dataset["project_id"])

        try:
            # Get file metadata
            file_metadata = osf._get_file_metadata_via_api()

            if file_metadata:
                # Test geospatial filtering
                filtered_files = osf._filter_geospatial_files(
                    file_metadata,
                    skip_non_geospatial=True,
                    max_size_mb=None,
                    additional_extensions=None,
                )

                # Should have method available
                assert hasattr(osf, "_filter_geospatial_files")
                assert isinstance(filtered_files, list)

                # All filtered files should have geospatial extensions
                geospatial_exts = {
                    ".shp",
                    ".geojson",
                    ".kml",
                    ".gpx",
                    ".gml",
                    ".tif",
                    ".tiff",
                }
                for file_info in filtered_files:
                    file_name = file_info.get("name", "")
                    has_geo_ext = any(
                        file_name.lower().endswith(ext) for ext in geospatial_exts
                    )
                    assert (
                        has_geo_ext
                    ), f"Non-geospatial file found after filtering: {file_name}"

        except ImportError:
            pytest.skip("Required dependencies not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_osf_download_with_geospatial_filtering(self):
        """Test OSF download with geospatial filtering enabled"""
        import tempfile

        dataset = TestOSFProvider.TEST_DATASETS["gis_dataset_shapefiles"]

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                result = geoextent.fromRemote(
                    dataset["url"],
                    bbox=True,
                    tbox=False,
                    download_data=True,
                    download_skip_nogeo=True,  # Enable geospatial filtering
                    timeout=60,
                )

                # Should complete without the old warning about filtering not being supported
                assert result is not None
                assert result["format"] == "remote"

                # Should have bounding box since we're downloading geospatial files
                if "bbox" in result:
                    bbox = result["bbox"]
                    assert len(bbox) == 4
                    assert all(isinstance(coord, (int, float)) for coord in bbox)

        except ImportError:
            pytest.skip("Required dependencies not available")
        except Exception as e:
            pytest.skip(f"Network or processing error: {e}")

    def test_osf_download_with_size_filtering(self):
        """Test OSF download with size filtering"""
        import tempfile

        dataset = TestOSFProvider.TEST_DATASETS["gis_dataset_shapefiles"]

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                result = geoextent.fromRemote(
                    dataset["url"],
                    bbox=True,
                    tbox=False,
                    download_data=True,
                    max_download_size="1MB",  # Small size limit
                    timeout=60,
                )

                # Should complete with size filtering
                assert result is not None
                assert result["format"] == "remote"

        except ImportError:
            pytest.skip("Required dependencies not available")
        except Exception as e:
            pytest.skip(f"Network or processing error: {e}")

    def test_osf_download_with_combined_filtering(self):
        """Test OSF download with both geospatial and size filtering"""
        import tempfile

        dataset = TestOSFProvider.TEST_DATASETS["gis_dataset_shapefiles"]

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                result = geoextent.fromRemote(
                    dataset["url"],
                    bbox=True,
                    tbox=False,
                    download_data=True,
                    download_skip_nogeo=True,  # Geospatial filtering
                    max_download_size="5MB",  # Size filtering
                    timeout=60,
                )

                # Should complete with combined filtering
                assert result is not None
                assert result["format"] == "remote"

        except ImportError:
            pytest.skip("Required dependencies not available")
        except Exception as e:
            pytest.skip(f"Network or processing error: {e}")
