import json
import os
import pytest
import geoextent.lib.extent as geoextent
from conftest import NETWORK_SKIP_EXCEPTIONS


class TestSeanoeProvider:
    """Test SEANOE (SEA scieNtific Open data Edition) content provider."""

    TEST_DATASETS = {
        "french_mediterranean_ctd": {
            "doi": "10.17882/105467",
            "description": "CTD French Mediterranean",
            "expected_bbox": {
                "west": 2.70,
                "south": 42.39,
                "east": 7.56,
                "north": 43.92,
            },
            "has_tbox": True,
            "expected_tbox": ["2024-05-21", "2024-06-10"],
        },
        "ireland_rei": {
            "doi": "10.17882/109463",
            "description": "Ireland coastline REI",
            "expected_bbox": {
                "west": -10.82,
                "south": 51.30,
                "east": -5.20,
                "north": 55.49,
            },
            "has_tbox": False,
        },
        "hawaii_drone_thermal": {
            "doi": "10.17882/108464",
            "description": "Drone thermal, Hawaii (point extent)",
            "expected_bbox": {
                "west": -157.79,
                "south": 21.26,
                "east": -157.79,
                "north": 21.26,
            },
            "has_tbox": True,
            "expected_tbox": ["2024-05-13", "2025-04-04"],
        },
        "bathymetry": {
            "doi": "10.17882/103743",
            "description": "Shipboard bathymetry (Indian Ocean)",
            "expected_bbox": {
                "west": 64.27,
                "south": -28.27,
                "east": 64.82,
                "north": -27.56,
            },
            "has_tbox": False,
        },
        "whale_biologging": {
            "doi": "10.17882/112127",
            "description": "Bowhead whale biologging",
            "expected_bbox": {
                "west": -65.51,
                "south": 65.60,
                "east": -64.69,
                "north": 65.77,
            },
            "has_tbox": True,
            "expected_tbox": ["2023-07-31", "2024-08-12"],
        },
    }

    # -- Fast validation tests (no network) --

    def test_seanoe_doi_validation(self):
        """Test that SEANOE DOI prefix 10.17882/ is correctly validated"""
        from geoextent.lib.content_providers.SEANOE import SEANOE

        provider = SEANOE()
        assert provider.validate_provider("10.17882/105467")
        assert provider.record_id == "105467"

    def test_seanoe_url_validation(self):
        """Test that seanoe.org landing page URLs are validated"""
        from geoextent.lib.content_providers.SEANOE import SEANOE

        provider = SEANOE()
        assert provider.validate_provider("https://www.seanoe.org/data/00943/105467/")
        assert provider.record_id == "105467"

    def test_seanoe_validation_invalid_identifiers(self):
        """Test that non-SEANOE URLs/DOIs are rejected"""
        from geoextent.lib.content_providers.SEANOE import SEANOE

        provider = SEANOE()
        assert not provider.validate_provider("https://zenodo.org/record/4593540")
        assert not provider.validate_provider("10.5281/zenodo.4593540")
        assert not provider.validate_provider("https://example.com/dataset/123")

    def test_seanoe_provider_instantiation(self):
        """Test basic provider creation and metadata extraction support"""
        from geoextent.lib.content_providers.SEANOE import SEANOE

        provider = SEANOE()
        assert provider.name == "SEANOE"
        assert provider.supports_metadata_extraction is True
        info = provider.provider_info()
        assert info["name"] == "SEANOE"
        assert "10.17882" in info["doi_prefix"]

    # -- Network tests (auto-marked slow via conftest) --

    def test_seanoe_metadata_only_extraction(self):
        """Test metadata-only extraction (provider_sample smoke test)"""
        ds = self.TEST_DATASETS["french_mediterranean_ctd"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or SEANOE unreachable")

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from SEANOE metadata"
        # Default output: [minlat, minlon, maxlat, maxlon]
        minlat, minlon, maxlat, maxlon = bbox
        assert 42.0 < minlat < 43.0
        assert 2.0 < minlon < 3.5
        assert 43.5 < maxlat < 44.5
        assert 7.0 < maxlon < 8.0

        tbox = result.get("tbox")
        assert tbox is not None, "Expected temporal extent from SEANOE metadata"
        assert len(tbox) == 2

    def test_seanoe_french_mediterranean_ctd(self):
        """10.17882/105467: CTD French Mediterranean — bbox + tbox"""
        ds = self.TEST_DATASETS["french_mediterranean_ctd"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or SEANOE unreachable")

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None
        # Default: [minlat, minlon, maxlat, maxlon]
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

    def test_seanoe_ireland_rei(self):
        """10.17882/109463: Ireland coastline REI — bbox, no tbox"""
        ds = self.TEST_DATASETS["ireland_rei"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or SEANOE unreachable")

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None
        minlat, minlon, maxlat, maxlon = bbox
        eb = ds["expected_bbox"]
        assert abs(minlat - eb["south"]) < 0.5
        assert abs(minlon - eb["west"]) < 0.5
        assert abs(maxlat - eb["north"]) < 0.5
        assert abs(maxlon - eb["east"]) < 0.5

    def test_seanoe_hawaii_drone_thermal(self):
        """10.17882/108464: Drone thermal, Hawaii — point bbox + tbox"""
        ds = self.TEST_DATASETS["hawaii_drone_thermal"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or SEANOE unreachable")

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None
        minlat, minlon, maxlat, maxlon = bbox
        eb = ds["expected_bbox"]
        assert abs(minlat - eb["south"]) < 0.5
        assert abs(minlon - eb["west"]) < 0.5

        tbox = result.get("tbox")
        assert tbox is not None
        assert tbox[0] == ds["expected_tbox"][0]
        assert tbox[1] == ds["expected_tbox"][1]

    def test_seanoe_bathymetry(self):
        """10.17882/103743: Shipboard bathymetry — bbox, no tbox"""
        ds = self.TEST_DATASETS["bathymetry"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or SEANOE unreachable")

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None
        minlat, minlon, maxlat, maxlon = bbox
        eb = ds["expected_bbox"]
        assert abs(minlat - eb["south"]) < 1.0
        assert abs(minlon - eb["west"]) < 1.0
        assert abs(maxlat - eb["north"]) < 1.0
        assert abs(maxlon - eb["east"]) < 1.0

    def test_seanoe_whale_biologging(self):
        """10.17882/112127: Bowhead whale biologging — bbox + tbox"""
        ds = self.TEST_DATASETS["whale_biologging"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or SEANOE unreachable")

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None
        minlat, minlon, maxlat, maxlon = bbox
        eb = ds["expected_bbox"]
        assert abs(minlat - eb["south"]) < 1.0
        assert abs(minlon - eb["west"]) < 1.0
        assert abs(maxlat - eb["north"]) < 1.0
        assert abs(maxlon - eb["east"]) < 1.0

        tbox = result.get("tbox")
        assert tbox is not None
        assert tbox[0] == ds["expected_tbox"][0]
        assert tbox[1] == ds["expected_tbox"][1]

    # -- Convex hull test (unit, no network, mocked API response) --

    def test_seanoe_convex_hull_multiple_extents(self, tmp_path, monkeypatch):
        """Verify convex hull with multiple geoExtendList entries preserves individual shapes.

        Mocks the SEANOE API to return two non-overlapping bounding boxes.
        With convex_hull=True, the result should contain a bbox derived from all
        individual feature polygons rather than a pre-merged rectangle.
        """
        from geoextent.lib.content_providers.SEANOE import SEANOE

        # Two non-overlapping bboxes: one in Mediterranean, one in North Atlantic
        mock_response = {
            "docId": 999999,
            "publicationDoi": "10.17882/999999",
            "geoExtendList": [
                {"north": 44.0, "south": 42.0, "east": 8.0, "west": 3.0},
                {"north": 60.0, "south": 55.0, "east": -10.0, "west": -20.0},
            ],
            "temporalExtend": {"begin": "2024-01-01", "end": "2024-12-31"},
            "files": [],
        }

        class MockResponse:
            status_code = 200

            def json(self):
                return mock_response

            def raise_for_status(self):
                pass

        def mock_request(self, url, **kwargs):
            # Handle DOI resolution
            if "doi.org" in url:
                resp = MockResponse()
                resp.url = "https://www.seanoe.org/data/00999/999999/"
                return resp
            return MockResponse()

        monkeypatch.setattr(SEANOE, "_request", mock_request)

        result = geoextent.fromRemote(
            "10.17882/999999",
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
        # (a simple merged rectangle would have exactly 4 unique vertices)
        unique_coords = set(tuple(c) for c in coords[:-1])  # exclude closing point
        assert len(unique_coords) > 4, (
            f"Expected >4 unique vertices for convex hull of two disjoint bboxes, "
            f"got {len(unique_coords)}: {unique_coords}"
        )

        tbox = result.get("tbox")
        assert tbox is not None
        assert tbox[0] == "2024-01-01"
        assert tbox[1] == "2024-12-31"
