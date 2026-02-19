import json
import os
import pytest
import geoextent.lib.extent as geoextent
from conftest import NETWORK_SKIP_EXCEPTIONS


class TestUkcehProvider:
    """Test UKCEH (UK Centre for Ecology & Hydrology) content provider."""

    TEST_DATASETS = {
        "blelham_tarn": {
            "doi": "10.5285/dd35316a-cecc-4f6d-9a21-74a0f6599e9e",
            "uuid": "dd35316a-cecc-4f6d-9a21-74a0f6599e9e",
            "description": "Blelham Tarn water chemistry",
            "expected_bbox": {
                "west": -2.985,
                "south": 54.393,
                "east": -2.973,
                "north": 54.399,
            },
            "has_tbox": True,
            "expected_tbox": ["2019-01-01", "2020-12-31"],
        },
        "mozambique_biomass": {
            "doi": "10.5285/6a8b07f9-552e-408c-8351-595ee6a7fc5f",
            "uuid": "6a8b07f9-552e-408c-8351-595ee6a7fc5f",
            "description": "Mozambique woody biomass",
            "expected_bbox": {
                "west": 29.871,
                "south": -27.056,
                "east": 42.137,
                "north": -9.971,
            },
            "has_tbox": True,
            "expected_tbox": ["2007-01-01", "2014-12-31"],
        },
        "lake_victoria": {
            "doi": "10.5285/02977a5d-00a0-44f8-baee-d2e0eecb5df0",
            "uuid": "02977a5d-00a0-44f8-baee-d2e0eecb5df0",
            "description": "Lake Victoria erosion",
            "expected_bbox": {
                "west": 29.421,
                "south": -3.842,
                "east": 35.89,
                "north": 1.28,
            },
            "has_tbox": True,
            "expected_tbox": ["2000-01-01", "2022-12-31"],
        },
        "ozone_model": {
            "doi": "10.5285/4b0871a9-196a-48e1-a0c8-c5f53e17e9a7",
            "uuid": "4b0871a9-196a-48e1-a0c8-c5f53e17e9a7",
            "description": "UK/USA ozone model",
            "expected_bbox": {
                "west": -174.375,
                "south": 23.241,
                "east": 1.768,
                "north": 71.301,
            },
            "has_tbox": True,
            "expected_tbox": ["2018-01-01", "2018-12-31"],
        },
        "dddac": {
            "doi": "10.5285/3de48cb6-d1c2-446e-a652-57d329849361",
            "uuid": "3de48cb6-d1c2-446e-a652-57d329849361",
            "description": "Dynamic drivers of disease in Africa (3 bboxes)",
            "num_bboxes": 3,
            "expected_bbox": {
                # Merged envelope of all 3 bounding boxes
                "west": 21.711,
                "south": -18.729,
                "east": 41.14,
                "north": 0.64,
            },
            "has_tbox": True,
            "expected_tbox": ["2012-01-01", "2016-04-30"],
        },
    }

    # -- Fast validation tests (no network) --

    def test_ukceh_doi_validation(self):
        """Test that UKCEH DOI prefix 10.5285/ is correctly validated"""
        from geoextent.lib.content_providers.UKCEH import UKCEH

        provider = UKCEH()
        assert provider.validate_provider(
            "10.5285/6a8b07f9-552e-408c-8351-595ee6a7fc5f"
        )
        assert provider.record_id == "6a8b07f9-552e-408c-8351-595ee6a7fc5f"

    def test_ukceh_url_validation(self):
        """Test that catalogue.ceh.ac.uk URLs are validated"""
        from geoextent.lib.content_providers.UKCEH import UKCEH

        provider = UKCEH()
        assert provider.validate_provider(
            "https://catalogue.ceh.ac.uk/documents/6a8b07f9-552e-408c-8351-595ee6a7fc5f"
        )
        assert provider.record_id == "6a8b07f9-552e-408c-8351-595ee6a7fc5f"

    def test_ukceh_validation_invalid_identifiers(self):
        """Test that non-UKCEH URLs/DOIs are rejected"""
        from geoextent.lib.content_providers.UKCEH import UKCEH

        provider = UKCEH()
        assert not provider.validate_provider("https://zenodo.org/record/4593540")
        assert not provider.validate_provider("10.5281/zenodo.4593540")
        assert not provider.validate_provider("https://example.com/dataset/123")

    def test_ukceh_provider_instantiation(self):
        """Test basic provider creation and metadata extraction support"""
        from geoextent.lib.content_providers.UKCEH import UKCEH

        provider = UKCEH()
        assert provider.name == "UKCEH"
        assert provider.supports_metadata_extraction is True
        info = provider.provider_info()
        assert info["name"] == "UKCEH"
        assert "10.5285" in info["doi_prefix"]

    def test_ukceh_parse_datastore_listing_validation(self):
        """Unit test for _parse_human_size with various Apache size strings"""
        from geoextent.lib.content_providers.UKCEH import UKCEH

        assert UKCEH._parse_human_size("56M") == 56 * 1024 * 1024
        assert UKCEH._parse_human_size("6.4M") == int(6.4 * 1024 * 1024)
        assert UKCEH._parse_human_size("419K") == 419 * 1024
        assert UKCEH._parse_human_size("1.5G") == int(1.5 * 1024 * 1024 * 1024)
        assert UKCEH._parse_human_size("") == 0
        assert UKCEH._parse_human_size("abc") == 0
        assert UKCEH._parse_human_size("-") == 0

    # -- Network tests (auto-marked slow via conftest) --

    def test_ukceh_metadata_only_extraction(self):
        """Test metadata-only extraction (provider_sample smoke test)"""
        ds = self.TEST_DATASETS["blelham_tarn"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or UKCEH unreachable")

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from UKCEH metadata"
        # Default output: [minlat, minlon, maxlat, maxlon]
        minlat, minlon, maxlat, maxlon = bbox
        assert 54.0 < minlat < 55.0
        assert -3.0 < minlon < -2.5
        assert 54.0 < maxlat < 55.0
        assert -3.0 < maxlon < -2.5

        tbox = result.get("tbox")
        assert tbox is not None, "Expected temporal extent from UKCEH metadata"
        assert len(tbox) == 2

    def test_ukceh_blelham_tarn(self):
        """10.5285/dd35316a...: Blelham Tarn water chemistry — bbox + tbox"""
        ds = self.TEST_DATASETS["blelham_tarn"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or UKCEH unreachable")

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None
        minlat, minlon, maxlat, maxlon = bbox
        eb = ds["expected_bbox"]
        assert abs(minlat - eb["south"]) < 0.5, f"south: {minlat} vs {eb['south']}"
        assert abs(minlon - eb["west"]) < 0.5, f"west: {minlon} vs {eb['west']}"
        assert abs(maxlat - eb["north"]) < 0.5, f"north: {maxlat} vs {eb['north']}"
        assert abs(maxlon - eb["east"]) < 0.5, f"east: {maxlon} vs {eb['east']}"

        tbox = result.get("tbox")
        assert tbox is not None
        assert tbox[0] == ds["expected_tbox"][0]
        assert tbox[1] == ds["expected_tbox"][1]

    def test_ukceh_mozambique_biomass(self):
        """10.5285/6a8b07f9...: Mozambique woody biomass — bbox + tbox"""
        ds = self.TEST_DATASETS["mozambique_biomass"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or UKCEH unreachable")

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None
        minlat, minlon, maxlat, maxlon = bbox
        eb = ds["expected_bbox"]
        assert abs(minlat - eb["south"]) < 1.0, f"south: {minlat} vs {eb['south']}"
        assert abs(minlon - eb["west"]) < 1.0, f"west: {minlon} vs {eb['west']}"
        assert abs(maxlat - eb["north"]) < 1.0, f"north: {maxlat} vs {eb['north']}"
        assert abs(maxlon - eb["east"]) < 1.0, f"east: {maxlon} vs {eb['east']}"

        tbox = result.get("tbox")
        assert tbox is not None
        assert tbox[0] == ds["expected_tbox"][0]
        assert tbox[1] == ds["expected_tbox"][1]

    def test_ukceh_lake_victoria(self):
        """10.5285/02977a5d...: Lake Victoria erosion — bbox + tbox"""
        ds = self.TEST_DATASETS["lake_victoria"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or UKCEH unreachable")

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None
        minlat, minlon, maxlat, maxlon = bbox
        eb = ds["expected_bbox"]
        assert abs(minlat - eb["south"]) < 1.0, f"south: {minlat} vs {eb['south']}"
        assert abs(minlon - eb["west"]) < 1.0, f"west: {minlon} vs {eb['west']}"
        assert abs(maxlat - eb["north"]) < 1.0, f"north: {maxlat} vs {eb['north']}"
        assert abs(maxlon - eb["east"]) < 1.0, f"east: {maxlon} vs {eb['east']}"

        tbox = result.get("tbox")
        assert tbox is not None
        assert tbox[0] == ds["expected_tbox"][0]
        assert tbox[1] == ds["expected_tbox"][1]

    def test_ukceh_ozone_model(self):
        """10.5285/4b0871a9...: UK/USA ozone model — bbox + tbox"""
        ds = self.TEST_DATASETS["ozone_model"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or UKCEH unreachable")

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None
        minlat, minlon, maxlat, maxlon = bbox
        eb = ds["expected_bbox"]
        assert abs(minlat - eb["south"]) < 1.0, f"south: {minlat} vs {eb['south']}"
        assert abs(minlon - eb["west"]) < 1.0, f"west: {minlon} vs {eb['west']}"
        assert abs(maxlat - eb["north"]) < 1.0, f"north: {maxlat} vs {eb['north']}"
        assert abs(maxlon - eb["east"]) < 1.0, f"east: {maxlon} vs {eb['east']}"

        tbox = result.get("tbox")
        assert tbox is not None
        assert tbox[0] == ds["expected_tbox"][0]
        assert tbox[1] == ds["expected_tbox"][1]

    def test_ukceh_dddac_convex_hull(self):
        """10.5285/3de48cb6...: DDDAC — convex hull from 3 non-overlapping bboxes.

        This dataset has 3 bounding boxes in different parts of Africa
        (Kenya coast, southern Africa, Kenya/Somalia). The convex hull of
        these disjoint rectangles must have >4 unique vertices — proving it
        is not just a simple axis-aligned rectangle.
        """
        ds = self.TEST_DATASETS["dddac"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
                convex_hull=True,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or UKCEH unreachable")

        assert result is not None
        assert result.get("convex_hull") is True, "Expected convex_hull flag"

        bbox = result.get("bbox")
        assert bbox is not None, "Expected convex hull bbox"
        # In convex hull mode, bbox is a GeoJSON Polygon dict
        assert isinstance(bbox, dict), f"Expected dict, got {type(bbox)}"
        assert bbox.get("type") == "Polygon"

        coords = bbox["coordinates"][0]
        unique_coords = set(tuple(c) for c in coords[:-1])  # exclude closing point
        assert len(unique_coords) > 4, (
            f"Expected >4 unique vertices for convex hull of 3 disjoint bboxes, "
            f"got {len(unique_coords)}: {unique_coords}"
        )

        # Verify the hull encloses all three bboxes by checking that the
        # overall extent matches the merged envelope (lat/lon in output order)
        eb = ds["expected_bbox"]
        all_lats = [c[0] for c in coords]
        all_lons = [c[1] for c in coords]
        assert min(all_lats) == pytest.approx(eb["south"], abs=1.0)
        assert max(all_lats) == pytest.approx(eb["north"], abs=1.0)
        assert min(all_lons) == pytest.approx(eb["west"], abs=1.0)
        assert max(all_lons) == pytest.approx(eb["east"], abs=1.0)

        tbox = result.get("tbox")
        assert tbox is not None
        assert tbox[0] == ds["expected_tbox"][0]
        assert tbox[1] == ds["expected_tbox"][1]

    # -- Convex hull test (unit, no network, mocked API response) --

    def test_ukceh_convex_hull_multiple_extents(self, tmp_path, monkeypatch):
        """Verify convex hull with multiple boundingBoxes entries preserves individual shapes.

        Mocks the UKCEH API to return two non-overlapping bounding boxes.
        With convex_hull=True, the result should contain a bbox derived from all
        individual feature polygons rather than a pre-merged rectangle.
        """
        from geoextent.lib.content_providers.UKCEH import UKCEH

        # Two non-overlapping bboxes: one in UK, one in East Africa
        mock_response = {
            "id": "00000000-0000-0000-0000-000000000000",
            "title": "Mock multi-bbox dataset",
            "boundingBoxes": [
                {
                    "westBoundLongitude": -3.0,
                    "eastBoundLongitude": -2.0,
                    "southBoundLatitude": 54.0,
                    "northBoundLatitude": 55.0,
                },
                {
                    "westBoundLongitude": 30.0,
                    "eastBoundLongitude": 36.0,
                    "southBoundLatitude": -4.0,
                    "northBoundLatitude": 2.0,
                },
            ],
            "temporalExtents": [{"begin": "2020-01-01", "end": "2022-12-31"}],
            "onlineResources": [],
            "accessLimitation": {"code": "Available"},
        }

        class MockResponse:
            status_code = 200

            def json(self):
                return mock_response

            def raise_for_status(self):
                pass

        def mock_request(self, url, **kwargs):
            if "doi.org" in url:
                resp = MockResponse()
                resp.url = (
                    "https://catalogue.ceh.ac.uk/documents/"
                    "00000000-0000-0000-0000-000000000000"
                )
                return resp
            return MockResponse()

        monkeypatch.setattr(UKCEH, "_request", mock_request)

        result = geoextent.fromRemote(
            "10.5285/00000000-0000-0000-0000-000000000000",
            bbox=True,
            tbox=True,
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

        tbox = result.get("tbox")
        assert tbox is not None
        assert tbox[0] == "2020-01-01"
        assert tbox[1] == "2022-12-31"
