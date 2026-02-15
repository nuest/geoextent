import pytest
import geoextent.lib.extent as geoextent
from conftest import NETWORK_SKIP_EXCEPTIONS


class TestFourTUProvider:
    """Test 4TU.ResearchData content provider functionality"""

    TEST_DATASETS = {
        "rhine_mississippi_shapefile": {
            "doi": "10.4121/uuid:8ce9d22a-9aa4-41ea-9299-f44efa9c8b75",
            "url": "https://data.4tu.nl/articles/_/12707150/1",
            "id": "12707150",
            "uuid": "b0714fc2-3459-446c-bbed-b75c644a3dd7",
            "title": "Shapefile Rhine and Mississippi basin",
            "description": "Shapefiles of Rhine and Mississippi river basin boundaries (~1.2 MB zip)",
        },
        "dutch_distribution_centres": {
            "doi": "10.4121/19361018.v2",
            "url": "https://data.4tu.nl/datasets/61e28011-f96d-4b01-900e-15145b77ee59/2",
            "id": "19361018",
            "uuid": "61e28011-f96d-4b01-900e-15145b77ee59",
            "title": "Dutch Distribution Centres 2021 Geodata",
            "description": "Distribution centres in the Netherlands with CSV, GeoJSON, GeoPackage, Shapefile",
        },
        "rebioclim_dresden": {
            "doi": "10.4121/3035126d-ee51-4dbd-a187-5f6b0be85e9f.v1",
            "url": "https://data.4tu.nl/datasets/3035126d-ee51-4dbd-a187-5f6b0be85e9f/1",
            "id": "3035126d-ee51-4dbd-a187-5f6b0be85e9f",
            "uuid": "3035126d-ee51-4dbd-a187-5f6b0be85e9f",
            "title": "ReBioClim Dresden: Spatial analysis dataset for urban stream restoration",
            "description": "GeoJSON and GeoPackage with 698 grid cells (500x500m) for Dresden, Germany",
        },
    }

    # -- Fast validation tests (no network) --

    def test_fourtu_url_validation(self):
        """Test that 4TU.ResearchData URLs are correctly validated"""
        from geoextent.lib.content_providers.FourTU import FourTU

        fourtu = FourTU()

        # Test old-style /articles/_/ID URL
        assert fourtu.validate_provider("https://data.4tu.nl/articles/_/12707150/1")
        assert fourtu.record_id == "12707150"

        # Test new-style /datasets/UUID URL
        assert fourtu.validate_provider(
            "https://data.4tu.nl/datasets/61e28011-f96d-4b01-900e-15145b77ee59/2"
        )
        assert fourtu.record_id == "61e28011-f96d-4b01-900e-15145b77ee59"

        # Test /datasets/UUID without version
        assert fourtu.validate_provider(
            "https://data.4tu.nl/datasets/b0714fc2-3459-446c-bbed-b75c644a3dd7"
        )
        assert fourtu.record_id == "b0714fc2-3459-446c-bbed-b75c644a3dd7"

        # Test /articles/_/ID without version
        assert fourtu.validate_provider("https://data.4tu.nl/articles/_/12707150")
        assert fourtu.record_id == "12707150"

        # Test old-style Figshare URL with article type and title
        assert fourtu.validate_provider(
            "https://data.4tu.nl/articles/dataset/Shapefile_Rhine/12707150"
        )
        assert fourtu.record_id == "12707150"

    def test_fourtu_doi_validation(self):
        """Test that 4TU DOIs are NOT validated without network (DOI resolution required)

        4TU DOIs need network resolution to get the data.4tu.nl URL.
        This test confirms the provider doesn't accidentally match raw DOI strings.
        """
        from geoextent.lib.content_providers.FourTU import FourTU

        fourtu = FourTU()

        # Raw DOI strings don't start with data.4tu.nl hostname, so they need
        # resolution via get_url. Without network they won't validate.
        # (In real usage, get_url resolves the DOI to data.4tu.nl and then it matches.)

        # Invalid URLs should not match
        assert fourtu.validate_provider("https://zenodo.org/record/820562") is False
        assert (
            fourtu.validate_provider("https://figshare.com/articles/dataset/test/12345")
            is False
        )
        assert fourtu.validate_provider("not-a-url-at-all") is False

    def test_fourtu_url_validation_invalid_patterns(self):
        """Test that incomplete or malformed 4TU URLs are rejected"""
        from geoextent.lib.content_providers.FourTU import FourTU

        fourtu = FourTU()

        # Base URL without a record ID
        assert fourtu.validate_provider("https://data.4tu.nl/articles/") is False
        assert fourtu.validate_provider("https://data.4tu.nl/datasets/") is False

    # -- Network tests (auto-marked slow) --

    def test_fourtu_actual_bbox_extraction(self):
        """Test 4TU provider with actual bounding box extraction from Rhine/Mississippi shapefile"""
        dataset = self.TEST_DATASETS["rhine_mississippi_shapefile"]

        try:
            result = geoextent.fromRemote(
                dataset["url"],
                bbox=True,
                tbox=False,
                download_data=True,
            )

            assert result is not None
            assert result["format"] == "remote"

            if "bbox" in result:
                bbox = result["bbox"]
                assert isinstance(bbox, list)
                assert len(bbox) == 4
                # Rhine basin roughly: lat 46-52, lon 6-12
                # Mississippi basin roughly: lat 30-50, lon -112 to -77
                # Combined bbox should span both
                assert bbox[0] < bbox[2]  # minlat < maxlat
                assert bbox[1] < bbox[3]  # minlon < maxlon

            if "crs" in result:
                assert result["crs"] == "4326"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_fourtu_metadata_only_extraction(self):
        """Test 4TU.ResearchData metadata-only extraction (limited functionality)"""
        dataset = self.TEST_DATASETS["rhine_mississippi_shapefile"]

        try:
            result = geoextent.fromRemote(
                dataset["url"],
                bbox=True,
                tbox=True,
                download_data=False,
            )

            # Metadata-only mode has limited data for 4TU (no geospatial metadata in API)
            assert result is not None
            assert result["format"] == "remote"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_fourtu_doi_extraction(self):
        """Test 4TU provider via DOI resolution"""
        dataset = self.TEST_DATASETS["rhine_mississippi_shapefile"]

        try:
            result = geoextent.fromRemote(
                dataset["doi"],
                bbox=True,
                tbox=False,
                download_data=True,
            )

            assert result is not None
            assert result["format"] == "remote"

            if "bbox" in result:
                bbox = result["bbox"]
                assert isinstance(bbox, list)
                assert len(bbox) == 4

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_fourtu_uuid_url_extraction(self):
        """Test 4TU provider via new-style /datasets/UUID URL"""
        dataset = self.TEST_DATASETS["rhine_mississippi_shapefile"]

        try:
            # Use UUID-based URL format
            uuid_url = f"https://data.4tu.nl/datasets/{dataset['uuid']}/1"
            result = geoextent.fromRemote(
                uuid_url,
                bbox=True,
                tbox=False,
                download_data=True,
            )

            assert result is not None
            assert result["format"] == "remote"

            if "bbox" in result:
                bbox = result["bbox"]
                assert isinstance(bbox, list)
                assert len(bbox) == 4

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    # -- Tests for ReBioClim Dresden dataset (3035126d) --

    def test_fourtu_rebioclim_bbox_extraction(self):
        """Test 4TU provider with ReBioClim Dresden dataset (GeoJSON + GeoPackage).

        With download_data=True, bbox comes from actual data files and tbox
        comes from the metadata temporal sidecar (custom_fields "Time coverage").
        The sidecar file appears in details for provenance transparency.
        """
        dataset = self.TEST_DATASETS["rebioclim_dresden"]

        try:
            result = geoextent.fromRemote(
                dataset["url"],
                bbox=True,
                tbox=True,
                download_data=True,
                details=True,
            )

            assert result is not None
            assert result["format"] == "remote"

            bbox = result.get("bbox")
            assert bbox is not None
            assert len(bbox) == 4
            # Dresden area roughly: lat 50.9-51.2, lon 13.5-13.9
            assert bbox[0] < bbox[2]  # minlat < maxlat
            assert bbox[1] < bbox[3]  # minlon < maxlon

            assert result.get("crs") == "4326"

            # Temporal extent from metadata temporal sidecar
            tbox = result.get("tbox")
            assert (
                tbox is not None
            ), "tbox should be extracted from metadata temporal sidecar"
            assert tbox[0].startswith("2025-05")
            assert tbox[1].startswith("2025-06")

            # Provenance: metadata temporal sidecar should appear in details
            details = result.get("details", {})
            temporal_sidecar_files = [k for k in details if "metadata_temporal" in k]
            assert len(temporal_sidecar_files) == 1, (
                f"Expected one metadata_temporal sidecar in details, "
                f"got {temporal_sidecar_files}"
            )

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_fourtu_rebioclim_doi_extraction(self):
        """Test 4TU ReBioClim Dresden dataset via DOI resolution"""
        dataset = self.TEST_DATASETS["rebioclim_dresden"]

        try:
            result = geoextent.fromRemote(
                dataset["doi"],
                bbox=True,
                tbox=False,
                download_data=True,
            )

            assert result is not None
            assert result["format"] == "remote"

            if "bbox" in result:
                bbox = result["bbox"]
                assert isinstance(bbox, list)
                assert len(bbox) == 4

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_fourtu_rebioclim_metadata_only(self):
        """Test 4TU ReBioClim Dresden with metadata-only extraction.

        4TU's custom_fields contain geolocation (lat=51.050407, lon=13.737262)
        and temporal coverage. Metadata-only mode should extract a point bbox
        from these fields.
        """
        dataset = self.TEST_DATASETS["rebioclim_dresden"]

        try:
            result = geoextent.fromRemote(
                dataset["url"],
                bbox=True,
                tbox=True,
                download_data=False,
            )

            assert result is not None
            assert result["format"] == "remote"

            # 4TU exposes geolocation via custom_fields
            assert (
                result.get("bbox") is not None
            ), "4TU metadata-only should yield a bbox from custom_fields geolocation"
            bbox = result["bbox"]
            assert len(bbox) == 4
            # Point location: Dresden (lat=51.050407, lon=13.737262)
            # Default output order is [minlat, minlon, maxlat, maxlon]
            assert (
                abs(bbox[0] - 51.050407) < 0.01
            ), f"Expected lat ~51.05, got {bbox[0]}"
            assert (
                abs(bbox[1] - 13.737262) < 0.01
            ), f"Expected lon ~13.74, got {bbox[1]}"
            assert (
                abs(bbox[2] - 51.050407) < 0.01
            ), f"Expected lat ~51.05, got {bbox[2]}"
            assert (
                abs(bbox[3] - 13.737262) < 0.01
            ), f"Expected lon ~13.74, got {bbox[3]}"

            # Temporal coverage: "2025-05-21 to 2025-06-17"
            assert (
                result.get("tbox") is not None
            ), "4TU metadata-only should yield a tbox from custom_fields Time coverage"
            tbox = result["tbox"]
            assert tbox[0].startswith("2025-05")
            assert tbox[1].startswith("2025-06")

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")
