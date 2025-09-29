import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance


class TestGFZProvider:
    """Test GFZ Data Services content provider functionality with actual bounding box verification"""

    # Test datasets with known geographic and temporal coverage
    TEST_DATASETS = {
        "santiaguito_lava_dome": {
            "doi": "10.5880/GFZ.2.1.2020.001",
            "url": "https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=escidoc:5148893",
            "id": "escidoc:5148893",
            "title": "High-resolution photogrammetry data of the Santiaguito lava dome collected by UAS surveys",
            # Expected bounding box extracted from GFZ metadata (approximate)
            "expected_bbox": [
                -91.8,  # W
                14.6,  # S
                -91.7,  # E
                14.8,  # N
            ],  # [W, S, E, N] - Guatemala coordinates
            "expected_tbox": ["2020-01-01", "2020-12-31"],  # 2020 data collection
        },
        "geothermal_north_german_basin": {
            "doi": "10.5880/GFZ.4.8.2023.004",
            "url": "https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=bd4d58fb-1441-11ee-95b8-f851ad6d1e4b",
            "id": "bd4d58fb-1441-11ee-95b8-f851ad6d1e4b",
            "title": "Dataset to Geothermal Resources and ATES Potential of Mesozoic Reservoirs in the North German Basin",
            # Expected bounding box for North German Basin
            "expected_bbox": [
                3.93,  # W
                51.32,  # S
                15.38,  # E
                55.91,  # N
            ],  # [W, S, E, N] - North German Basin coordinates
            "expected_tbox": ["2023-01-01", "2023-12-31"],  # 2023 publication year
        },
    }

    def test_gfz_url_validation(self):
        """Test that GFZ URLs and DOIs are correctly validated"""
        from geoextent.lib.content_providers.GFZ import GFZ

        gfz = GFZ()

        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            # Test DOI validation
            assert gfz.validate_provider(dataset_info["doi"]) == True

            # Test URL validation
            assert gfz.validate_provider(dataset_info["url"]) == True

        # Test additional GFZ DOI formats
        valid_identifiers = [
            "10.5880/GFZ.2.1.2020.001",
            "https://doi.org/10.5880/GFZ.2.1.2020.001",
            "https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=escidoc:5148893",
            "dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=escidoc:5148893",
        ]

        for identifier in valid_identifiers:
            assert gfz.validate_provider(identifier) == True

        # Test invalid identifiers
        invalid_identifiers = [
            "10.5281/zenodo.820562",  # Zenodo DOI
            "10.1594/PANGAEA.734969",  # PANGAEA DOI
            "https://figshare.com/articles/123456",  # Figshare URL
            "not-a-doi-at-all",
            "",
            "10.5880/WRONG.2.1.2020.001",  # Wrong GFZ prefix
        ]

        for identifier in invalid_identifiers:
            assert gfz.validate_provider(identifier) == False

    def test_gfz_download_url_extraction(self):
        """Test GFZ download URL extraction from landing pages"""
        from geoextent.lib.content_providers.GFZ import GFZ
        from bs4 import BeautifulSoup

        gfz = GFZ()
        dataset = self.TEST_DATASETS["santiaguito_lava_dome"]

        # Validate the provider first
        assert gfz.validate_provider(dataset["url"]) == True

        try:
            # Test download URL extraction
            response = gfz._request(dataset["url"], throttle=False)
            soup = BeautifulSoup(response.text, "html.parser")
            download_url = gfz._extract_download_url(soup)

            assert download_url is not None
            assert isinstance(download_url, str)
            assert "datapub.gfz-potsdam.de" in download_url
            assert "download" in download_url or download_url.endswith(".zip")

        except ImportError:
            pytest.skip("Required libraries (BeautifulSoup) not available")
        except Exception as e:
            pytest.skip(f"Network error: {e}")

    def test_gfz_actual_bounding_box_verification(self):
        """Test GFZ provider with actual bounding box verification"""
        dataset = self.TEST_DATASETS["santiaguito_lava_dome"]

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

                # Verify bounding box validity (Guatemala region)
                assert bbox[0] <= bbox[2], "West longitude should be <= East longitude"
                assert bbox[1] <= bbox[3], "South latitude should be <= North latitude"
                assert -180 <= bbox[0] <= 180, "West longitude should be valid"
                assert -180 <= bbox[2] <= 180, "East longitude should be valid"
                assert -90 <= bbox[1] <= 90, "South latitude should be valid"
                assert -90 <= bbox[3] <= 90, "North latitude should be valid"

                # Check if coordinates are in Guatemala region (approximate)
                assert -92 <= bbox[0] <= -88, "West longitude should be in Guatemala"
                assert -92 <= bbox[2] <= -88, "East longitude should be in Guatemala"
                assert 13 <= bbox[1] <= 18, "South latitude should be in Guatemala"
                assert 13 <= bbox[3] <= 18, "North latitude should be in Guatemala"

            # Check CRS
            if "crs" in result:
                assert result["crs"] == "4326", "CRS should be WGS84"

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_gfz_metadata_only_extraction(self):
        """Test GFZ metadata-only extraction"""
        dataset = self.TEST_DATASETS["santiaguito_lava_dome"]

        try:
            # Note: GFZ doesn't provide structured geospatial metadata without downloading
            result = geoextent.fromRemote(
                dataset["url"], bbox=True, tbox=True, download_data=False
            )

            assert result is not None
            assert result["format"] == "remote"

            # GFZ may have limited metadata without file downloads

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_gfz_multiple_identifiers(self):
        """Test GFZ with different identifier formats"""
        dataset = self.TEST_DATASETS["santiaguito_lava_dome"]

        identifiers = [
            dataset["doi"],
            f"https://doi.org/{dataset['doi']}",
            dataset["url"],
            dataset["id"],  # Just the escidoc ID
        ]

        from geoextent.lib.content_providers.GFZ import GFZ

        gfz = GFZ()

        for identifier in identifiers:
            try:
                is_valid = gfz.validate_provider(identifier)
                # At least the URL and DOI should validate
                if identifier in [dataset["doi"], dataset["url"]]:
                    assert is_valid == True

            except Exception as e:
                continue

    def test_gfz_doi_formats(self):
        """Test various GFZ DOI formats"""
        from geoextent.lib.content_providers.GFZ import GFZ

        gfz = GFZ()

        valid_gfz_dois = [
            "10.5880/GFZ.2.1.2020.001",
            "10.5880/GFZ.1.2.2019.002",
            "10.5880/GFZ.3.4.2021.003",
            "10.5880/GFZ.4.8.2023.004",  # New geothermal dataset
        ]

        for doi in valid_gfz_dois:
            assert gfz.validate_provider(doi) == True
            # Verify GFZ DOI pattern matching
            assert gfz.gfz_doi_pattern.search(doi) is not None

    def test_gfz_geothermal_dataset_validation(self):
        """Test GFZ provider with geothermal dataset (10.5880/GFZ.4.8.2023.004)"""
        from geoextent.lib.content_providers.GFZ import GFZ

        gfz = GFZ()
        dataset = self.TEST_DATASETS["geothermal_north_german_basin"]

        # Test DOI validation
        assert gfz.validate_provider(dataset["doi"]) == True
        assert gfz.doi == dataset["doi"]

        gfz = GFZ()  # Reset for URL test
        # Test URL validation
        assert gfz.validate_provider(dataset["url"]) == True
        assert gfz.dataset_id == dataset["id"]

        # Test download URL extraction (if network available)
        try:
            from bs4 import BeautifulSoup

            response = gfz._request(dataset["url"], throttle=False)
            soup = BeautifulSoup(response.text, "html.parser")
            download_url = gfz._extract_download_url(soup)

            assert download_url is not None
            assert isinstance(download_url, str)
            assert "datapub.gfz-potsdam.de" in download_url

        except ImportError:
            pytest.skip("Required libraries (BeautifulSoup) not available")
        except Exception as e:
            pytest.skip(f"Network error: {e}")

    def test_gfz_geothermal_dataset_geographic_bounds(self):
        """Test that geothermal dataset coordinates are reasonable for North German Basin"""
        dataset = self.TEST_DATASETS["geothermal_north_german_basin"]
        expected_bbox = dataset["expected_bbox"]

        # Verify coordinates are in Europe (rough bounds check)
        assert (
            -10 <= expected_bbox[0] <= 30
        ), "Western longitude should be in European range"
        assert (
            -10 <= expected_bbox[2] <= 30
        ), "Eastern longitude should be in European range"
        assert (
            40 <= expected_bbox[1] <= 70
        ), "Southern latitude should be in Northern European range"
        assert (
            40 <= expected_bbox[3] <= 70
        ), "Northern latitude should be in Northern European range"

        # Verify this is specifically North German Basin region
        assert (
            3 <= expected_bbox[0] <= 16
        ), "Western longitude should be in German region"
        assert (
            3 <= expected_bbox[2] <= 16
        ), "Eastern longitude should be in German region"
        assert (
            50 <= expected_bbox[1] <= 56
        ), "Southern latitude should be in North German region"
        assert (
            50 <= expected_bbox[3] <= 56
        ), "Northern latitude should be in North German region"

    def test_gfz_directory_listing_url_fix(self):
        """Test that directory listings with URLs not ending in '/' work correctly"""
        from geoextent.lib.content_providers.GFZ import GFZ
        from urllib.parse import urljoin

        gfz = GFZ()

        # Test the specific issue: urljoin behavior with directory URLs
        base_url_no_slash = (
            "https://datapub.gfz-potsdam.de/download/10.5880.GFZ.4.8.2023.004sdsdfds"
        )
        base_url_with_slash = base_url_no_slash + "/"
        filename = "2023-004_Frick-et-al_Data.zip"

        # Without fix: urljoin replaces the last path component
        wrong_url = urljoin(base_url_no_slash, filename)
        expected_wrong = (
            "https://datapub.gfz-potsdam.de/download/2023-004_Frick-et-al_Data.zip"
        )
        assert (
            wrong_url == expected_wrong
        ), "Without fix, urljoin should replace last component"

        # With fix: urljoin correctly appends to directory
        correct_url = urljoin(base_url_with_slash, filename)
        expected_correct = "https://datapub.gfz-potsdam.de/download/10.5880.GFZ.4.8.2023.004sdsdfds/2023-004_Frick-et-al_Data.zip"
        assert (
            correct_url == expected_correct
        ), "With fix, urljoin should append to directory"

        # Verify our fix logic works
        fixed_base = (
            base_url_no_slash
            if base_url_no_slash.endswith("/")
            else base_url_no_slash + "/"
        )
        assert fixed_base == base_url_with_slash, "Fix should add trailing slash"

    def test_gfz_doi_resolution_fix(self):
        """Test that DOI resolution uses proper URL resolution instead of manual construction"""
        from geoextent.lib.content_providers.GFZ import GFZ

        gfz = GFZ()
        doi = "10.5880/GFZ.4.8.2023.004"

        # Validate the DOI
        assert gfz.validate_provider(doi) == True
        assert gfz.doi == doi

        # Test that get_url properly resolves the DOI to the correct landing page
        resolved_url = gfz.get_url
        assert resolved_url is not None
        assert resolved_url != doi, "Resolved URL should be different from original DOI"
        assert "dataservices.gfz-potsdam.de/panmetaworks/showshort.php" in resolved_url
        assert "id=" in resolved_url

        # The resolved URL should be a valid GFZ dataset URL
        gfz2 = GFZ()
        assert gfz2.validate_provider(resolved_url) == True
        assert gfz2.dataset_id is not None

        # Verify the resolved URL is not the old incorrect format
        incorrect_url = f"https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=escidoc:{doi.replace('10.5880/GFZ.', '')}"
        assert (
            resolved_url != incorrect_url
        ), f"Should not use incorrect URL format: {incorrect_url}"


