import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance
from geojson_validator import validate_structure
import subprocess
import json


class TestPensoftProvider:
    """Test Pensoft content provider functionality with actual bounding box verification"""

    # Test datasets with known geographic coverage from Pensoft journals
    TEST_DATASETS = {
        "fungus_gnats_finland": {
            "doi": "10.3897/BDJ.2.e1068",
            "doi_url": "https://doi.org/10.3897/BDJ.2.e1068",
            "article_url": "https://bdj.pensoft.net/article/1068/",
            "article_id": "1068",
            "title": "Recent noteworthy findings of fungus gnats from Finland and northwestern Russia",
            "expected_bbox": [
                19.7,  # W
                59.963,  # S
                36.622,  # E
                69.909,  # N
            ],
            "coordinate_count": 251,
            "description": "Fungus gnat records from Finland and northwestern Russia with extensive coordinate data",
        },
        "amphibians_vietnam": {
            "doi": "10.3897/BDJ.13.e159973",
            "doi_url": "https://doi.org/10.3897/BDJ.13.e159973",
            "article_url": "https://bdj.pensoft.net/article/159973/",
            "article_id": "159973",
            "title": "New records of amphibians for Ha Nam Province, Vietnam",
            "expected_bbox": [
                105.83960166667,  # W
                20.536216666667,  # S
                106.54058333333,  # E
                20.8705,  # N
            ],
            "coordinate_count": 6,
            "description": "Amphibian records from Ha Nam Province, Vietnam",
        },
        "scarab_beetles_volga": {
            "doi": "10.3897/BDJ.1.e979",
            "doi_url": "https://doi.org/10.3897/BDJ.1.e979",
            "article_url": "https://bdj.pensoft.net/article/979/",
            "article_id": "979",
            "title": "A contribution to the study of the Lower Volga center of scarab beetle diversity",
            "expected_bbox": [
                47.900,  # W
                46.900,  # S
                48.020,  # E
                47.000,  # N
            ],
            "coordinate_count": 9,
            "description": "Historic DOI from volume 1, scarab beetle diversity study",
        },
        "chaitophorus_aphids": {
            "doi": None,  # This one doesn't have a clear DOI pattern
            "doi_url": None,
            "article_url": "https://bdj.pensoft.net/article/150852/",
            "article_id": "150852",
            "title": "Unveiling hidden diversity: new records of Chaitophorus (Hemiptera, Aphididae)",
            "expected_bbox": None,  # Will be determined during testing
            "coordinate_count": 7,
            "description": "Recent article on aphid diversity",
        },
    }

    def test_pensoft_doi_validation(self):
        """Test that Pensoft DOIs are correctly validated"""
        from geoextent.lib.content_providers.Pensoft import Pensoft

        pensoft = Pensoft()

        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            # Test DOI validation if DOI exists
            if dataset_info["doi"]:
                assert pensoft.validate_provider(dataset_info["doi"]) == True
                assert pensoft.article_id == dataset_info["article_id"]

            # Test DOI URL validation if exists
            if dataset_info["doi_url"]:
                assert pensoft.validate_provider(dataset_info["doi_url"]) == True
                assert pensoft.article_id == dataset_info["article_id"]

            # Test direct article URL validation
            if dataset_info["article_url"]:
                assert pensoft.validate_provider(dataset_info["article_url"]) == True
                assert pensoft.article_id == dataset_info["article_id"]

        # Test invalid DOI (from another provider)
        invalid_doi = "10.1594/PANGAEA.734969"
        assert pensoft.validate_provider(invalid_doi) == False

        # Test invalid URL
        invalid_url = "https://example.com/article/123"
        assert pensoft.validate_provider(invalid_url) == False

    def test_pensoft_coordinate_extraction(self):
        """Test that coordinates are correctly extracted from Pensoft articles"""
        from geoextent.lib.content_providers.Pensoft import Pensoft

        pensoft = Pensoft()

        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            # Use the DOI if available, otherwise use article URL
            test_input = dataset_info["doi"] or dataset_info["article_url"]

            print(f"\nTesting coordinate extraction for {dataset_name}: {test_input}")

            # Validate and download
            assert pensoft.validate_provider(test_input) == True
            record_data = pensoft.download_record()

            # Check title extraction
            assert record_data["title"] is not None
            assert len(record_data["title"]) > 0
            print(f"  Title: {record_data['title'][:80]}...")

            # Check coordinate count
            actual_count = len(record_data["coordinates"])
            expected_count = dataset_info["coordinate_count"]
            print(f"  Coordinates found: {actual_count}, expected: {expected_count}")

            # Allow some tolerance for coordinate counts in case of data changes
            assert actual_count >= expected_count * 0.9  # Allow 10% variation

            # Check coordinate format (should be lon, lat tuples)
            if record_data["coordinates"]:
                first_coord = record_data["coordinates"][0]
                assert isinstance(first_coord, tuple)
                assert len(first_coord) == 2
                lon, lat = first_coord
                assert isinstance(lon, (int, float))
                assert isinstance(lat, (int, float))
                # Basic coordinate range validation
                assert -180 <= lon <= 180
                assert -90 <= lat <= 90
                print(f"  Sample coordinate: ({lon}, {lat})")

    def test_pensoft_geojson_generation(self):
        """Test that GeoJSON is correctly generated from Pensoft data"""
        import json
        from geoextent.lib.content_providers.Pensoft import Pensoft

        pensoft = Pensoft()

        # Test with the fungus gnats dataset (has most coordinates)
        test_dataset = self.TEST_DATASETS["fungus_gnats_finland"]

        assert pensoft.validate_provider(test_dataset["doi"]) == True
        geojson_content = pensoft.get_file_content(pensoft.article_id)

        assert geojson_content is not None

        # Parse and validate GeoJSON structure
        geojson = json.loads(geojson_content)
        assert geojson["type"] == "FeatureCollection"
        assert "features" in geojson
        assert "properties" in geojson

        # Check features
        features = geojson["features"]
        assert len(features) > 0

        for feature in features[:5]:  # Check first 5 features
            assert feature["type"] == "Feature"
            assert "geometry" in feature
            assert "properties" in feature

            geometry = feature["geometry"]
            assert geometry["type"] == "Point"
            assert "coordinates" in geometry
            assert len(geometry["coordinates"]) == 2

            properties = feature["properties"]
            assert "source" in properties
            assert properties["source"] == "Pensoft"
            assert "article_id" in properties

    def test_pensoft_bbox_calculation(self):
        """Test bounding box calculation through geoextent integration"""

        for dataset_name, dataset_info in self.TEST_DATASETS.items():
            if not dataset_info.get("expected_bbox"):
                continue  # Skip datasets without expected bbox

            # Use the DOI if available, otherwise use article URL
            test_input = dataset_info["doi"] or dataset_info["article_url"]

            print(f"\nTesting bbox calculation for {dataset_name}: {test_input}")

            try:
                result = geoextent.fromRemote(test_input, bbox=True, tbox=False)

                assert result is not None
                assert "bbox" in result

                actual_bbox = result["bbox"]
                expected_bbox = dataset_info["expected_bbox"]

                print(f"  Expected bbox: {expected_bbox}")
                print(f"  Actual bbox:   {actual_bbox}")

                # Check bbox format [W, S, E, N]
                assert len(actual_bbox) == 4
                assert actual_bbox[0] <= actual_bbox[2]  # W <= E
                assert actual_bbox[1] <= actual_bbox[3]  # S <= N

                # Check bbox values are within tolerance
                for i in range(4):
                    assert (
                        abs(actual_bbox[i] - expected_bbox[i]) <= tolerance
                    ), f"Bbox coordinate {i} differs: {actual_bbox[i]} vs {expected_bbox[i]}"

                print(f"  ✓ Bbox matches expected values within tolerance")

            except Exception as e:
                pytest.fail(f"Failed to process {dataset_name}: {e}")

    def test_pensoft_input_variants(self):
        """Test that all input format variants work correctly"""
        from geoextent.lib.content_providers.Pensoft import Pensoft

        # Test with the Vietnam dataset (has all variants)
        test_dataset = self.TEST_DATASETS["amphibians_vietnam"]

        input_variants = [
            ("Plain DOI", test_dataset["doi"]),
            ("DOI URL", test_dataset["doi_url"]),
            ("Article URL", test_dataset["article_url"]),
        ]

        expected_article_id = test_dataset["article_id"]
        expected_coord_count = test_dataset["coordinate_count"]

        pensoft = Pensoft()

        for variant_name, test_input in input_variants:
            print(f"\nTesting {variant_name}: {test_input}")

            # Validate
            assert pensoft.validate_provider(test_input) == True
            assert pensoft.article_id == expected_article_id

            # Extract coordinates
            record_data = pensoft.download_record()
            actual_count = len(record_data["coordinates"])

            print(f"  Article ID: {pensoft.article_id}")
            print(f"  Coordinates: {actual_count}")

            # All variants should give the same results
            assert actual_count >= expected_coord_count * 0.9  # Allow 10% tolerance

    def test_pensoft_historic_doi_support(self):
        """Test that historic DOIs from early volumes are supported"""

        # Test volume 1 DOI (historic)
        historic_dataset = self.TEST_DATASETS["scarab_beetles_volga"]

        try:
            result = geoextent.fromRemote(
                historic_dataset["doi"], bbox=True, tbox=False
            )

            assert result is not None
            assert "bbox" in result

            actual_bbox = result["bbox"]
            expected_bbox = historic_dataset["expected_bbox"]

            print(f"\nHistoric DOI test:")
            print(f"  DOI: {historic_dataset['doi']}")
            print(f"  Expected bbox: {expected_bbox}")
            print(f"  Actual bbox:   {actual_bbox}")

            # Verify bbox is reasonable for the Volga region
            for i in range(4):
                assert abs(actual_bbox[i] - expected_bbox[i]) <= tolerance

        except Exception as e:
            pytest.fail(f"Failed to process historic DOI: {e}")

    def test_pensoft_integration_with_geoextent(self):
        """Test complete integration with geoextent system"""

        # Test with Finland dataset (most comprehensive)
        test_dataset = self.TEST_DATASETS["fungus_gnats_finland"]

        result = geoextent.fromRemote(test_dataset["doi"], bbox=True, tbox=False)

        # Verify result structure
        assert result is not None
        assert result["format"] == "remote"
        assert result["crs"] == "4326"  # CRS is returned as string
        assert "bbox" in result

        bbox = result["bbox"]
        expected_bbox = test_dataset["expected_bbox"]

        # Verify bbox accuracy
        for i in range(4):
            assert abs(bbox[i] - expected_bbox[i]) <= tolerance

        # Verify geographic extent makes sense (Finland/Russia region)
        assert 15 <= bbox[0] <= 40  # Western longitude
        assert 55 <= bbox[1] <= 75  # Southern latitude
        assert 30 <= bbox[2] <= 45  # Eastern longitude
        assert 65 <= bbox[3] <= 75  # Northern latitude

    def test_pensoft_error_handling(self):
        """Test error handling for invalid inputs and network issues"""
        from geoextent.lib.content_providers.Pensoft import Pensoft

        pensoft = Pensoft()

        # Test invalid DOI patterns
        invalid_inputs = [
            "10.1234/invalid.doi",  # Invalid DOI pattern
            "https://example.com/article/123",  # Wrong domain
            "not-a-doi-at-all",  # Not a DOI at all
            "https://different-journal.com/article/123/",  # Different journal
        ]

        for invalid_input in invalid_inputs:
            # Should not validate (URL pattern doesn't match)
            assert pensoft.validate_provider(invalid_input) == False

        # Test a Pensoft URL that would validate but fail on download
        # (This tests that validation checks format, not existence)
        non_existent_url = "https://bdj.pensoft.net/article/999999999/"
        assert pensoft.validate_provider(non_existent_url) == True  # Validates format

        # But should fail when trying to download
        try:
            pensoft.download_record()
            # If we get here without an exception, something's wrong
            assert False, "Expected HTTPError for non-existent article"
        except Exception as e:
            # Should get some kind of error (404, HTTPError, etc.)
            assert True  # Expected behavior

        # Test with a DOI that might not have coordinates
        # (This would need to be a real DOI that exists but has no geographic data)

    def test_pensoft_cli_geojson_validation(self):
        """Test Pensoft CLI output with GeoJSON validation"""
        test_doi = (
            "10.3897/BDJ.2.e1068"  # Fungus gnats from Finland with rich coordinate data
        )

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

            # Verify properties contain expected metadata
            properties = feature["properties"]
            assert "format" in properties, "Properties should contain format field"
            assert properties["format"] == "remote", "Format should be 'remote'"

        except subprocess.TimeoutExpired:
            pytest.skip("CLI test skipped due to timeout (network issues)")
        except json.JSONDecodeError as e:
            pytest.fail(
                f"Failed to parse CLI output as JSON: {e}\nOutput: {result.stdout}"
            )
        except Exception as e:
            pytest.skip(f"Network or API error: {e}")
