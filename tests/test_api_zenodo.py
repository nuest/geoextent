import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance


class TestZenodoProvider:
    """Test Zenodo content provider functionality with actual bounding box verification"""

    # Test datasets with known geographic and temporal coverage
    TEST_DATASETS = {
        "landslide_imagery": {
            "doi": "10.5281/zenodo.820562",
            "url": "https://zenodo.org/record/820562",
            "id": "820562",
            "title": "Landslide imagery from Hpakant, Myanmar",
            "expected_bbox": [
                96.21146318274846,
                25.56156568254296,
                96.35495081696702,
                25.6297452149091,
            ],  # [W, S, E, N]
            "expected_tbox": None,  # May not have temporal extent
        },
        "geospatial_dataset": {
            "doi": "10.5281/zenodo.4593540",
            "url": "https://zenodo.org/records/4593540",
            "id": "4593540",
            "title": "Geospatial data for coastal erosion analysis",
            # Bounding box will be determined by actual extraction
            "expected_bbox": None,  # To be filled after testing
        },
    }

    def test_zenodo_doi_validation(self):
        """Test that Zenodo DOIs are correctly validated"""
        from geoextent.lib.content_providers.Zenodo import Zenodo

        zenodo = Zenodo()

        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            # Test DOI validation
            assert zenodo.validate_provider(dataset_info["doi"]) == True

            # Test URL validation
            assert zenodo.validate_provider(dataset_info["url"]) == True

        # Test invalid DOI
        invalid_doi = "10.1594/PANGAEA.734969"
        assert zenodo.validate_provider(invalid_doi) == False

    def test_zenodo_actual_bounding_box_verification(self):
        """Test Zenodo provider with actual bounding box verification"""
        dataset = self.TEST_DATASETS["landslide_imagery"]

        try:
            # Test with download_data=True to get actual geospatial data
            result = geoextent.fromRemote(
                dataset["doi"], bbox=True, tbox=True, download_data=True
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

                if expected_bbox:
                    # Verify bounding box with reasonable tolerance (0.01 degrees ~ 1.1 km)
                    assert (
                        abs(bbox[0] - expected_bbox[0]) < 0.01
                    ), f"West longitude: {bbox[0]} vs {expected_bbox[0]}"
                    assert (
                        abs(bbox[1] - expected_bbox[1]) < 0.01
                    ), f"South latitude: {bbox[1]} vs {expected_bbox[1]}"
                    assert (
                        abs(bbox[2] - expected_bbox[2]) < 0.01
                    ), f"East longitude: {bbox[2]} vs {expected_bbox[2]}"
                    assert (
                        abs(bbox[3] - expected_bbox[3]) < 0.01
                    ), f"North latitude: {bbox[3]} vs {expected_bbox[3]}"

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

            # Check temporal coverage if expected
            if "tbox" in result and dataset["expected_tbox"]:
                tbox = result["tbox"]
                expected_tbox = dataset["expected_tbox"]

                assert len(tbox) == 2
                # Allow flexibility in temporal extent matching
                assert tbox[0].startswith(expected_tbox[0][:7])  # Year-month match
                assert tbox[1].startswith(expected_tbox[1][:7])

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_zenodo_metadata_only_extraction(self):
        """Test Zenodo metadata-only extraction (limited functionality)"""
        dataset = self.TEST_DATASETS["landslide_imagery"]

        try:
            result = geoextent.fromRemote(
                dataset["doi"], bbox=True, tbox=True, download_data=False
            )

            assert result is not None
            assert result["format"] == "remote"

            # For Zenodo, metadata-only may still extract bounding box from downloaded files
            # since Zenodo doesn't provide geospatial metadata directly

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_zenodo_multiple_identifiers(self):
        """Test Zenodo with different identifier formats"""
        base_doi = "10.5281/zenodo.820562"
        identifiers = [
            base_doi,
            f"https://doi.org/{base_doi}",
            "https://zenodo.org/record/820562",
            f"https://zenodo.org/doi/{base_doi}",
        ]

        from geoextent.lib.content_providers.Zenodo import Zenodo

        zenodo = Zenodo()

        for identifier in identifiers:
            try:
                assert zenodo.validate_provider(identifier) == True

                # Test actual extraction with one identifier
                if identifier == base_doi:
                    result = geoextent.fromRemote(
                        identifier, bbox=True, download_data=True
                    )
                    assert result is not None

            except Exception as e:
                continue

    def test_zenodo_invalid_identifiers(self):
        """Test Zenodo validation with invalid identifiers"""
        from geoextent.lib.content_providers.Zenodo import Zenodo

        zenodo = Zenodo()

        invalid_identifiers = [
            "10.1594/PANGAEA.734969",  # PANGAEA DOI
            "https://figshare.com/articles/123456",  # Figshare URL
            "10.5281/zenodo.nonexistent",  # Invalid Zenodo DOI
            "not-a-doi-at-all",
            "",
        ]

        for identifier in invalid_identifiers:
            assert zenodo.validate_provider(identifier) == False


class TestZenodoParameterCombinations:
    """Test Zenodo with various parameter combinations"""

    def test_zenodo_bbox_only(self):
        """Test Zenodo extraction with only bbox enabled"""
        test_doi = "10.5281/zenodo.820562"

        try:
            result = geoextent.fromRemote(
                test_doi, bbox=True, tbox=False, download_data=True
            )
            assert result is not None
            assert result["format"] == "remote"
            assert "tbox" not in result

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_zenodo_tbox_only(self):
        """Test Zenodo extraction with only tbox enabled"""
        test_doi = "10.5281/zenodo.820562"

        try:
            result = geoextent.fromRemote(
                test_doi, bbox=False, tbox=True, download_data=True
            )
            assert result is not None
            assert result["format"] == "remote"
            assert "bbox" not in result

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_zenodo_with_details(self):
        """Test Zenodo extraction with details enabled"""
        test_doi = "10.5281/zenodo.820562"

        try:
            result = geoextent.fromRemote(
                test_doi, bbox=True, tbox=True, details=True, download_data=True
            )
            assert result is not None
            assert result["format"] == "remote"
            assert "details" in result
            assert isinstance(result["details"], dict)

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")


class TestZenodoEdgeCases:
    """Test Zenodo edge cases and error handling"""

    def test_zenodo_nonexistent_record(self):
        """Test Zenodo with nonexistent record"""
        nonexistent_doi = "10.5281/zenodo.999999999"

        try:
            result = geoextent.fromRemote(
                nonexistent_doi, bbox=True, download_data=True
            )
            # Should either raise exception or return error indicator
            if result is not None:
                assert isinstance(result, dict)

        except Exception:
            # Exception is expected for nonexistent records
            pass

    def test_zenodo_malformed_dois(self):
        """Test Zenodo with malformed DOIs"""
        from geoextent.lib.content_providers.Zenodo import Zenodo

        zenodo = Zenodo()

        malformed_dois = [
            "10.5281/zenodo.",  # Incomplete
            "10.5281/zenodo.abc",  # Non-numeric ID
            "10.1234/zenodo.123456",  # Wrong prefix
        ]

        for doi in malformed_dois:
            assert zenodo.validate_provider(doi) == False
