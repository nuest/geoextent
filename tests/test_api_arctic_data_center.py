import pytest
import geoextent.lib.extent as geoextent
from conftest import NETWORK_SKIP_EXCEPTIONS


class TestArcticDataCenterProvider:
    """Test NSF Arctic Data Center content provider functionality"""

    TEST_DATASETS = {
        "ice_wedge_point_lay": {
            "doi": "10.18739/A2Z892H2J",
            "catalog_url": "https://arcticdata.io/catalog/view/doi%3A10.18739%2FA2Z892H2J",
            "description": "Ice Wedge Thermokarst, Point Lay, AK (2 GeoJSON, 1.6 MB)",
            "expected_bbox_lat": (69.5, 70.0),
            "expected_bbox_lon": (-163.5, -162.5),
        },
        "circum_arctic_permafrost": {
            "urn_uuid": "urn:uuid:054b4c9a-8be1-4d28-8724-5e2beb0ce4e6",
            "description": "Circum-Arctic Permafrost (GeoPackage + GeoTIFF, 10.7 MB)",
            "expected_bbox_lat": (60.0, 90.0),
            "expected_bbox_lon": (-180.0, 180.0),
        },
    }

    # -- Fast validation tests (no network) --

    def test_adc_doi_validation(self):
        """Test that Arctic Data Center DOI prefix 10.18739/ is correctly validated"""
        from geoextent.lib.content_providers.ArcticDataCenter import ArcticDataCenter

        adc = ArcticDataCenter()
        assert adc.validate_provider("10.18739/A2Z892H2J")
        assert adc.dataset_id == "doi:10.18739/A2Z892H2J"

        adc2 = ArcticDataCenter()
        assert adc2.validate_provider("https://doi.org/10.18739/A2Z892H2J")
        assert adc2.dataset_id == "doi:10.18739/A2Z892H2J"

    def test_adc_url_validation(self):
        """Test that arcticdata.io catalog URLs are correctly validated"""
        from geoextent.lib.content_providers.ArcticDataCenter import ArcticDataCenter

        # DOI catalog URL
        adc = ArcticDataCenter()
        assert adc.validate_provider(
            "https://arcticdata.io/catalog/view/doi%3A10.18739%2FA2Z892H2J"
        )
        assert adc.dataset_id == "doi:10.18739/A2Z892H2J"

        # URN UUID catalog URL
        adc2 = ArcticDataCenter()
        assert adc2.validate_provider(
            "https://arcticdata.io/catalog/view/urn%3Auuid%3A054b4c9a-8be1-4d28-8724-5e2beb0ce4e6"
        )
        assert adc2.dataset_id == "urn:uuid:054b4c9a-8be1-4d28-8724-5e2beb0ce4e6"

    def test_adc_urn_uuid_validation(self):
        """Test that URN UUID identifiers are correctly validated"""
        from geoextent.lib.content_providers.ArcticDataCenter import ArcticDataCenter

        adc = ArcticDataCenter()
        assert adc.validate_provider("urn:uuid:054b4c9a-8be1-4d28-8724-5e2beb0ce4e6")
        assert adc.dataset_id == "urn:uuid:054b4c9a-8be1-4d28-8724-5e2beb0ce4e6"

    def test_adc_validation_invalid_patterns(self):
        """Test that non-ADC URLs/DOIs are rejected"""
        from geoextent.lib.content_providers.ArcticDataCenter import ArcticDataCenter

        adc = ArcticDataCenter()
        assert not adc.validate_provider("https://zenodo.org/record/4593540")
        assert not adc.validate_provider("10.5281/zenodo.4593540")
        assert not adc.validate_provider("https://example.com/dataset/123")
        assert not adc.validate_provider("10.35097/tvn5vujqfvf99f32")

    def test_adc_supports_metadata_extraction(self):
        """Test that provider reports metadata extraction support"""
        from geoextent.lib.content_providers.ArcticDataCenter import ArcticDataCenter

        adc = ArcticDataCenter()
        assert adc.supports_metadata_extraction is True

    # -- Network tests (auto-marked slow via conftest) --

    def test_adc_metadata_only_extraction(self):
        """Test metadata-only extraction (provider_sample smoke test)"""
        ds = self.TEST_DATASETS["ice_wedge_point_lay"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or Arctic Data Center unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"Arctic Data Center unreachable: {e}")
            raise
        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from Arctic Data Center metadata"
        # Default output order: [minlat, minlon, maxlat, maxlon]
        minlat, minlon, maxlat, maxlon = bbox
        assert (
            ds["expected_bbox_lat"][0] < minlat < maxlat < ds["expected_bbox_lat"][1]
        ), f"Latitude range {minlat}-{maxlat} outside expected {ds['expected_bbox_lat']}"
        assert (
            ds["expected_bbox_lon"][0] < minlon < maxlon < ds["expected_bbox_lon"][1]
        ), f"Longitude range {minlon}-{maxlon} outside expected {ds['expected_bbox_lon']}"

    def test_adc_actual_bbox_extraction(self):
        """Test full download extraction from Arctic Data Center"""
        ds = self.TEST_DATASETS["ice_wedge_point_lay"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or Arctic Data Center unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"Arctic Data Center unreachable: {e}")
            raise
        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from Arctic Data Center dataset"
        # Default output order: [minlat, minlon, maxlat, maxlon]
        minlat, minlon, maxlat, maxlon = bbox
        assert (
            ds["expected_bbox_lat"][0] < minlat < maxlat < ds["expected_bbox_lat"][1]
        ), f"Latitude range {minlat}-{maxlat} outside expected {ds['expected_bbox_lat']}"
        assert (
            ds["expected_bbox_lon"][0] < minlon < maxlon < ds["expected_bbox_lon"][1]
        ), f"Longitude range {minlon}-{maxlon} outside expected {ds['expected_bbox_lon']}"

    def test_adc_urn_uuid_extraction(self):
        """Test extraction via URN UUID identifier (metadata-only)"""
        ds = self.TEST_DATASETS["circum_arctic_permafrost"]
        try:
            result = geoextent.fromRemote(
                ds["urn_uuid"],
                bbox=True,
                tbox=False,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or Arctic Data Center unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"Arctic Data Center unreachable: {e}")
            raise
        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from Arctic Data Center URN UUID"

    def test_adc_temporal_extraction(self):
        """Test temporal extent extraction from Arctic Data Center metadata"""
        ds = self.TEST_DATASETS["ice_wedge_point_lay"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=False,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or Arctic Data Center unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"Arctic Data Center unreachable: {e}")
            raise
        assert result is not None
        tbox = result.get("tbox")
        assert (
            tbox is not None
        ), "Expected temporal extent from Arctic Data Center metadata"
