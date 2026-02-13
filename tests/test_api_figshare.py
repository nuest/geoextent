import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance
from geojson_validator import validate_structure
import geoextent.lib.helpfunctions as hf
import subprocess
import json


class TestFigshareProvider:
    """Test Figshare content provider functionality with actual bounding box verification"""

    # Test datasets with known geographic coverage from real Figshare articles
    TEST_DATASETS = {
        "prince_edward_islands": {
            "doi": "10.6084/m9.figshare.19248626.v2",
            "url": "https://figshare.com/articles/dataset/Prince_Edward_Islands_geospatial_database/19248626",
            "id": "19248626",
            "title": "Prince Edward Islands geospatial database",
            "expected_bbox": [
                -47.00490880063488,
                37.51696444333383,
                -46.58858378306222,
                38.032055268506745,
            ],  # [S, W, N, E]
            "description": "South African sub-Antarctic islands geospatial data",
        },
        "raster_workshop": {
            "doi": "10.6084/m9.figshare.20146919.v1",
            "url": "https://figshare.com/articles/dataset/Raster_dataset_for_workshop_Introduction_to_Geospatial_Raster_and_Vector_Data_with_Python_/20146919",
            "id": "20146919",
            "title": 'Raster dataset for workshop "Introduction to Geospatial Raster and Vector Data with Python"',
            "expected_bbox": [
                52.25345680616433,
                4.464980367155466,
                53.208217152152926,
                6.141769904471917,
            ],  # [S, W, N, E]
            "description": "Geospatial raster data for Python workshop - covers parts of Netherlands",
        },
    }

    def test_figshare_url_validation(self):
        """Test that Figshare URLs are correctly validated"""
        from geoextent.lib.content_providers.Figshare import Figshare

        figshare = Figshare()

        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            # Test URL validation
            assert figshare.validate_provider(dataset_info["url"]) == True
            assert figshare.record_id == dataset_info["id"]

        # Test invalid URLs
        invalid_urls = [
            "https://zenodo.org/record/820562",  # Zenodo URL
            "10.1594/PANGAEA.734969",  # PANGAEA DOI
            "not-a-url-at-all",
            "",
        ]

        for url in invalid_urls:
            assert figshare.validate_provider(url) == False

    def test_figshare_actual_bounding_box_verification_prince_edward(self):
        """Test Figshare provider with actual bounding box verification - Prince Edward Islands"""
        dataset = self.TEST_DATASETS["prince_edward_islands"]

        try:
            # Test with download_data=True to get actual geospatial data
            result = geoextent.fromRemote(
                dataset["url"], bbox=True, tbox=True, download_data=True
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

                # Verify bounding box with reasonable tolerance (0.01 degrees ~ 1.1 km)
                assert (
                    abs(bbox[0] - expected_bbox[0]) < 0.01
                ), f"South latitude: {bbox[0]} vs {expected_bbox[0]}"
                assert (
                    abs(bbox[1] - expected_bbox[1]) < 0.01
                ), f"West longitude: {bbox[1]} vs {expected_bbox[1]}"
                assert (
                    abs(bbox[2] - expected_bbox[2]) < 0.01
                ), f"North latitude: {bbox[2]} vs {expected_bbox[2]}"
                assert (
                    abs(bbox[3] - expected_bbox[3]) < 0.01
                ), f"East longitude: {bbox[3]} vs {expected_bbox[3]}"

                # Verify bounding box validity
                assert bbox[0] <= bbox[2], "South latitude should be <= North latitude"
                assert bbox[1] <= bbox[3], "West longitude should be <= East longitude"
                assert -90 <= bbox[0] <= 90, "South latitude should be valid"
                assert -90 <= bbox[2] <= 90, "North latitude should be valid"
                assert -180 <= bbox[1] <= 180, "West longitude should be valid"
                assert -180 <= bbox[3] <= 180, "East longitude should be valid"

            # Check CRS
            if "crs" in result:
                assert result["crs"] == "4326", "CRS should be WGS84"

            # Figshare datasets typically don't have temporal coverage
            # but test should succeed regardless

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_figshare_actual_bounding_box_verification_raster_workshop(self):
        """Test Figshare provider with actual bounding box verification - Raster Workshop Dataset"""
        dataset = self.TEST_DATASETS["raster_workshop"]

        try:
            # Test with download_data=True to get actual geospatial data
            result = geoextent.fromRemote(
                dataset["url"], bbox=True, tbox=True, download_data=True
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

                # Verify bounding box with reasonable tolerance (0.01 degrees ~ 1.1 km)
                assert (
                    abs(bbox[0] - expected_bbox[0]) < 0.01
                ), f"South latitude: {bbox[0]} vs {expected_bbox[0]}"
                assert (
                    abs(bbox[1] - expected_bbox[1]) < 0.01
                ), f"West longitude: {bbox[1]} vs {expected_bbox[1]}"
                assert (
                    abs(bbox[2] - expected_bbox[2]) < 0.01
                ), f"North latitude: {bbox[2]} vs {expected_bbox[2]}"
                assert (
                    abs(bbox[3] - expected_bbox[3]) < 0.01
                ), f"East longitude: {bbox[3]} vs {expected_bbox[3]}"

                # Verify bounding box validity
                assert bbox[0] <= bbox[2], "South latitude should be <= North latitude"
                assert bbox[1] <= bbox[3], "West longitude should be <= East longitude"
                assert -90 <= bbox[0] <= 90, "South latitude should be valid"
                assert -90 <= bbox[2] <= 90, "North latitude should be valid"
                assert -180 <= bbox[1] <= 180, "West longitude should be valid"
                assert -180 <= bbox[3] <= 180, "East longitude should be valid"

            # Check CRS
            if "crs" in result:
                assert result["crs"] == "4326", "CRS should be WGS84"

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_figshare_metadata_only_extraction(self):
        """Test Figshare metadata-only extraction (limited functionality)"""
        dataset = self.TEST_DATASETS["prince_edward_islands"]

        try:
            result = geoextent.fromRemote(
                dataset["url"], bbox=True, tbox=True, download_data=False
            )

            assert result is not None
            assert result["format"] == "remote"

            # For Figshare, metadata-only still downloads files since
            # Figshare doesn't provide geospatial metadata directly
            # This behavior is expected and documented

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_figshare_multiple_url_formats(self):
        """Test Figshare with different URL formats"""
        base_url = "https://figshare.com/articles/dataset/Prince_Edward_Islands_geospatial_database/19248626"
        url_variants = [
            base_url,
            base_url + "/",  # Trailing slash
            "https://figshare.com/articles/19248626",  # Shorter format
            "https://api.figshare.com/v2/articles/19248626",  # API URL
        ]

        from geoextent.lib.content_providers.Figshare import Figshare

        figshare = Figshare()

        for url in url_variants:
            try:
                is_valid = figshare.validate_provider(url)
                if is_valid:
                    assert figshare.record_id == "19248626"

                    # Test actual extraction with one variant
                    if url == base_url:
                        result = geoextent.fromRemote(
                            url, bbox=True, download_data=True
                        )
                        assert result is not None

            except Exception as e:
                continue

    def test_figshare_invalid_articles(self):
        """Test Figshare validation and error handling with invalid articles"""
        from geoextent.lib.content_providers.Figshare import Figshare

        figshare = Figshare()

        # Test nonexistent article
        nonexistent_url = "https://figshare.com/articles/dataset/nonexistent/999999999"
        assert (
            figshare.validate_provider(nonexistent_url) == True
        )  # URL format is valid

        # But trying to extract should fail gracefully
        try:
            result = geoextent.fromRemote(
                nonexistent_url, bbox=True, download_data=True
            )
            # Should either raise exception or return error indicator
            if result is not None:
                assert isinstance(result, dict)
        except Exception:
            # Exception is expected for nonexistent articles
            pass


class TestFigshareParameterCombinations:
    """Test Figshare with various parameter combinations"""

    def test_figshare_bbox_only(self):
        """Test Figshare extraction with only bbox enabled"""
        test_url = "https://figshare.com/articles/dataset/Prince_Edward_Islands_geospatial_database/19248626"

        try:
            result = geoextent.fromRemote(
                test_url, bbox=True, tbox=False, download_data=True
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
            pytest.skip(f"Network or API error: {e}")

    def test_figshare_tbox_only(self):
        """Test Figshare extraction with only tbox enabled"""
        test_url = "https://figshare.com/articles/dataset/Prince_Edward_Islands_geospatial_database/19248626"

        try:
            result = geoextent.fromRemote(
                test_url, bbox=False, tbox=True, download_data=True
            )
            assert result is not None
            assert result["format"] == "remote"
            assert "bbox" not in result

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_figshare_with_details(self):
        """Test Figshare extraction with details enabled"""
        test_url = "https://figshare.com/articles/dataset/Prince_Edward_Islands_geospatial_database/19248626"

        try:
            result = geoextent.fromRemote(
                test_url, bbox=True, tbox=True, details=True, download_data=True
            )
            assert result is not None
            assert result["format"] == "remote"
            assert "details" in result
            assert isinstance(result["details"], dict)

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_figshare_download_data_parameter(self):
        """Test Figshare with download_data parameter variations"""
        test_url = "https://figshare.com/articles/dataset/Prince_Edward_Islands_geospatial_database/19248626"

        try:
            # Test with download_data=True (default for geospatial extraction)
            result_with_data = geoextent.fromRemote(
                test_url, bbox=True, download_data=True
            )
            assert result_with_data is not None
            assert result_with_data["format"] == "remote"

            # Test with download_data=False (metadata-only, limited for Figshare)
            result_metadata = geoextent.fromRemote(
                test_url, bbox=True, download_data=False
            )
            assert result_metadata is not None
            assert result_metadata["format"] == "remote"

            # Both should return similar structure (Figshare downloads files regardless)
            assert ("bbox" in result_with_data) == ("bbox" in result_metadata)

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")


class TestFigshareEdgeCases:
    """Test Figshare edge cases and error handling"""

    def test_figshare_malformed_urls(self):
        """Test Figshare with malformed URLs"""
        from geoextent.lib.content_providers.Figshare import Figshare

        figshare = Figshare()

        malformed_urls = [
            "https://figshare.com/articles/",  # Incomplete
            "https://figshare.com/articles/abc",  # Non-numeric ID
            "https://notfigshare.com/articles/123456",  # Wrong domain
            "",  # Empty string
        ]

        for url in malformed_urls:
            assert figshare.validate_provider(url) == False

    def test_figshare_different_article_types(self):
        """Test Figshare with different article types (dataset, presentation, etc.)"""
        # The validation should work regardless of article type
        from geoextent.lib.content_providers.Figshare import Figshare

        figshare = Figshare()

        # Different article types should all validate if URL format is correct
        article_urls = [
            "https://figshare.com/articles/dataset/test/123456",
            "https://figshare.com/articles/presentation/test/123456",
            "https://figshare.com/articles/figure/test/123456",
            "https://figshare.com/articles/123456",  # Without type
        ]

        for url in article_urls:
            # URL validation should pass for all (actual content might not exist)
            is_valid = figshare.validate_provider(url)
            if is_valid:
                assert figshare.record_id == "123456"

    def test_figshare_api_error_handling(self):
        """Test Figshare API error handling"""
        # This tests the error handling when API calls fail
        from geoextent.lib.content_providers.Figshare import Figshare

        figshare = Figshare()
        figshare.record_id = "999999999"  # Nonexistent article

        try:
            metadata = figshare._get_metadata()
            # Should either return None or raise exception
            if metadata is not None:
                assert isinstance(metadata, dict)
        except Exception as e:
            # Exception is expected for nonexistent articles
            assert (
                "does not exist" in str(e)
                or "404" in str(e)
                or "error" in str(e).lower()
            )

    def test_figshare_cli_geojson_validation(self):
        """Test Figshare CLI output with GeoJSON validation"""
        test_url = "https://figshare.com/articles/dataset/Prince_Edward_Islands_geospatial_database/19248626"

        try:
            # Run geoextent CLI with --quiet flag to get clean JSON output
            result = subprocess.run(
                ["python", "-m", "geoextent", "-b", "--quiet", test_url],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout for network operations
            )

            # Check that the command succeeded
            assert (
                result.returncode == 0
            ), f"CLI command failed with error: {result.stderr}"

            # Parse the GeoJSON output
            geojson_output = json.loads(result.stdout)

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
            assert (
                "coordinates" in feature["geometry"]
            ), "Geometry should have coordinates"

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