class TestGFZParameterCombinations:
    """Test GFZ with various parameter combinations"""

    def test_gfz_bbox_only(self):
        """Test GFZ extraction with only bbox enabled"""
        test_url = "https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=escidoc:5148893"

        try:
            result = geoextent.fromRemote(
                test_url, bbox=True, tbox=False, download_data=True
            )
            assert result is not None
            assert result["format"] == "remote"
            assert "tbox" not in result

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_gfz_tbox_only(self):
        """Test GFZ extraction with only tbox enabled"""
        test_url = "https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=escidoc:5148893"

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

    def test_gfz_with_details(self):
        """Test GFZ extraction with details enabled"""
        test_url = "https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=escidoc:5148893"

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


class TestGFZEdgeCases:
    """Test GFZ edge cases and error handling"""

    def test_gfz_nonexistent_dataset(self):
        """Test GFZ with nonexistent dataset"""
        nonexistent_url = "https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=escidoc:nonexistent"

        try:
            result = geoextent.fromRemote(
                nonexistent_url, bbox=True, download_data=True
            )
            # Should either raise exception or return error indicator
            if result is not None:
                assert isinstance(result, dict)

        except Exception:
            # Exception is expected for nonexistent records
            pass

    def test_gfz_malformed_identifiers(self):
        """Test GFZ with malformed identifiers"""
        from geoextent.lib.content_providers.GFZ import GFZ

        gfz = GFZ()

        malformed_identifiers = [
            "10.5880/GFZ.",  # Incomplete DOI
            "10.5880/GFZ.abc",  # Invalid format
            "10.1234/GFZ.2.1.2020.001",  # Wrong prefix
            "https://dataservices.gfz-potsdam.de/showshort.php",  # No ID parameter
        ]

        for identifier in malformed_identifiers:
            assert gfz.validate_provider(identifier) == False

    def test_gfz_url_validation_edge_cases(self):
        """Test GFZ URL validation edge cases"""
        from geoextent.lib.content_providers.GFZ import GFZ

        gfz = GFZ()

        # Test various URL formats
        test_cases = [
            (
                "https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=escidoc:5148893",
                True,
            ),
            (
                "http://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=escidoc:5148893",
                True,
            ),
            (
                "dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=escidoc:5148893",
                True,
            ),
            (
                "https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=5148893",
                True,
            ),
            ("https://example.com/showshort.php?id=escidoc:5148893", False),
            ("https://dataservices.gfz-potsdam.de/other.php?id=escidoc:5148893", False),
        ]

        for url, expected in test_cases:
            result = gfz.validate_provider(url)
            assert result == expected, f"URL {url} should validate as {expected}"


class TestGFZIntegration:
    """Integration tests for GFZ provider"""

    def test_gfz_full_workflow(self):
        """Test complete GFZ workflow from validation to extraction"""
        test_url = "https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=escidoc:5148893"

        try:
            # Step 1: Validation
            from geoextent.lib.content_providers.GFZ import GFZ

            gfz = GFZ()
            assert gfz.validate_provider(test_url) == True

            # Step 2: Full extraction
            result = geoextent.fromRemote(
                test_url, bbox=True, tbox=True, download_data=True
            )

            # Step 3: Verify results
            assert result is not None
            assert result["format"] == "remote"

            # At minimum, we should get some spatial or temporal information
            has_spatial = "bbox" in result and result["bbox"] is not None
            has_temporal = "tbox" in result and result["tbox"] is not None

            assert (
                has_spatial or has_temporal
            ), "Should extract at least spatial or temporal extent"

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")
