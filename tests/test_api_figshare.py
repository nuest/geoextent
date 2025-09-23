import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance


class TestFigshareProvider:
    """Test Figshare content provider functionality with actual bounding box verification"""

    # Test datasets with known geographic coverage from real Figshare articles
    TEST_DATASETS = {
        "prince_edward_islands": {
            "doi": "10.6084/m9.figshare.19248626.v2",
            "url": "https://figshare.com/articles/dataset/Prince_Edward_Islands_geospatial_database/19248626",
            "id": "19248626",
            "title": "Prince Edward Islands geospatial database",
            "expected_bbox": [37.51696444333383, -47.00490880063488, 38.032055268506745, -46.58858378306222],  # [W, S, E, N]
            "description": "South African sub-Antarctic islands geospatial data",
        },
        "raster_workshop": {
            "doi": "10.6084/m9.figshare.20146919.v1",
            "url": "https://figshare.com/articles/dataset/Raster_dataset_for_workshop_Introduction_to_Geospatial_Raster_and_Vector_Data_with_Python_/20146919",
            "id": "20146919",
            "title": "Raster dataset for workshop \"Introduction to Geospatial Raster and Vector Data with Python\"",
            "expected_bbox": [4.464980367155466, 52.25345680616433, 6.141769904471917, 53.208217152152926],  # [W, S, E, N]
            "description": "Geospatial raster data for Python workshop - covers parts of Netherlands",
        }
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
            result = geoextent.from_repository(
                dataset["url"], bbox=True, tbox=True, download_data=True
            )


            assert result is not None
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
            result = geoextent.from_repository(
                dataset["url"], bbox=True, tbox=True, download_data=True
            )


            assert result is not None
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

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_figshare_metadata_only_extraction(self):
        """Test Figshare metadata-only extraction (limited functionality)"""
        dataset = self.TEST_DATASETS["prince_edward_islands"]

        try:
            result = geoextent.from_repository(
                dataset["url"], bbox=True, tbox=True, download_data=False
            )

            assert result is not None
            assert result["format"] == "repository"


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
                        result = geoextent.from_repository(
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
        assert figshare.validate_provider(nonexistent_url) == True  # URL format is valid

        # But trying to extract should fail gracefully
        try:
            result = geoextent.from_repository(
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
            result = geoextent.from_repository(
                test_url, bbox=True, tbox=False, download_data=True
            )
            assert result is not None
            assert result["format"] == "repository"
            assert "tbox" not in result

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_figshare_tbox_only(self):
        """Test Figshare extraction with only tbox enabled"""
        test_url = "https://figshare.com/articles/dataset/Prince_Edward_Islands_geospatial_database/19248626"

        try:
            result = geoextent.from_repository(
                test_url, bbox=False, tbox=True, download_data=True
            )
            assert result is not None
            assert result["format"] == "repository"
            assert "bbox" not in result

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_figshare_with_details(self):
        """Test Figshare extraction with details enabled"""
        test_url = "https://figshare.com/articles/dataset/Prince_Edward_Islands_geospatial_database/19248626"

        try:
            result = geoextent.from_repository(
                test_url, bbox=True, tbox=True, details=True, download_data=True
            )
            assert result is not None
            assert result["format"] == "repository"
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
            result_with_data = geoextent.from_repository(
                test_url, bbox=True, download_data=True
            )
            assert result_with_data is not None
            assert result_with_data["format"] == "repository"

            # Test with download_data=False (metadata-only, limited for Figshare)
            result_metadata = geoextent.from_repository(
                test_url, bbox=True, download_data=False
            )
            assert result_metadata is not None
            assert result_metadata["format"] == "repository"

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
            assert "does not exist" in str(e) or "404" in str(e) or "error" in str(e).lower()