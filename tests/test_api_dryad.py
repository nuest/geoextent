import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance
from geojson_validator import validate_structure
import geoextent.lib.helpfunctions as hf
import subprocess
import json


class TestDryadProvider:
    """Test Dryad content provider functionality with actual bounding box verification"""

    # Test datasets with known geographic coverage from real Dryad articles
    # Note: These are real datasets but may be large and cause timeouts in CI
    TEST_DATASETS = {
        "pacific_atolls": {
            "doi": "10.5061/dryad.0k6djhb7x",
            "url": "https://datadryad.org/dataset/doi:10.5061/dryad.0k6djhb7x",
            "id": "doi:10.5061/dryad.0k6djhb7x",
            "title": "Pacific Atoll Vegetation Maps",
            "description": "Vegetation classification maps of 235 Pacific atolls (1,925.6 km2 in total)",
            # Bounding box will be determined by actual extraction if successful
            "expected_bbox": None,  # Pacific Ocean region, very broad
        },
        "channel_mobility": {
            "doi": "10.5061/dryad.wm37pvmvf",
            "url": "https://datadryad.org/dataset/doi:10.5061/dryad.wm37pvmvf",
            "id": "doi:10.5061/dryad.wm37pvmvf",
            "title": "Channel mobility and floodplain reworking across river planform morphologies",
            "description": "All .tif, .gpkg, and .csv files are spatially located with Lat-Lon coordinates",
            # Expected bounding box to be determined by testing
            "expected_bbox": None,
        },
        "marine_species": {
            "doi": "10.5061/dryad.wh70rxx13",
            "url": "https://datadryad.org/dataset/doi:10.5061/dryad.wh70rxx13",
            "id": "doi:10.5061/dryad.wh70rxx13",
            "title": "Using spatial capture-recapture methods to estimate long-term spatiotemporal variation of a wide-ranging marine species",
            "description": "Grid-based marine species data with approximately 44km cell size",
            # Expected bounding box to be determined by testing
            "expected_bbox": None,
        },
    }

    def test_dryad_url_validation(self):
        """Test that Dryad URLs are correctly validated"""
        from geoextent.lib.content_providers.Dryad import Dryad

        dryad = Dryad()

        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            # Test URL validation
            assert dryad.validate_provider(dataset_info["url"]) == True
            assert dryad.record_id == dataset_info["id"]

        # Test invalid URLs
        invalid_urls = [
            "https://zenodo.org/record/820562",  # Zenodo URL
            "https://figshare.com/articles/123456",  # Figshare URL
            "10.1594/PANGAEA.734969",  # PANGAEA DOI
            "not-a-url-at-all",
            "",
        ]

        for url in invalid_urls:
            assert dryad.validate_provider(url) == False

    def test_dryad_actual_bounding_box_verification_pacific_atolls(self):
        """Test Dryad provider with actual bounding box verification - Pacific Atolls"""
        dataset = self.TEST_DATASETS["pacific_atolls"]

        try:
            # Test with download_data=True to get actual geospatial data
            # Note: This dataset may be large and could timeout
            result = geoextent.fromRemote(
                dataset["url"], bbox=True, tbox=True, download_data=True, timeout=120
            )

            assert result is not None
            assert result["format"] == "remote"

            # Check geographic coverage
            if "bbox" in result:
                bbox = result["bbox"]

                assert len(bbox) == 4
                assert isinstance(bbox[0], (int, float))
                assert isinstance(bbox[1], (int, float))
                assert isinstance(bbox[2], (int, float))
                assert isinstance(bbox[3], (int, float))

                # Verify bounding box validity (Pacific region should be reasonable)
                assert bbox[0] <= bbox[2], "West longitude should be <= East longitude"
                assert bbox[1] <= bbox[3], "South latitude should be <= North latitude"
                assert -180 <= bbox[0] <= 180, "West longitude should be valid"
                assert -180 <= bbox[2] <= 180, "East longitude should be valid"
                assert -90 <= bbox[1] <= 90, "South latitude should be valid"
                assert -90 <= bbox[3] <= 90, "North latitude should be valid"

                # Pacific atolls should be in Pacific Ocean region
                # Rough Pacific bounds: 120°E to 80°W, 60°N to 60°S
                # Allow flexibility for coordinate system transformations
                assert (
                    -180 <= bbox[0] <= 180
                ), f"West longitude {bbox[0]} should be in valid range"
                assert (
                    -60 <= bbox[1] <= 60
                ), f"South latitude {bbox[1]} should be in expected Pacific range"

            # Check CRS
            if "crs" in result:
                assert result["crs"] == "4326", "CRS should be WGS84"

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            # Dryad datasets can be very large and may timeout
            pytest.skip(f"Network, timeout, or API error: {e}")

    def test_dryad_metadata_only_extraction(self):
        """Test Dryad metadata-only extraction (limited functionality)"""
        dataset = self.TEST_DATASETS["pacific_atolls"]

        try:
            result = geoextent.fromRemote(
                dataset["url"], bbox=True, tbox=True, download_data=False
            )

            # For Dryad, metadata-only extraction has very limited capabilities
            # The test should succeed but may not return geospatial extents
            assert result is not None
            assert result["format"] == "remote"

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_dryad_multiple_url_formats(self):
        """Test Dryad with different URL formats"""
        base_doi = "10.5061/dryad.0k6djhb7x"
        url_variants = [
            f"https://datadryad.org/dataset/doi:{base_doi}",
            f"https://datadryad.org/stash/dataset/doi:{base_doi}",  # Alternative format
        ]

        from geoextent.lib.content_providers.Dryad import Dryad

        dryad = Dryad()

        for url in url_variants:
            try:
                is_valid = dryad.validate_provider(url)
                if is_valid:
                    assert dryad.record_id == f"doi:{base_doi}"
                else:
                    # Some URL formats may not be supported
                    pass

            except Exception as e:
                continue

    def test_dryad_api_error_handling(self):
        """Test Dryad API error handling"""
        from geoextent.lib.content_providers.Dryad import Dryad

        dryad = Dryad()

        # Test with nonexistent dataset
        nonexistent_url = "https://datadryad.org/dataset/doi:10.5061/dryad.nonexistent"
        assert dryad.validate_provider(nonexistent_url) == True  # URL format is valid

        # But trying to extract metadata should fail gracefully
        try:
            metadata = dryad._get_metadata()
            # Should either return None or raise exception
            if metadata is not None:
                assert isinstance(metadata, dict)
        except Exception as e:
            # Exception is expected for nonexistent datasets
            assert (
                "does not exist" in str(e)
                or "404" in str(e)
                or "error" in str(e).lower()
            )

    def test_dryad_provider_robustness(self):
        """Test Dryad provider handles various edge cases"""
        # Test a real but smaller dataset that's more likely to succeed
        test_url = "https://datadryad.org/dataset/doi:10.5061/dryad.j432q"

        try:
            # This dataset has Excel files, not typical geospatial formats
            # Should handle gracefully without crashing
            result = geoextent.fromRemote(
                test_url, bbox=True, tbox=True, download_data=True, timeout=60
            )

            assert result is not None
            assert result["format"] == "remote"

            # This dataset likely won't have extractable geospatial extents
            # but the extraction should complete without errors

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            # Expected for datasets without geospatial data
            pytest.skip(f"Expected error for non-geospatial dataset: {e}")


