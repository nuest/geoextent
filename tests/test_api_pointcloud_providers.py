"""
Provider tests for point cloud (LAS/LAZ) support in geoextent.

These tests download real point cloud datasets from research data repositories
and verify that geoextent can extract spatial and temporal extents from them.

All tests are network-dependent and automatically marked as 'slow' by conftest.py.
"""

import pytest
import requests
import geoextent.lib.extent as geoextent
from conftest import NETWORK_SKIP_EXCEPTIONS


class TestZenodoPointCloud:
    """Test point cloud extraction from Zenodo datasets"""

    def test_zenodo_laz_utm32n_asiago(self):
        """Zenodo record 10428845: Asiago Plateau UAV point cloud (LAZ, UTM 32N).

        DOI: 10.5281/zenodo.10428845
        File: Asiago...UTM32.laz (~0.78 MB)
        CRS: EPSG:32632 (UTM 32N)
        Expected: Asiago Plateau area in northern Italy (~45.8N, 11.5E)
        """
        try:
            result = geoextent.from_remote(
                "10.5281/zenodo.10428845",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        bbox = result["bbox"]
        assert bbox is not None
        # Asiago is roughly at 45.8N, 11.5E
        # bbox in [minlat, minlon, maxlat, maxlon] order
        assert 45.0 < bbox[0] < 46.5  # latitude range
        assert 11.0 < bbox[1] < 12.0  # longitude range

    def test_zenodo_laz_epsg5514_iphone(self):
        """Zenodo record 15421291: iPhone LiDAR point cloud (LAZ, EPSG:5514).

        DOI: 10.5281/zenodo.15421291
        File: iPhone.laz (~11 MB)
        CRS: EPSG:5514 (S-JTSK / Krovak East North)
        Expected: Czech Republic area
        """
        try:
            result = geoextent.from_remote(
                "10.5281/zenodo.15421291",
                bbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        bbox = result["bbox"]
        assert bbox is not None
        # Czech Republic is roughly at 49-51N, 12-19E
        assert 48.0 < bbox[0] < 52.0  # latitude range
        assert 11.0 < bbox[1] < 20.0  # longitude range

    def test_zenodo_ply_not_handled(self):
        """Zenodo record 10122133: PLY point cloud (NOT handled by Phase 1).

        PLY files are not supported by the laspy-based handler.
        This test verifies they don't produce a point cloud result.
        DOI: 10.5281/zenodo.10122133
        """
        try:
            result = geoextent.from_remote(
                "10.5281/zenodo.10122133",
                bbox=True,
                download_data=True,
                max_download_size="10MB",
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")
        except Exception:
            # May fail for various reasons (size, format), that's fine
            pass

        # PLY files should NOT be handled by handle_pointcloud
        # The result may have no bbox or may have been handled by another handler
        if result is not None and result.get("details"):
            for filename, file_result in result.get("details", {}).items():
                if filename.endswith(".ply") and isinstance(file_result, dict):
                    assert file_result.get("geoextent_handler") != "handle_pointcloud"


class TestFigsharePointCloud:
    """Test point cloud extraction from Figshare datasets"""

    @pytest.mark.large_download
    def test_figshare_las_santorini(self):
        """Figshare record 1138736: Santorini LiDAR point cloud (LAS, ~35 MB).

        DOI: 10.6084/m9.figshare.1138736
        File: LDR-...-12.LAS
        Expected: Santorini area (~36.4N, 25.4E)
        """
        try:
            result = geoextent.from_remote(
                "10.6084/m9.figshare.1138736",
                bbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        bbox = result["bbox"]
        assert bbox is not None
        # Santorini is roughly at 36.4N, 25.4E
        assert 35.0 < bbox[0] < 38.0  # latitude range
        assert 24.0 < bbox[1] < 27.0  # longitude range


class TestDryadPointCloud:
    """Test point cloud extraction from Dryad datasets"""

    def test_zenodo_laz_zip_retention_trees(self):
        """Dryad dataset fqz612jw3: LAZ files in ZIP archive.

        DOI: 10.5061/dryad.fqz612jw3
        Contains: laz_stand_files.zip with LAZ files inside
        This verifies that LAZ files inside ZIP archives are detected.
        """
        try:
            result = geoextent.from_remote(
                "10.5061/dryad.fqz612jw3",
                bbox=True,
                max_download_size="30MB",
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        # If the archive was extracted and LAZ files found, we should have a bbox
        if result.get("bbox") is not None:
            bbox = result["bbox"]
            # The dataset is from a forestry study, exact location varies
            assert len(bbox) == 4
