import pytest
import geoextent.lib.extent as geoextent
from conftest import NETWORK_SKIP_EXCEPTIONS


class TestDataOneProvider:
    """Test DataONE content provider functionality."""

    # Test datasets from different DataONE member nodes.
    # Each entry uses a DOI whose prefix maps to that node.
    TEST_DATASETS = {
        # KNB — Knowledge Network for Biocomplexity (DOI prefix 10.5063/)
        "knb_alaska_elevation": {
            "doi": "10.5063/F1Z60M87",
            "description": "Elevation per SASAP region, Alaskan watersheds (KNB)",
            "expected_bbox_lat": (50.0, 75.0),
            "expected_bbox_lon": (-170.0, -125.0),
            "has_temporal": True,
        },
        # PISCO — Partnership for Interdisciplinary Studies of Coastal Oceans
        # (DOI prefix 10.6085/)
        "pisco_kelp_forest": {
            "doi": "10.6085/AA/PISCO_kelpforest.1.11",
            "description": "PISCO Kelp Forest Community Surveys (PISCO)",
            "expected_bbox_lat": (30.0, 50.0),
            "expected_bbox_lon": (-130.0, -115.0),
            "has_temporal": True,
        },
    }

    # -- Fast validation tests (no network) --

    def test_dataone_doi_validation_knb(self):
        """KNB DOI prefix 10.5063/ is correctly validated."""
        from geoextent.lib.content_providers.DataOne import DataOne

        d = DataOne()
        assert d.validate_provider("10.5063/F1Z60M87")
        assert d.dataset_id == "doi:10.5063/F1Z60M87"

    def test_dataone_doi_validation_pisco(self):
        """PISCO DOI prefix 10.6085/ is correctly validated."""
        from geoextent.lib.content_providers.DataOne import DataOne

        d = DataOne()
        assert d.validate_provider("10.6085/AA/PISCO_kelpforest.1.11")
        assert d.dataset_id == "doi:10.6085/AA/PISCO_kelpforest.1.11"

    def test_dataone_doi_validation_full_url(self):
        """DOI URL (https://doi.org/...) is correctly validated."""
        from geoextent.lib.content_providers.DataOne import DataOne

        d = DataOne()
        assert d.validate_provider("https://doi.org/10.5063/F1Z60M87")
        assert d.dataset_id == "doi:10.5063/F1Z60M87"

    def test_dataone_url_validation_search(self):
        """search.dataone.org URLs are correctly validated."""
        from geoextent.lib.content_providers.DataOne import DataOne

        d = DataOne()
        assert d.validate_provider(
            "https://search.dataone.org/view/doi%3A10.5063%2FF1Z60M87"
        )
        assert d.dataset_id == "doi:10.5063/F1Z60M87"

    def test_dataone_url_validation_search_hash(self):
        """search.dataone.org hash-based URLs (#view/) are correctly validated."""
        from geoextent.lib.content_providers.DataOne import DataOne

        d = DataOne()
        assert d.validate_provider(
            "https://search.dataone.org/#view/doi:10.5063/F1Z60M87"
        )
        assert d.dataset_id == "doi:10.5063/F1Z60M87"

    def test_dataone_url_validation_datasets(self):
        """dataone.org/datasets/ PIRI URLs are correctly validated."""
        from geoextent.lib.content_providers.DataOne import DataOne

        d = DataOne()
        assert d.validate_provider(
            "https://dataone.org/datasets/doi%3A10.5063%2FF1Z60M87"
        )
        assert d.dataset_id == "doi:10.5063/F1Z60M87"

    def test_dataone_url_validation_cn_object(self):
        """CN object URLs are correctly validated."""
        from geoextent.lib.content_providers.DataOne import DataOne

        d = DataOne()
        assert d.validate_provider(
            "https://cn.dataone.org/cn/v2/object/doi%3A10.5063%2FF1Z60M87"
        )
        assert d.dataset_id == "doi:10.5063/F1Z60M87"

    def test_dataone_url_validation_cn_resolve(self):
        """CN resolve URLs are correctly validated."""
        from geoextent.lib.content_providers.DataOne import DataOne

        d = DataOne()
        assert d.validate_provider(
            "https://cn.dataone.org/cn/v2/resolve/doi%3A10.5063%2FF1Z60M87"
        )
        assert d.dataset_id == "doi:10.5063/F1Z60M87"

    def test_dataone_invalid_identifiers(self):
        """Non-DataONE identifiers are rejected."""
        from geoextent.lib.content_providers.DataOne import DataOne

        d = DataOne()
        assert not d.validate_provider("https://zenodo.org/record/4593540")
        assert not d.validate_provider("10.5281/zenodo.4593540")
        assert not d.validate_provider("https://example.com/dataset/123")
        assert not d.validate_provider("10.18739/A2KW57K57")  # Arctic Data Center

    def test_dataone_supports_metadata_extraction(self):
        """Provider reports metadata extraction support."""
        from geoextent.lib.content_providers.DataOne import DataOne

        d = DataOne()
        assert d.supports_metadata_extraction is True

    def test_dataone_provider_info(self):
        """Provider info is complete."""
        from geoextent.lib.content_providers.DataOne import DataOne

        info = DataOne.provider_info()
        assert info is not None
        assert "DataONE" in info["name"]
        assert info["website"]
        assert info["supported_identifiers"]

    # -- Network tests (auto-marked slow via conftest) --

    def test_dataone_metadata_only_extraction(self):
        """Smoke test: metadata-only extraction from KNB via DataONE CN (provider_sample)."""
        ds = self.TEST_DATASETS["knb_alaska_elevation"]
        try:
            result = geoextent.from_remote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or DataONE CN unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"DataONE CN unreachable: {e}")
            raise

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from DataONE metadata"
        # Default output order: [minlat, minlon, maxlat, maxlon]
        minlat, minlon, maxlat, maxlon = bbox
        assert (
            ds["expected_bbox_lat"][0] < minlat < maxlat < ds["expected_bbox_lat"][1]
        ), f"Latitude range {minlat}-{maxlat} outside expected {ds['expected_bbox_lat']}"
        assert (
            ds["expected_bbox_lon"][0] < minlon < maxlon < ds["expected_bbox_lon"][1]
        ), f"Longitude range {minlon}-{maxlon} outside expected {ds['expected_bbox_lon']}"

    def test_dataone_knb_bbox_and_temporal(self):
        """KNB (10.5063/) dataset: spatial and temporal extraction."""
        ds = self.TEST_DATASETS["knb_alaska_elevation"]
        try:
            result = geoextent.from_remote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or DataONE CN unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"DataONE CN unreachable: {e}")
            raise

        assert result is not None
        assert result.get("bbox") is not None, "Expected bbox from KNB dataset"
        if ds["has_temporal"]:
            assert result.get("tbox") is not None, "Expected tbox from KNB dataset"

    def test_dataone_pisco_bbox_and_temporal(self):
        """PISCO (10.6085/) dataset: spatial and temporal extraction."""
        ds = self.TEST_DATASETS["pisco_kelp_forest"]
        try:
            result = geoextent.from_remote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or DataONE CN unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"DataONE CN unreachable: {e}")
            raise

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from PISCO dataset"
        minlat, minlon, maxlat, maxlon = bbox
        assert (
            ds["expected_bbox_lat"][0] < minlat < maxlat < ds["expected_bbox_lat"][1]
        ), f"Latitude range {minlat}-{maxlat} outside expected {ds['expected_bbox_lat']}"
        assert (
            ds["expected_bbox_lon"][0] < minlon < maxlon < ds["expected_bbox_lon"][1]
        ), f"Longitude range {minlon}-{maxlon} outside expected {ds['expected_bbox_lon']}"
        if ds["has_temporal"]:
            assert result.get("tbox") is not None, "Expected tbox from PISCO dataset"

    def test_dataone_search_url_extraction(self):
        """DataONE search.dataone.org URL: metadata extraction."""
        try:
            result = geoextent.from_remote(
                "https://search.dataone.org/view/doi%3A10.5063%2FF1Z60M87",
                bbox=True,
                tbox=False,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or DataONE CN unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"DataONE CN unreachable: {e}")
            raise

        assert result is not None
        assert result.get("bbox") is not None, "Expected bbox from search URL"

    def test_dataone_tbox_only(self):
        """Temporal-only extraction from DataONE."""
        ds = self.TEST_DATASETS["knb_alaska_elevation"]
        try:
            result = geoextent.from_remote(
                ds["doi"],
                bbox=False,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or DataONE CN unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"DataONE CN unreachable: {e}")
            raise

        assert result is not None
        tbox = result.get("tbox")
        assert tbox is not None, "Expected temporal extent from DataONE metadata"
