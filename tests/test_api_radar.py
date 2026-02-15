import pytest
import geoextent.lib.extent as geoextent
from conftest import NETWORK_SKIP_EXCEPTIONS


class TestRADARProvider:
    """Test RADAR (FIZ Karlsruhe) content provider functionality"""

    TEST_DATASETS = {
        "parking2pv_hesse": {
            "doi": "10.35097/tvn5vujqfvf99f32",
            "url": "https://www.radar-service.eu/radar/en/dataset/tvn5vujqfvf99f32",
            "kit_url": "https://radar.kit.edu/radar/en/dataset/tvn5vujqfvf99f32",
            "description": "Parking2PV Hesse - parking lot PV potential (4.1 MB tar with GeoPackage)",
            "expected_bbox_lat": (49.3, 51.8),
            "expected_bbox_lon": (7.5, 10.5),
        },
        "rio_sao_francisco": {
            "doi": "10.35097/600",
            "url": "https://www.radar-service.eu/radar/en/dataset/600",
            "description": "Rio Sao Francisco Runoff (50.1 MB tar with Shapefiles, Brazil)",
            "expected_bbox_lat": (-26.0, -4.0),
            "expected_bbox_lon": (-51.0, -34.0),
        },
    }

    # -- Fast validation tests (no network) --

    def test_radar_url_validation(self):
        """Test that RADAR URLs are correctly validated"""
        from geoextent.lib.content_providers.RADAR import RADAR

        radar = RADAR()

        # Test www.radar-service.eu URL
        assert radar.validate_provider(
            "https://www.radar-service.eu/radar/en/dataset/tvn5vujqfvf99f32"
        )
        assert radar.record_id == "tvn5vujqfvf99f32"

        # Test radar.kit.edu URL
        radar2 = RADAR()
        assert radar2.validate_provider(
            "https://radar.kit.edu/radar/en/dataset/tvn5vujqfvf99f32"
        )
        assert radar2.record_id == "tvn5vujqfvf99f32"

        # Test German-language URL
        radar3 = RADAR()
        assert radar3.validate_provider(
            "https://www.radar-service.eu/radar/de/dataset/tvn5vujqfvf99f32"
        )
        assert radar3.record_id == "tvn5vujqfvf99f32"

        # Test backend URL
        radar4 = RADAR()
        assert radar4.validate_provider(
            "https://www.radar-service.eu/radar-backend/archives/tvn5vujqfvf99f32"
        )
        assert radar4.record_id == "tvn5vujqfvf99f32"

    def test_radar_doi_validation(self):
        """Test that RADAR DOI prefix 10.35097/ is correctly validated"""
        from geoextent.lib.content_providers.RADAR import RADAR

        radar = RADAR()
        assert radar.validate_provider("10.35097/tvn5vujqfvf99f32")

        radar2 = RADAR()
        assert radar2.validate_provider("https://doi.org/10.35097/tvn5vujqfvf99f32")

    def test_radar_url_validation_invalid_patterns(self):
        """Test that non-RADAR URLs are rejected"""
        from geoextent.lib.content_providers.RADAR import RADAR

        radar = RADAR()
        assert not radar.validate_provider("https://zenodo.org/record/4593540")
        assert not radar.validate_provider("10.5281/zenodo.4593540")
        assert not radar.validate_provider("https://example.com/dataset/123")
        assert not radar.validate_provider("https://dataservices.gfz-potsdam.de/foo")

    # -- Network tests (auto-marked slow via conftest) --

    def test_radar_metadata_only_extraction(self):
        """Test metadata-only extraction (provider_sample smoke test)"""
        ds = self.TEST_DATASETS["parking2pv_hesse"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=False,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or RADAR service unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"RADAR service unreachable: {e}")
            raise
        # RADAR doesn't support metadata-only extraction, so result may
        # have no bbox, but the call should not crash
        assert result is not None

    def test_radar_actual_bbox_extraction(self):
        """Test full download extraction from RADAR (Parking2PV Hesse dataset)"""
        ds = self.TEST_DATASETS["parking2pv_hesse"]
        try:
            result = geoextent.fromRemote(
                ds["url"],
                bbox=True,
                tbox=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or RADAR service unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"RADAR service unreachable: {e}")
            raise
        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from RADAR dataset"
        # Default output order: [minlat, minlon, maxlat, maxlon]
        minlat, minlon, maxlat, maxlon = bbox
        assert (
            ds["expected_bbox_lat"][0] < minlat < maxlat < ds["expected_bbox_lat"][1]
        ), f"Latitude range {minlat}-{maxlat} outside expected {ds['expected_bbox_lat']}"
        assert (
            ds["expected_bbox_lon"][0] < minlon < maxlon < ds["expected_bbox_lon"][1]
        ), f"Longitude range {minlon}-{maxlon} outside expected {ds['expected_bbox_lon']}"

    def test_radar_doi_extraction(self):
        """Test extraction via DOI resolution"""
        ds = self.TEST_DATASETS["parking2pv_hesse"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or RADAR service unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"RADAR service unreachable: {e}")
            raise
        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from RADAR DOI"

    @pytest.mark.large_download
    def test_radar_large_dataset_extraction(self):
        """Test extraction from large RADAR dataset (Rio Sao Francisco, ~50 MB)"""
        ds = self.TEST_DATASETS["rio_sao_francisco"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or RADAR service unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"RADAR service unreachable: {e}")
            raise
        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from large RADAR dataset"
        # Default output order: [minlat, minlon, maxlat, maxlon]
        minlat, minlon, maxlat, maxlon = bbox
        assert (
            ds["expected_bbox_lat"][0] < minlat < maxlat < ds["expected_bbox_lat"][1]
        ), f"Latitude range {minlat}-{maxlat} outside expected {ds['expected_bbox_lat']}"
        assert (
            ds["expected_bbox_lon"][0] < minlon < maxlon < ds["expected_bbox_lon"][1]
        ), f"Longitude range {minlon}-{maxlon} outside expected {ds['expected_bbox_lon']}"

    def test_radar_kit_url_extraction(self):
        """Test extraction via radar.kit.edu URL variant"""
        ds = self.TEST_DATASETS["parking2pv_hesse"]
        try:
            result = geoextent.fromRemote(
                ds["kit_url"],
                bbox=True,
                tbox=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or RADAR service unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"RADAR service unreachable: {e}")
            raise
        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from radar.kit.edu URL"
