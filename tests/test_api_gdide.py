import json
import os
import pytest
import geoextent.lib.extent as geoextent
from conftest import NETWORK_SKIP_EXCEPTIONS

# Test datasets with known geographic and temporal coverage
# Reference data retrieved from GDI-DE CSW API (gdk.gdi-de.org)
TEST_DATASETS = {
    "heavy_rain_hazards": {
        "uuid": "75987CE0-AA66-4445-AC44-068B98390E89",
        "landing_url": "https://www.geoportal.de/Metadata/75987CE0-AA66-4445-AC44-068B98390E89",
        "title": "Starkregengefahren",
        # Reference bbox [S, W, N, E] (public API format)
        # Internal bbox from CSW: [6.098, 47.237, 15.579, 55.054]
        "expected_bbox": [47.237, 6.098, 55.054, 15.579],
        "expected_tbox": None,  # No temporal extent
        "bbox_tolerance": 1.0,
    },
    "forest_canopy_loss": {
        "uuid": "cdb2c209-7e08-4f4c-b500-69de926e3023",
        "landing_url": "https://www.geoportal.de/Metadata/cdb2c209-7e08-4f4c-b500-69de926e3023",
        "title": "Forest Canopy Cover Loss",
        # Reference bbox [S, W, N, E] (public API format)
        # Internal bbox from CSW: [5.23, 47.06, 15.69, 55.08]
        "expected_bbox": [47.06, 5.23, 55.08, 15.69],
        "expected_tbox_start_year": "2017",
        "expected_tbox_end_year": "2024",
        "bbox_tolerance": 1.0,
    },
    "severe_weather_reports": {
        "uuid": "54eb433d-742f-47c9-bb29-9c16796e9937",
        "landing_url": "https://www.geoportal.de/Metadata/54eb433d-742f-47c9-bb29-9c16796e9937",
        "title": "Nutzermeldungen",
        # Reference bbox [S, W, N, E] (public API format)
        # Internal bbox from CSW: [5.9, 47.3, 15.0, 54.9]
        "expected_bbox": [47.3, 5.9, 54.9, 15.0],
        "expected_tbox": None,  # No temporal extent in metadata
        "bbox_tolerance": 1.0,
    },
}


class TestGDIDEValidation:
    """Fast validation tests (no network)."""

    def test_gdide_url_validation(self):
        """Test that GDI-DE geoportal.de URLs are correctly validated"""
        from geoextent.lib.content_providers.GDIDE import GDIDE

        dataset = TEST_DATASETS["heavy_rain_hazards"]

        provider = GDIDE()
        assert provider.validate_provider(dataset["landing_url"]) is True
        assert provider.record_uuid == dataset["uuid"]

    def test_gdide_csw_url_validation(self):
        """Test that GDI-DE CSW endpoint URLs are validated"""
        from geoextent.lib.content_providers.GDIDE import GDIDE

        uuid = "75987CE0-AA66-4445-AC44-068B98390E89"
        csw_url = f"https://gdk.gdi-de.org/gdi-de/srv/eng/csw?service=CSW&request=GetRecordById&Id={uuid}"

        provider = GDIDE()
        assert provider.validate_provider(csw_url) is True
        assert provider.record_uuid == uuid

    def test_gdide_validation_invalid_identifiers(self):
        """Test that non-GDI-DE identifiers are rejected"""
        from geoextent.lib.content_providers.GDIDE import GDIDE

        invalid_identifiers = [
            "10.5281/zenodo.820562",  # Zenodo DOI
            "10.48437/7ca5ef-2e1287",  # BAW DOI
            "not-a-valid-identifier",
            "",
            "https://example.com/dataset/123",
            "https://figshare.com/articles/123456",
            "https://nokis.mdi-de-dienste.org/trefferanzeige?docuuid=00100e9d-7838-4563-9dd7-2570b0d932cb",
            "https://datenrepository.baw.de/trefferanzeige?docuuid=40936F66-3DD8-43D0-99AE-7CA5EF2E1287",
        ]

        for identifier in invalid_identifiers:
            provider = GDIDE()
            assert (
                provider.validate_provider(identifier) is False
            ), f"Should not validate: {identifier}"

    def test_gdide_provider_instantiation(self):
        """Test that GDI-DE provider is available and properly configured"""
        from geoextent.lib.content_providers.GDIDE import GDIDE

        provider = GDIDE()
        assert provider is not None
        assert provider.name == "GDI-DE"
        assert hasattr(provider, "validate_provider")
        assert hasattr(provider, "download")
        assert provider.supports_metadata_extraction is True

        info = GDIDE.provider_info()
        assert info["name"] == "GDI-DE"
        assert "geoportal.de" in info["website"]
        assert len(info["supported_identifiers"]) >= 2
        assert len(info["examples"]) >= 2

    def test_gdide_url_parsing_variants(self):
        """Test various URL format variants are parsed correctly"""
        from geoextent.lib.content_providers.GDIDE import GDIDE

        uuid = "75987CE0-AA66-4445-AC44-068B98390E89"
        urls = [
            f"https://www.geoportal.de/Metadata/{uuid}",
            f"http://www.geoportal.de/Metadata/{uuid}",
            f"https://geoportal.de/Metadata/{uuid}",
        ]

        for url in urls:
            provider = GDIDE()
            assert provider.validate_provider(url) is True, f"Failed for URL: {url}"
            assert provider.record_uuid == uuid


