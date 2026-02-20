import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance
from geojson_validator import validate_structure
import geoextent.lib.helpfunctions as hf
import subprocess
import json
from conftest import NETWORK_SKIP_EXCEPTIONS


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

    def test_figshare_institutional_portal_url_validation(self):
        """Test that Figshare institutional portal URLs are correctly validated"""
        from geoextent.lib.content_providers.Figshare import Figshare

        figshare = Figshare()

        # Institutional portal URLs (*.figshare.com)
        portal_urls = [
            (
                "https://springernature.figshare.com/articles/dataset/test/8319737",
                "8319737",
            ),
            ("https://monash.figshare.com/articles/dataset/test/12345678", "12345678"),
            ("https://rmit.figshare.com/articles/dataset/test/99999999/2", "99999999"),
        ]

        for url, expected_id in portal_urls:
            assert figshare.validate_provider(url) == True, f"Should validate: {url}"
            assert figshare.record_id == expected_id

        # Invalid institutional portal URLs (no numeric ID)
        assert (
            figshare.validate_provider("https://springernature.figshare.com/articles/")
            == False
        )

    @pytest.mark.large_download
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

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    @pytest.mark.large_download
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

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_figshare_metadata_only_extraction(self):
        """Test Figshare metadata-only extraction returns temporal extent from published_date"""
        dataset = self.TEST_DATASETS["prince_edward_islands"]

        try:
            result = geoextent.fromRemote(
                dataset["url"], bbox=True, tbox=True, download_data=False
            )

            assert result is not None
            assert result["format"] == "remote"

            # Figshare metadata-only should yield temporal extent from published_date
            # but typically no spatial extent (API lacks geolocation for most items)
            if "tbox" in result:
                tbox = result["tbox"]
                assert len(tbox) == 2

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

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
            is_valid = figshare.validate_provider(url)
            assert is_valid, f"URL should be valid: {url}"
            assert figshare.record_id == "19248626"

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

    @pytest.mark.large_download
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

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    @pytest.mark.large_download
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

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    @pytest.mark.large_download
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

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_figshare_download_data_parameter(self):
        """Test Figshare with download_data=False returns metadata-extracted tbox"""
        test_url = "https://figshare.com/articles/dataset/Prince_Edward_Islands_geospatial_database/19248626"

        try:
            # Test with download_data=False (metadata-only)
            result_metadata = geoextent.fromRemote(
                test_url, bbox=True, tbox=True, download_data=False
            )
            assert result_metadata is not None
            assert result_metadata["format"] == "remote"

            # Metadata-only should yield temporal extent from published_date
            # but typically no bbox (Figshare API lacks geolocation)
            if "tbox" in result_metadata:
                tbox = result_metadata["tbox"]
                assert len(tbox) == 2

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")


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

    def test_figshare_supports_metadata_extraction(self):
        """Test that Figshare provider reports metadata extraction support"""
        from geoextent.lib.content_providers.Figshare import Figshare

        figshare = Figshare()
        assert figshare.supports_metadata_extraction is True

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

    @pytest.mark.large_download
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
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")


