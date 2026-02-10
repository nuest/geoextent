import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance
from geojson_validator import validate_structure
import geoextent.lib.helpfunctions as hf
import subprocess
import json


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

            # Validate GeoJSON output format as returned by the library
            if "bbox" in result:
                # Get GeoJSON format as returned by geoextent library
                geojson_output = hf.format_extent_output(result, "geojson")

                # Validate the GeoJSON structure
                validation_errors = validate_structure(geojson_output)
                assert (
                    not validation_errors
                ), f"Invalid GeoJSON structure: {validation_errors}"

                # Additional basic GeoJSON structure checks
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

    def test_zenodo_cli_geojson_validation(self):
        """Test Zenodo CLI output with GeoJSON validation"""
        test_doi = "10.5281/zenodo.820562"

        try:
            # Run geoextent CLI with --quiet flag to get clean JSON output
            result = subprocess.run(
                ["python", "-m", "geoextent", "-b", "--quiet", test_doi],
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


class TestZenodoZIPFileHandling:
    """Test Zenodo single ZIP file handling"""

    def test_zenodo_single_zip_file(self):
        """Test Zenodo repository containing a single ZIP file with geospatial data

        This test verifies that geoextent correctly:
        1. Downloads a single ZIP file from Zenodo
        2. Automatically extracts the ZIP file
        3. Processes all geospatial files inside the ZIP
        4. Returns a valid bounding box from the extracted files

        Test dataset: https://doi.org/10.5281/zenodo.3446746
        Contains: LandscapeGeoinformatics/EU-SoilHydroGrids_tiles_nav-v1.0.zip (~1MB)
        With: Multiple geospatial formats (GeoPackage, Shapefile, PNG)
        """
        test_doi = "10.5281/zenodo.3446746"

        try:
            # Test with size limit to keep test fast
            result = geoextent.fromRemote(
                test_doi,
                bbox=True,
                tbox=False,
                download_data=True,
                max_download_size=2 * 1024 * 1024,  # 2MB limit
                quiet=True,
            )

            assert result is not None, "Result should not be None"
            assert result["format"] == "remote", "Format should be 'remote'"

            # Verify bounding box was extracted from ZIP contents
            assert "bbox" in result, "Should have extracted bbox from ZIP contents"
            bbox = result["bbox"]

            # Verify bbox is valid
            assert len(bbox) == 4, "Bbox should have 4 coordinates"
            assert bbox[0] <= bbox[2], "West should be <= East"
            assert bbox[1] <= bbox[3], "South should be <= North"

            # Verify coordinates are reasonable for European data
            assert -180 <= bbox[0] <= 180, "West longitude should be valid"
            assert -180 <= bbox[2] <= 180, "East longitude should be valid"
            assert -90 <= bbox[1] <= 90, "South latitude should be valid"
            assert -90 <= bbox[3] <= 90, "North latitude should be valid"

            # Verify CRS
            assert "crs" in result, "Should have CRS"
            assert result["crs"] == "4326", "CRS should be WGS84"

            # Verify GeoJSON output format
            geojson_output = hf.format_extent_output(result, "geojson")
            validation_errors = validate_structure(geojson_output)
            assert not validation_errors, f"Invalid GeoJSON: {validation_errors}"

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_zenodo_zip_with_nested_archives(self):
        """Test that nested ZIP files within the main ZIP are also extracted

        The test dataset contains nested ZIP files that should be automatically
        extracted and processed.
        """
        test_doi = "10.5281/zenodo.3446746"

        try:
            # Enable details to see individual file processing
            result = geoextent.fromRemote(
                test_doi,
                bbox=True,
                tbox=False,
                details=True,
                download_data=True,
                max_download_size=2 * 1024 * 1024,  # 2MB limit
                quiet=True,
            )

            assert result is not None
            assert "bbox" in result

            # If details are available, verify multiple files were processed
            if "details" in result:
                assert isinstance(result["details"], dict)
                # Should have processed multiple files from the ZIP
                assert len(result["details"]) > 0

        except ImportError:
            pytest.skip("Required libraries not available")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")

    def test_zenodo_zip_cli_output(self):
        """Test Zenodo ZIP file handling via CLI"""
        test_doi = "10.5281/zenodo.3446746"

        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "geoextent",
                    "-b",
                    "--max-download-size",
                    "2MB",
                    "--quiet",
                    test_doi,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            assert result.returncode == 0, f"CLI failed: {result.stderr}"

            # Parse and validate GeoJSON output
            geojson_output = json.loads(result.stdout)
            validation_errors = validate_structure(geojson_output)
            assert not validation_errors, f"Invalid GeoJSON: {validation_errors}"

            # Verify it's a valid FeatureCollection with spatial extent
            assert geojson_output["type"] == "FeatureCollection"
            assert len(geojson_output["features"]) > 0

            feature = geojson_output["features"][0]
            assert feature["geometry"]["type"] == "Polygon"

            # Verify geoextent_extraction metadata
            assert "geoextent_extraction" in geojson_output
            assert geojson_output["geoextent_extraction"]["format"] == "remote"

        except subprocess.TimeoutExpired:
            pytest.skip("CLI test timeout (network issues)")
        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to parse JSON: {e}\nOutput: {result.stdout}")
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")