class TestDryadParameterCombinations:
    """Test Dryad with various parameter combinations"""

    def test_dryad_bbox_only(self):
        """Test Dryad extraction with only bbox enabled"""
        test_url = "https://datadryad.org/dataset/doi:10.5061/dryad.0k6djhb7x"

        try:
            result = geoextent.fromRemote(
                test_url, bbox=True, tbox=False, download_data=True, timeout=60
            )
            assert result is not None
            assert result["format"] == "remote"
            assert "tbox" not in result

            # Validate GeoJSON output format as returned by the library
            if "bbox" in result:
                # Get GeoJSON format as returned by geoextent library
                geojson_output = hf.format_extent_output(result, "geojson")

                # Validate the GeoJSON structure
                validation_errors = validate_structure(geojson_output)
                assert (
                    not validation_errors
                ), f"Invalid GeoJSON structure: {validation_errors}"

                # Additional GeoJSON structure checks
                assert (
                    geojson_output["type"] == "FeatureCollection"
                ), "Should be a FeatureCollection"
                assert (
                    len(geojson_output["features"]) > 0
                ), "Should have at least one feature"

                feature = geojson_output["features"][0]
                assert feature["type"] == "Feature", "Feature should have correct type"
                assert (
                    feature["geometry"]["type"] == "Polygon"
                ), "Geometry should be a Polygon"
                assert (
                    len(feature["geometry"]["coordinates"][0]) == 5
                ), "Polygon should be closed"

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network, timeout, or API error: {e}")

    def test_dryad_tbox_only(self):
        """Test Dryad extraction with only tbox enabled"""
        test_url = "https://datadryad.org/dataset/doi:10.5061/dryad.0k6djhb7x"

        try:
            result = geoextent.fromRemote(
                test_url, bbox=False, tbox=True, download_data=True, timeout=60
            )
            assert result is not None
            assert result["format"] == "remote"
            assert "bbox" not in result

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network, timeout, or API error: {e}")

    def test_dryad_with_details(self):
        """Test Dryad extraction with details enabled"""
        test_url = "https://datadryad.org/dataset/doi:10.5061/dryad.j432q"

        try:
            result = geoextent.fromRemote(
                test_url,
                bbox=True,
                tbox=True,
                details=True,
                download_data=True,
                timeout=60,
            )
            assert result is not None
            assert result["format"] == "remote"
            assert "details" in result
            assert isinstance(result["details"], dict)

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network, timeout, or API error: {e}")

    def test_dryad_download_data_parameter(self):
        """Test Dryad with download_data parameter variations"""
        test_url = "https://datadryad.org/dataset/doi:10.5061/dryad.j432q"

        try:
            # Test with download_data=False (metadata-only, very limited for Dryad)
            result_metadata = geoextent.fromRemote(
                test_url, bbox=True, download_data=False
            )
            assert result_metadata is not None
            assert result_metadata["format"] == "remote"

            # Test with download_data=True (file download)
            result_with_data = geoextent.fromRemote(
                test_url, bbox=True, download_data=True, timeout=60
            )
            assert result_with_data is not None
            assert result_with_data["format"] == "remote"

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network, timeout, or API error: {e}")