class TestFigshareExtendedDatasets:
    """Extended Figshare test suite with smaller datasets (33KB-23MB).

    These tests use download_data=True to verify full geospatial extraction
    from a variety of file formats hosted on Figshare. Expected bounding boxes
    are based on actual extraction results and use 1-degree tolerance to account
    for minor GDAL version differences.
    """

    # Expected bboxes: [minlat, minlon, maxlat, maxlon] (EPSG:4326 native axis order)
    TOLERANCE = 1.0  # degrees

    def _assert_bbox_near(self, bbox, expected, label=""):
        """Assert bbox coordinates are within tolerance of expected values."""
        assert len(bbox) == 4
        assert bbox[0] <= bbox[2], f"{label}: minlat > maxlat"
        assert bbox[1] <= bbox[3], f"{label}: minlon > maxlon"
        for i, (actual, exp) in enumerate(zip(bbox, expected)):
            assert (
                abs(actual - exp) < self.TOLERANCE
            ), f"{label}: bbox[{i}] = {actual}, expected ~{exp} (tolerance {self.TOLERANCE})"

    def test_figshare_country_centroids_bbox(self):
        """Country Centroids CSV (33KB) - near-global coverage"""
        url = "https://figshare.com/articles/dataset/Country_centroids/5902369"
        try:
            result = geoextent.fromRemote(url, bbox=True, tbox=True, download_data=True)
            assert result is not None
            assert "bbox" in result
            # Expected: [-56.0, -176.2, 78.0, 178.0]
            self._assert_bbox_near(
                result["bbox"], [-56.0, -176.2, 78.0, 178.0], "Country Centroids"
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_figshare_whale_observations_bbox(self):
        """Whale Observations South Africa CSV (0.33MB) - Indian Ocean / South Africa"""
        url = "https://figshare.com/articles/dataset/Whale_observations_South_Africa/12630380"
        try:
            result = geoextent.fromRemote(url, bbox=True, tbox=True, download_data=True)
            assert result is not None
            assert "bbox" in result
            # Expected: [-38.34, -0.16, -10.13, 73.09]
            self._assert_bbox_near(
                result["bbox"], [-38.34, -0.16, -10.13, 73.09], "Whale Observations"
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_figshare_eland_observations_bbox(self):
        """Eland Observations CSV+KMZ+XLS (0.35MB) - Southern/Central Africa"""
        url = "https://figshare.com/articles/dataset/Observations_of_eland/4668736"
        try:
            result = geoextent.fromRemote(url, bbox=True, tbox=True, download_data=True)
            assert result is not None
            assert "bbox" in result
            # Expected: [-31.87, 0.0, 16.0, 24.80]
            self._assert_bbox_near(
                result["bbox"], [-31.87, 0.0, 16.0, 24.80], "Eland Observations"
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_figshare_mont_avic_land_cover_bbox(self):
        """Mont Avic Land Cover GeoTIFF x7 (0.57MB) - Aosta Valley, Italy"""
        url = "https://figshare.com/articles/dataset/Mont_Avic_land_cover/16718737"
        try:
            result = geoextent.fromRemote(url, bbox=True, tbox=True, download_data=True)
            assert result is not None
            assert "bbox" in result
            # Expected: [45.64, 7.54, 45.72, 7.67]
            self._assert_bbox_near(
                result["bbox"], [45.64, 7.54, 45.72, 7.67], "Mont Avic"
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_figshare_seama_montane_bbox(self):
        """SEAMA Montane GeoPackage+KML (1.09MB) - Mozambique/Malawi"""
        url = "https://figshare.com/articles/dataset/SEAMA_montane/24586941"
        try:
            result = geoextent.fromRemote(url, bbox=True, tbox=True, download_data=True)
            assert result is not None
            assert "bbox" in result
            # Expected: [-17.59, 34.86, -14.28, 38.99]
            self._assert_bbox_near(
                result["bbox"], [-17.59, 34.86, -14.28, 38.99], "SEAMA Montane"
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_figshare_london_boroughs_bbox(self):
        """London Boroughs GeoJSON (1.28MB) - Greater London"""
        url = "https://figshare.com/articles/dataset/London_boroughs/11373984"
        try:
            result = geoextent.fromRemote(url, bbox=True, tbox=True, download_data=True)
            assert result is not None
            assert "bbox" in result
            # Expected: [51.29, -0.51, 51.69, 0.33]
            self._assert_bbox_near(
                result["bbox"], [51.29, -0.51, 51.69, 0.33], "London Boroughs"
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_figshare_peru_aridity_bbox(self):
        """Peru Aridity Map Shapefile ZIP (1.54MB) - Peru"""
        url = "https://figshare.com/articles/dataset/Peru_aridity_map/13031021"
        try:
            result = geoextent.fromRemote(url, bbox=True, tbox=True, download_data=True)
            assert result is not None
            assert "bbox" in result
            # Expected: [-18.35, -81.33, -0.04, -68.65]
            self._assert_bbox_near(
                result["bbox"], [-18.35, -81.33, -0.04, -68.65], "Peru Aridity"
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_figshare_ontario_maps_bbox(self):
        """Ontario Maps GeoJSON x6 (4.81MB) - Ontario, Canada"""
        url = "https://figshare.com/articles/dataset/Ontario_maps/10312097"
        try:
            result = geoextent.fromRemote(url, bbox=True, tbox=True, download_data=True)
            assert result is not None
            assert "bbox" in result
            # Expected: [41.38, -95.19, 56.94, -74.31]
            self._assert_bbox_near(
                result["bbox"], [41.38, -95.19, 56.94, -74.31], "Ontario Maps"
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_figshare_geotiff_envisat_bbox(self):
        """Test GeoTIFF/ENVISAT (5.97MB) - raster"""
        url = "https://figshare.com/articles/dataset/Test_GeoTIFF_ENVISAT/5758794"
        try:
            result = geoextent.fromRemote(url, bbox=True, tbox=True, download_data=True)
            assert result is not None
            assert "bbox" in result
            # Expected: [11.36, -117.64, 33.94, 46.25]
            self._assert_bbox_near(
                result["bbox"], [11.36, -117.64, 33.94, 46.25], "GeoTIFF ENVISAT"
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_figshare_australian_hospitals_bbox(self):
        """Australian Hospitals CSV (197KB) - Australia (institutional portal)"""
        url = "https://springernature.figshare.com/articles/dataset/Australian_hospitals/8319737"
        try:
            result = geoextent.fromRemote(url, bbox=True, tbox=True, download_data=True)
            assert result is not None
            assert "bbox" in result
            # Expected: [-43.31, 113.66, -10.59, 159.07]
            self._assert_bbox_near(
                result["bbox"],
                [-43.31, 113.66, -10.59, 159.07],
                "Australian Hospitals",
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_figshare_ices_helcom_shapefiles_bbox(self):
        """ICES HELCOM fishing effort shapefiles (23MB) - Baltic Sea (institutional portal)"""
        url = "https://ices-library.figshare.com/articles/dataset/HELCOM_request_2022_for_spatial_data_layers_on_effort_fishing_intensity_and_fishing_footprint_for_the_years_2016-2021/20310255"
        try:
            result = geoextent.fromRemote(url, bbox=True, tbox=True, download_data=True)
            assert result is not None
            assert "bbox" in result
            # Expected: [53.9, 9.4, 65.8, 27.9] — Baltic Sea region
            self._assert_bbox_near(
                result["bbox"], [53.9, 9.4, 65.8, 27.9], "ICES HELCOM"
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")


class TestFigshareInstitutionalMetadata:
    """Tests for institutional portals with geospatial metadata in custom_fields.

    USDA Ag Data Commons stores GeoJSON FeatureCollections in a 'Geographic Coverage'
    custom field, enabling metadata-only spatial extraction without data download.
    """

    def test_usda_metadata_only_has_bbox(self):
        """USDA Ag Data Commons: metadata-only yields bbox from GeoJSON Point coverage."""
        # Tall Fescue dataset - Point at [-76.854, 39.018] in Geographic Coverage
        url = "https://api.figshare.com/v2/articles/30753383"
        try:
            result = geoextent.fromRemote(
                url, bbox=True, tbox=True, download_data=False
            )
            assert result is not None
            assert "bbox" in result
            bbox = result["bbox"]
            assert len(bbox) == 4
            # Degenerate point bbox near Beltsville, Maryland
            # Expected: [39.02, -76.85, 39.02, -76.85]
            assert bbox[0] == pytest.approx(39.02, abs=0.1), f"lat: {bbox[0]}"
            assert bbox[1] == pytest.approx(-76.85, abs=0.1), f"lon: {bbox[1]}"
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_usda_metadata_only_has_temporal(self):
        """USDA Ag Data Commons: metadata-only yields tbox from custom fields."""
        # Tall Fescue dataset - Temporal Extent Start Date: 2022-03-31, End Date: 2024-12-05
        url = "https://api.figshare.com/v2/articles/30753383"
        try:
            result = geoextent.fromRemote(
                url, bbox=False, tbox=True, download_data=False
            )
            assert result is not None
            assert "tbox" in result
            tbox = result["tbox"]
            assert len(tbox) == 2
            # Should use custom field dates, not published_date
            assert tbox[0] == "2022-03-31"
            assert tbox[1] == "2024-12-05"
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_usda_polygon_coverage_bbox(self):
        """USDA Ag Data Commons: Polygon coverage yields CONUS bounding box."""
        # US National Dairy Producer Survey - US-spanning Polygon
        url = "https://api.figshare.com/v2/articles/31079356"
        try:
            result = geoextent.fromRemote(
                url, bbox=True, tbox=True, download_data=False
            )
            assert result is not None
            assert "bbox" in result
            bbox = result["bbox"]
            assert len(bbox) == 4
            assert bbox[0] <= bbox[2]
            assert bbox[1] <= bbox[3]
            # Expected: ~[24.7, -126.0, 49.5, -67.1] — CONUS
            assert bbox[0] == pytest.approx(25.0, abs=5.0), f"S lat: {bbox[0]}"
            assert bbox[1] == pytest.approx(-125.0, abs=5.0), f"W lon: {bbox[1]}"
            assert bbox[2] == pytest.approx(50.0, abs=5.0), f"N lat: {bbox[2]}"
            assert bbox[3] == pytest.approx(-67.0, abs=5.0), f"E lon: {bbox[3]}"
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")


class TestFigshareMetadataVsDownload:
    """Comparison tests contrasting metadata-only vs download-based results."""

    def test_metadata_only_no_bbox_download_has_bbox(self):
        """Country Centroids: metadata-only has no bbox, download has bbox from CSV."""
        url = "https://figshare.com/articles/dataset/Country_centroids/5902369"
        try:
            result_meta = geoextent.fromRemote(
                url, bbox=True, tbox=True, download_data=False
            )
            result_data = geoextent.fromRemote(
                url, bbox=True, tbox=True, download_data=True
            )

            # Metadata: no spatial extent (Figshare API lacks geolocation)
            assert result_meta is not None
            assert "bbox" not in result_meta or result_meta.get("bbox") is None

            # Download: has spatial extent from data
            assert result_data is not None
            assert "bbox" in result_data and result_data["bbox"] is not None

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_metadata_temporal_vs_download_temporal(self):
        """Whale Observations: metadata tbox = published_date, download tbox from CSV dates."""
        url = "https://figshare.com/articles/dataset/Whale_observations_South_Africa/12630380"
        try:
            result_meta = geoextent.fromRemote(
                url, bbox=False, tbox=True, download_data=False
            )
            result_data = geoextent.fromRemote(
                url, bbox=False, tbox=True, download_data=True
            )

            # Both should have temporal extent
            assert result_meta is not None
            assert "tbox" in result_meta  # From published_date
            assert result_data is not None
            assert "tbox" in result_data  # From file content
            # They will likely differ (published_date vs observation dates)

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_metadata_first_fallback_to_download(self):
        """Country Centroids: metadata_first tries metadata (no bbox), falls back to download."""
        url = "https://figshare.com/articles/dataset/Country_centroids/5902369"
        try:
            result = geoextent.fromRemote(
                url, bbox=True, tbox=True, metadata_first=True
            )
            assert result is not None
            assert "bbox" in result

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_download_bbox_vs_convex_hull(self):
        """Mont Avic (7 GeoTIFFs): compare bbox vs convex hull."""
        url = "https://figshare.com/articles/dataset/Mont_Avic_land_cover/16718737"
        try:
            result_bbox = geoextent.fromRemote(url, bbox=True, download_data=True)
            result_hull = geoextent.fromRemote(
                url, bbox=True, convex_hull=True, download_data=True
            )
            assert result_bbox is not None
            assert "bbox" in result_bbox
            assert result_hull is not None
            assert "bbox" in result_hull
            # Both should cover the same region

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")