class TestGDIDEProvider:
    """Network tests for GDI-DE metadata extraction."""

    def test_gdide_metadata_only_extraction(self):
        """Provider sample test: heavy rain hazards dataset, bbox + no tbox"""
        dataset = TEST_DATASETS["heavy_rain_hazards"]

        try:
            result = geoextent.fromRemote(
                dataset["landing_url"],
                bbox=True,
                tbox=True,
                download_data=False,
            )

            assert result is not None
            assert result["format"] == "remote"

            # Check geographic coverage
            if "bbox" in result and result["bbox"] is not None:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]

                assert len(bbox) == 4
                assert abs(bbox[0] - expected_bbox[0]) < dataset["bbox_tolerance"]
                assert abs(bbox[1] - expected_bbox[1]) < dataset["bbox_tolerance"]
                assert abs(bbox[2] - expected_bbox[2]) < dataset["bbox_tolerance"]
                assert abs(bbox[3] - expected_bbox[3]) < dataset["bbox_tolerance"]

            # This dataset has no temporal extent
            # tbox may or may not be present

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_gdide_dataset_with_temporal(self):
        """Test forest canopy loss dataset: bbox + tbox range check"""
        dataset = TEST_DATASETS["forest_canopy_loss"]

        try:
            result = geoextent.fromRemote(
                dataset["uuid"], bbox=True, tbox=True, download_data=False
            )

            assert result is not None
            assert result["format"] == "remote"

            # Check geographic coverage
            if "bbox" in result and result["bbox"] is not None:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]

                assert len(bbox) == 4
                assert abs(bbox[0] - expected_bbox[0]) < dataset["bbox_tolerance"]
                assert abs(bbox[1] - expected_bbox[1]) < dataset["bbox_tolerance"]
                assert abs(bbox[2] - expected_bbox[2]) < dataset["bbox_tolerance"]
                assert abs(bbox[3] - expected_bbox[3]) < dataset["bbox_tolerance"]

            # Check temporal coverage
            if "tbox" in result and result["tbox"] is not None:
                tbox = result["tbox"]
                assert dataset["expected_tbox_start_year"] in tbox[0]
                assert dataset["expected_tbox_end_year"] in tbox[1]

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_gdide_severe_weather_reports(self):
        """Test DWD severe weather reports: bbox check, no temporal extent"""
        dataset = TEST_DATASETS["severe_weather_reports"]

        try:
            result = geoextent.fromRemote(
                dataset["uuid"], bbox=True, tbox=True, download_data=False
            )

            assert result is not None
            assert result["format"] == "remote"

            # Check geographic coverage
            if "bbox" in result and result["bbox"] is not None:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]

                assert len(bbox) == 4
                assert abs(bbox[0] - expected_bbox[0]) < dataset["bbox_tolerance"]
                assert abs(bbox[1] - expected_bbox[1]) < dataset["bbox_tolerance"]
                assert abs(bbox[2] - expected_bbox[2]) < dataset["bbox_tolerance"]
                assert abs(bbox[3] - expected_bbox[3]) < dataset["bbox_tolerance"]

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_gdide_url_based_extraction(self):
        """Test full fromRemote() with geoportal.de landing URL"""
        dataset = TEST_DATASETS["forest_canopy_loss"]

        try:
            result = geoextent.fromRemote(
                dataset["landing_url"],
                bbox=True,
                tbox=True,
                download_data=False,
            )

            assert result is not None
            assert result["format"] == "remote"

            if "bbox" in result and result["bbox"] is not None:
                bbox = result["bbox"]
                expected_bbox = dataset["expected_bbox"]
                tol = dataset["bbox_tolerance"]

                assert abs(bbox[0] - expected_bbox[0]) < tol
                assert abs(bbox[1] - expected_bbox[1]) < tol
                assert abs(bbox[2] - expected_bbox[2]) < tol
                assert abs(bbox[3] - expected_bbox[3]) < tol

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_gdide_convex_hull_multiple(self, tmp_path, monkeypatch):
        """Verify convex hull with two non-overlapping bboxes.

        Mocks the GDI-DE CSW to return two separate records with
        non-overlapping bounding boxes. With convex_hull=True, the result
        should contain >4 unique vertices.
        """
        from geoextent.lib.content_providers.GDIDE import GDIDE

        # Create two mock GeoJSON files with non-overlapping bboxes
        # One in northern Germany, one in southern Germany
        geojson_north = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [9.0, 53.0],
                                [11.0, 53.0],
                                [11.0, 55.0],
                                [9.0, 55.0],
                                [9.0, 53.0],
                            ]
                        ],
                    },
                    "properties": {"source": "GDI-DE", "title": "North"},
                }
            ],
        }

        geojson_south = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [11.0, 47.0],
                                [13.0, 47.0],
                                [13.0, 49.0],
                                [11.0, 49.0],
                                [11.0, 47.0],
                            ]
                        ],
                    },
                    "properties": {"source": "GDI-DE", "title": "South"},
                }
            ],
        }

        # Write mock GeoJSON files to tmp_path
        download_dir = tmp_path / "gdide_mock"
        download_dir.mkdir()

        with open(download_dir / "gdide_north.geojson", "w") as f:
            json.dump(geojson_north, f)

        with open(download_dir / "gdide_south.geojson", "w") as f:
            json.dump(geojson_south, f)

        # Mock the download method to write our test files
        def mock_download(
            self,
            folder,
            throttle=False,
            download_data=True,
            show_progress=True,
            **kwargs,
        ):
            import shutil

            target = os.path.join(folder, "gdide_mock")
            if not os.path.exists(target):
                shutil.copytree(str(download_dir), target)
            return target

        monkeypatch.setattr(GDIDE, "download", mock_download)

        result = geoextent.fromRemote(
            "https://www.geoportal.de/Metadata/75987CE0-AA66-4445-AC44-068B98390E89",
            bbox=True,
            tbox=False,
            download_data=False,
            convex_hull=True,
        )

        assert result is not None
        assert result.get("convex_hull") is True, "Expected convex_hull flag"

        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from merged extents"
        # In convex hull mode, bbox is a GeoJSON Polygon dict
        assert isinstance(
            bbox, dict
        ), f"Expected dict for convex hull, got {type(bbox)}"
        assert bbox.get("type") == "Polygon"
        coords = bbox["coordinates"][0]
        # Two non-overlapping rectangles should produce >4 unique vertices
        unique_coords = set(tuple(c) for c in coords[:-1])  # exclude closing point
        assert len(unique_coords) > 4, (
            f"Expected >4 unique vertices for convex hull of two disjoint bboxes, "
            f"got {len(unique_coords)}: {unique_coords}"
        )