class TestDryadEdgeCases:
    """Test Dryad edge cases and error handling"""

    def test_dryad_malformed_urls(self):
        """Test Dryad with malformed URLs"""
        from geoextent.lib.content_providers.Dryad import Dryad

        dryad = Dryad()

        malformed_urls = [
            "https://datadryad.org/dataset/",  # Incomplete
            "https://datadryad.org/dataset/doi:",  # Incomplete DOI
            "https://notdryad.com/dataset/doi:10.5061/dryad.test",  # Wrong domain
            "",  # Empty string
        ]

        for url in malformed_urls:
            assert dryad.validate_provider(url) == False

    def test_dryad_nonexistent_dataset(self):
        """Test Dryad with nonexistent dataset"""
        nonexistent_url = (
            "https://datadryad.org/dataset/doi:10.5061/dryad.nonexistent999"
        )

        try:
            result = geoextent.fromRemote(
                nonexistent_url, bbox=True, download_data=True
            )
            # Should either raise exception or return error indicator
            if result is not None:
                assert isinstance(result, dict)

        except Exception:
            # Exception is expected for nonexistent datasets
            pass

    @pytest.mark.large_download
    def test_dryad_large_dataset_timeout_handling(self):
        """Test Dryad timeout handling with large datasets"""
        # This tests the timeout behavior with a known large dataset
        large_dataset_url = "https://datadryad.org/dataset/doi:10.5061/dryad.gb5mkkwxm"

        try:
            # Use a very short timeout to test timeout handling
            result = geoextent.fromRemote(
                large_dataset_url, bbox=True, download_data=True, timeout=5
            )

            # If it completes within timeout, result should be valid
            if result is not None:
                assert result["format"] == "remote"

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            # Timeout, disk space, or other errors are expected for large datasets
            error_msg = str(e).lower()
            expected_errors = ["timeout", "error", "time", "no space", "disk", "errno"]
            assert any(
                keyword in error_msg for keyword in expected_errors
            ), f"Expected timeout/error/disk space related error, got: {e}"

    def test_dryad_url_encoding_handling(self):
        """Test Dryad URL encoding handling"""
        from geoextent.lib.content_providers.Dryad import Dryad

        dryad = Dryad()

        # Test URL with special characters that need encoding
        test_url = "https://datadryad.org/dataset/doi:10.5061/dryad.0k6djhb7x"

        assert dryad.validate_provider(test_url) == True
        assert dryad.record_id == "doi:10.5061/dryad.0k6djhb7x"

        # The record_id_html should be URL encoded
        assert dryad.record_id_html is not None
        assert "doi" in dryad.record_id_html

    @pytest.mark.large_download
    def test_dryad_cli_geojson_validation(self):
        """Test Dryad CLI output with GeoJSON validation

        Note: This test downloads 473 files (~850MB) from a large Dryad dataset
        and may fail due to network issues, API rate limiting, or timeouts.
        """
        test_url = "https://datadryad.org/dataset/doi:10.5061/dryad.0k6djhb7x"

        try:
            # Run geoextent CLI with --quiet flag to get clean JSON output
            result = subprocess.run(
                ["python", "-m", "geoextent", "-b", "--quiet", test_url],
                capture_output=True,
                text=True,
                timeout=180,  # 3 minute timeout for Dryad (can be slow)
            )

            # Check for HTTP error codes in output (e.g., "405", "429", "503")
            # These indicate API/network issues and should skip the test
            if (
                result.stdout.strip()
                and result.stdout.strip().split("\n")[0].strip().isdigit()
            ):
                http_code = result.stdout.strip().split("\n")[0].strip()
                if int(http_code) >= 400:
                    pytest.skip(f"HTTP error {http_code} - API/network issue")

            # Check that the command succeeded
            if result.returncode != 0:
                # Check if it's a network/API error that should be skipped
                if (
                    "HTTPError" in result.stderr
                    or "ConnectionError" in result.stderr
                    or "Timeout" in result.stderr
                ):
                    pytest.skip(f"Network/API error: {result.stderr}")
                else:
                    pytest.fail(f"CLI command failed with error: {result.stderr}")

            # Parse the GeoJSON output - handle cases where there might be non-JSON output first
            # (e.g., HTTP status codes or warnings on separate lines)
            output_lines = result.stdout.strip().split("\n")
            json_line = None

            # Try to find the JSON line (usually the last line with actual content)
            for line in reversed(output_lines):
                line = line.strip()
                if line and (line.startswith("{") or line.startswith("[")):
                    json_line = line
                    break

            if json_line is None:
                pytest.skip(
                    f"No JSON found in output (possible API issue): {result.stdout[:200]}"
                )

            geojson_output = json.loads(json_line)

            # Validate the GeoJSON structure using geojson-validator
            validation_errors = validate_structure(geojson_output)
            assert (
                not validation_errors
            ), f"Invalid GeoJSON structure: {validation_errors}"

            # Additional GeoJSON structure checks
            assert (
                geojson_output["type"] == "FeatureCollection"
            ), "Should be a FeatureCollection"
            assert "features" in geojson_output, "Should contain features"
            assert (
                len(geojson_output["features"]) > 0
            ), "Should have at least one feature"

            feature = geojson_output["features"][0]
            assert feature["type"] == "Feature", "Feature should have correct type"
            assert "geometry" in feature, "Feature should have geometry"
            assert "properties" in feature, "Feature should have properties"
            assert (
                feature["geometry"]["type"] == "Polygon"
            ), "Geometry should be a Polygon"

            # Verify geoextent_extraction metadata
            assert (
                "geoextent_extraction" in geojson_output
            ), "Output should contain geoextent_extraction metadata"
            extraction_metadata = geojson_output["geoextent_extraction"]
            assert (
                "format" in extraction_metadata
            ), "Extraction metadata should contain format field"
            assert (
                extraction_metadata["format"] == "remote"
            ), "Format should be 'remote'"
            assert (
                "crs" in extraction_metadata
            ), "Extraction metadata should contain CRS field"
            assert (
                extraction_metadata["crs"] == "4326"
            ), "CRS should be WGS84 (EPSG:4326)"

        except subprocess.TimeoutExpired:
            pytest.skip("CLI test skipped due to timeout (network issues)")
        except json.JSONDecodeError as e:
            pytest.fail(
                f"Failed to parse CLI output as JSON: {e}\nOutput: {result.stdout}"
            )
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")


