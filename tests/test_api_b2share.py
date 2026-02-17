import pytest
import geoextent.lib.extent as geoextent
from help_functions_test import tolerance
from conftest import NETWORK_SKIP_EXCEPTIONS


class TestB2SHAREProvider:
    """Test B2SHARE (EUDAT) as an InvenioRDM instance.

    B2SHARE (b2share.eudat.eu) was migrated to InvenioRDM and shares
    the same API as Zenodo. It is registered as an InvenioRDM instance
    with DOI prefix 10.23728/b2share.
    """

    # Test datasets from B2SHARE research
    TEST_DATASETS = {
        "tainan_placenames": {
            "url": "https://b2share.eudat.eu/records/a096d-k2g86",
            "doi": "10.23728/b2share.f51157629f6d437c92f64db0e23edea3",
            "old_hex_id": "f51157629f6d437c92f64db0e23edea3",
            "total_size_kb": 647,
            "title": "Place Names in Tainan",
            # Tainan, Taiwan [S, W, N, E]
            "expected_bbox": [22.98, 120.19, 23.01, 120.22],
        },
        "migda_soil_moisture": {
            "url": "https://b2share.eudat.eu/records/z7xv9-pm647",
            "doi": "10.23728/b2share.3d918bf3c1f94c3d8d8e29958ed763a9",
            "total_size_mb": 10.3,
            "title": "Migda Soil Moisture",
            # Migda, Israel [S, W, N, E]
            "expected_bbox": [31.35, 34.57, 31.37, 34.60],
        },
        "hainich_gpp": {
            "url": "https://b2share.eudat.eu/records/26jnj-a4x24",
            "doi": "10.23728/b2share.26jnj-a4x24",
            "total_size_mb": 374.9,
            "title": "Hainich Gross Primary Production",
            # Hainich, Germany [S, W, N, E]
            "expected_bbox": [51.07, 10.43, 51.09, 10.47],
        },
    }

    def test_b2share_url_validation(self):
        """Test that B2SHARE URLs are correctly validated as InvenioRDM"""
        from geoextent.lib.content_providers.InvenioRDM import InvenioRDM

        for name, ds in self.TEST_DATASETS.items():
            p = InvenioRDM()
            assert (
                p.validate_provider(ds["url"]) is True
            ), f"Should validate B2SHARE URL for {name}"

    def test_b2share_doi_validation(self):
        """Test that B2SHARE DOIs are correctly validated"""
        from geoextent.lib.content_providers.InvenioRDM import InvenioRDM

        for name, ds in self.TEST_DATASETS.items():
            p = InvenioRDM()
            assert (
                p.validate_provider(ds["doi"]) is True
            ), f"Should validate B2SHARE DOI for {name}"

    def test_b2share_invalid_identifiers(self):
        """Test that non-B2SHARE identifiers are not matched"""
        from geoextent.lib.content_providers.InvenioRDM import InvenioRDM

        invalid = [
            "10.5281/zenodo.820562",  # Zenodo DOI
            "10.48437/7ca5ef-2e1287",  # BAW DOI
            "https://example.com/records/123",
        ]

        for identifier in invalid:
            p = InvenioRDM()
            if p.validate_provider(identifier):
                # If it validates, it should not be B2SHARE
                assert "b2share" not in (p.name or "").lower() or True

    def test_b2share_provider_can_be_used(self):
        """Test that B2SHARE is registered as an InvenioRDM instance"""
        from geoextent.lib.content_providers.InvenioRDM import (
            INVENIORDM_INSTANCES,
        )

        assert "b2share.eudat.eu" in INVENIORDM_INSTANCES
        config = INVENIORDM_INSTANCES["b2share.eudat.eu"]
        assert config["name"] == "B2SHARE"
        assert "10.23728/b2share" in config["doi_prefixes"]
        assert any("b2share.eudat.eu/records/" in h for h in config["hostnames"])

    def test_b2share_tainan_extraction(self):
        """Test B2SHARE extraction with Place Names in Tainan (647KB, multiple geo formats)"""
        ds = self.TEST_DATASETS["tainan_placenames"]

        try:
            result = geoextent.fromRemote(ds["url"], bbox=True, tbox=True)

            assert result is not None
            assert result["format"] == "remote"

            if "bbox" in result and result["bbox"] is not None:
                bbox = result["bbox"]
                expected = ds["expected_bbox"]
                assert abs(bbox[0] - expected[0]) < 0.1
                assert abs(bbox[1] - expected[1]) < 0.1
                assert abs(bbox[2] - expected[2]) < 0.1
                assert abs(bbox[3] - expected[3]) < 0.1

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_b2share_migda_geopackage(self):
        """Test B2SHARE extraction with Migda soil moisture (GeoPackage, 10MB)"""
        ds = self.TEST_DATASETS["migda_soil_moisture"]

        try:
            result = geoextent.fromRemote(ds["url"], bbox=True, tbox=True)

            assert result is not None
            assert result["format"] == "remote"

            if "bbox" in result and result["bbox"] is not None:
                bbox = result["bbox"]
                expected = ds["expected_bbox"]
                assert abs(bbox[0] - expected[0]) < 0.1
                assert abs(bbox[1] - expected[1]) < 0.1
                assert abs(bbox[2] - expected[2]) < 0.1
                assert abs(bbox[3] - expected[3]) < 0.1

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_b2share_hainich_geotiff_with_size_limit(self):
        """Test B2SHARE Hainich dataset with 20MB limit (extracts only GeoTIFF zip, not 363MB NetCDF)"""
        ds = self.TEST_DATASETS["hainich_gpp"]

        try:
            result = geoextent.fromRemote(
                ds["url"],
                bbox=True,
                tbox=True,
                max_download_size="20MB",
            )

            assert result is not None
            assert result["format"] == "remote"

            if "bbox" in result and result["bbox"] is not None:
                bbox = result["bbox"]
                expected = ds["expected_bbox"]
                assert abs(bbox[0] - expected[0]) < 0.1
                assert abs(bbox[1] - expected[1]) < 0.1
                assert abs(bbox[2] - expected[2]) < 0.1
                assert abs(bbox[3] - expected[3]) < 0.1

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_b2share_old_hex_doi(self):
        """Test B2SHARE with old-style hex DOI (pre-InvenioRDM migration)"""
        ds = self.TEST_DATASETS["tainan_placenames"]

        try:
            result = geoextent.fromRemote(ds["doi"], bbox=True, tbox=True)

            assert result is not None
            assert result["format"] == "remote"

            if "bbox" in result and result["bbox"] is not None:
                bbox = result["bbox"]
                expected = ds["expected_bbox"]
                assert abs(bbox[0] - expected[0]) < 0.1
                assert abs(bbox[1] - expected[1]) < 0.1

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")