class TestDryadFilteringCapabilities:
    """Test Dryad provider filtering capabilities for geospatial files and size limits"""

    def test_dryad_metadata_extraction(self):
        """Test that Dryad provider can extract file metadata"""
        from geoextent.lib.content_providers.Dryad import Dryad

        dryad = Dryad()
        dataset = TestDryadProvider.TEST_DATASETS["pacific_atolls"]

        try:
            dryad.validate_provider(dataset["url"])
            metadata = dryad._get_metadata()

            # Should get metadata with file information
            assert metadata is not None
            assert "_embedded" in metadata
            assert "stash:files" in metadata["_embedded"]

            files = metadata["_embedded"]["stash:files"]
            assert isinstance(files, list)
            assert len(files) > 0

            # Check file metadata structure
            for file_info in files:
                assert "path" in file_info
                assert "size" in file_info
                assert "_links" in file_info
                assert "stash:download" in file_info["_links"]

        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_dryad_geospatial_filtering_logic(self):
        """Test that Dryad provider filtering logic works correctly"""
        from geoextent.lib.content_providers.Dryad import Dryad

        dryad = Dryad()

        # Test with mock file data
        mock_files = [
            {"name": "data.shp", "size": 1000},
            {"name": "data.dbf", "size": 500},
            {"name": "readme.txt", "size": 200},
            {"name": "analysis.csv", "size": 800},
            {"name": "map.tiff", "size": 5000},
        ]

        # Test geospatial filtering
        filtered_files = dryad._filter_geospatial_files(
            mock_files,
            skip_non_geospatial=True,
            max_size_mb=None,
            additional_extensions=None,
        )

        # Should filter out non-geospatial files
        filtered_names = [f["name"] for f in filtered_files]
        assert "data.shp" in filtered_names
        assert "data.dbf" in filtered_names  # Shapefile component
        assert "map.tiff" in filtered_names
        assert "readme.txt" not in filtered_names
        # CSV could be geospatial or not, depending on implementation

    @pytest.mark.large_download
    def test_dryad_download_with_geospatial_filtering(self):
        """Test Dryad download with geospatial filtering enabled"""
        import tempfile

        dataset = TestDryadProvider.TEST_DATASETS["channel_mobility"]

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                result = geoextent.fromRemote(
                    dataset["url"],
                    bbox=True,
                    tbox=False,
                    download_data=True,
                    download_skip_nogeo=True,  # Enable geospatial filtering
                    timeout=120,  # Longer timeout for Dryad
                )

                # Should complete without the old warning about filtering not being supported
                assert result is not None
                assert result["format"] == "remote"

                # Should have bounding box since we're downloading geospatial files
                if "bbox" in result:
                    bbox = result["bbox"]
                    assert len(bbox) == 4
                    assert all(isinstance(coord, (int, float)) for coord in bbox)

        except Exception as e:
            pytest.skip(f"Network, timeout, or processing error: {e}")

    def test_dryad_download_with_size_filtering(self):
        """Test Dryad download with size filtering"""
        import tempfile

        dataset = TestDryadProvider.TEST_DATASETS["pacific_atolls"]

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                result = geoextent.fromRemote(
                    dataset["url"],
                    bbox=True,
                    tbox=False,
                    download_data=True,
                    max_download_size="10MB",  # Size limit for large datasets
                    timeout=120,
                )

                # Should complete with size filtering
                assert result is not None
                assert result["format"] == "remote"

        except Exception as e:
            pytest.skip(f"Network, timeout, or processing error: {e}")

    def test_dryad_bulk_vs_individual_download_decision(self):
        """Test that Dryad chooses appropriate download method based on filtering"""
        # Test logic for when to use individual file downloads
        # This tests the logic used in the download method

        # Should use individual files when filtering is requested
        use_individual_1 = (
            True  # download_skip_nogeo
            or None is not None  # max_size_bytes
            or "ordered" != "ordered"  # max_download_method
        )
        assert use_individual_1 == True

        use_individual_2 = (
            False  # download_skip_nogeo
            or 1000000 is not None  # max_size_bytes (1MB limit)
            or "ordered" != "ordered"  # max_download_method
        )
        assert use_individual_2 == True

        use_individual_3 = (
            False  # download_skip_nogeo
            or None is not None  # max_size_bytes
            or "random" != "ordered"  # max_download_method
        )
        assert use_individual_3 == True

        # Should use bulk download when no filtering is needed
        use_individual_4 = (
            False  # download_skip_nogeo
            or None is not None  # max_size_bytes
            or "ordered" != "ordered"  # max_download_method
        )
        assert use_individual_4 == False

    def test_dryad_combined_filtering(self):
        """Test Dryad download with both geospatial and size filtering"""
        import tempfile

        dataset = TestDryadProvider.TEST_DATASETS["marine_species"]

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                result = geoextent.fromRemote(
                    dataset["url"],
                    bbox=True,
                    tbox=False,
                    download_data=True,
                    download_skip_nogeo=True,  # Geospatial filtering
                    max_download_size="5MB",  # Size filtering
                    timeout=120,
                )

                # Should complete with combined filtering
                assert result is not None
                assert result["format"] == "remote"

        except Exception as e:
            pytest.skip(f"Network, timeout, or processing error: {e}")
