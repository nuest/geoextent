import pytest
import geoextent.lib.extent as geoextent
from conftest import NETWORK_SKIP_EXCEPTIONS


class TestGenericCKANProvider:
    """Test generic CKAN content provider for arbitrary CKAN instances."""

    # ------------------------------------------------------------------ #
    # Test datasets from various CKAN instances
    # ------------------------------------------------------------------ #

    TEST_DATASETS = {
        "geokur_cropland": {
            "url": "https://geokur-dmp.geo.tu-dresden.de/dataset/cropland-extent",
            "dataset_id": "cropland-extent",
            "host": "geokur-dmp.geo.tu-dresden.de",
            "has_spatial": True,
            "has_temporal": True,
            "temporal_start": "2010-01-01",
            "temporal_end": "2010-12-31",
        },
        "uk_bishkek": {
            "url": "https://ckan.publishing.service.gov.uk/dataset/bishkek-spatial-data",
            "dataset_id": "bishkek-spatial-data",
            "host": "ckan.publishing.service.gov.uk",
            "has_spatial": True,
            "has_temporal": True,
            # bbox-east-long=75, bbox-west-long=74, bbox-north-lat=43, bbox-south-lat=42
            "expected_bbox_approx": {
                "west": 74.0,
                "south": 42.0,
                "east": 75.0,
                "north": 43.0,
            },
        },
        "govdata_rhine": {
            "url": "https://ckan.govdata.de/dataset/a-spatially-distributed-sampling-of-rhine-surface-water-for-non-target-screening",
            "dataset_id": "a-spatially-distributed-sampling-of-rhine-surface-water-for-non-target-screening",
            "host": "ckan.govdata.de",
            "has_spatial": True,
            "has_temporal": True,
            "temporal_start": "2017-03-21",
            "temporal_end": "2017-10-03",
        },
        "ireland_libraries": {
            "url": "https://data.gov.ie/dataset/libraries-dlr",
            "dataset_id": "libraries-dlr",
            "host": "data.gov.ie",
            "has_spatial": False,  # No spatial metadata in catalogue
            "has_temporal": False,
            # Data download: Shapefile with 8 library Point features near Dublin
            # bbox (internal lon/lat): [-6.25, 53.23, -6.10, 53.30]
            # bbox (output EPSG:4326): [53.23, -6.25, 53.30, -6.10]
            "expected_bbox_approx": {
                "west": -6.3,
                "south": 53.2,
                "east": -6.0,
                "north": 53.4,
            },
        },
        "australia_gisborne": {
            "url": "https://data.gov.au/dataset/gisborne-neighbourhood-character-precincts",
            "dataset_id": "gisborne-neighbourhood-character-precincts",
            "host": "data.gov.au",
            "has_spatial": True,
            "has_temporal": False,
            # Data download: GeoJSON with 34 MultiPolygon features near Melbourne
            # bbox (internal lon/lat): [144.57, -37.51, 144.62, -37.46]
            # bbox (output EPSG:4326): [-37.51, 144.57, -37.46, 144.62]
            "expected_bbox_approx": {
                "west": 144.5,
                "south": -37.6,
                "east": 144.7,
                "north": -37.4,
            },
        },
    }

    # ------------------------------------------------------------------ #
    # Fast validation tests (no network calls)
    # ------------------------------------------------------------------ #

    def test_ckan_url_validation(self):
        """Test that CKAN provider correctly validates URL patterns."""
        from geoextent.lib.content_providers.CKAN import CKAN

        provider = CKAN()
        assert provider.validate_provider(
            "https://geokur-dmp.geo.tu-dresden.de/dataset/cropland-extent"
        )
        assert provider.dataset_id == "cropland-extent"

    def test_ckan_known_host_validation(self):
        """Test that known CKAN hosts are matched without API probe."""
        from geoextent.lib.content_providers.CKAN import CKAN, _KNOWN_CKAN_HOSTS

        for host in _KNOWN_CKAN_HOSTS:
            provider = CKAN()
            assert provider.validate_provider(
                f"https://{host}/dataset/test-dataset"
            ), f"Known host not matched: {host}"

    def test_ckan_rejects_senckenberg(self):
        """Test that Senckenberg host is excluded from generic CKAN matching."""
        from geoextent.lib.content_providers.CKAN import CKAN

        provider = CKAN()
        assert not provider.validate_provider(
            "https://dataportal.senckenberg.de/dataset/as-sahabi-1"
        )

    def test_ckan_rejects_non_dataset_url(self):
        """Test that non-dataset URLs are rejected."""
        from geoextent.lib.content_providers.CKAN import CKAN

        provider = CKAN()
        assert not provider.validate_provider("https://example.com/not-a-dataset")
        assert not provider.validate_provider("https://example.com/organization/test")

    def test_ckan_invalid_identifiers(self):
        """Test that various invalid identifiers are rejected."""
        from geoextent.lib.content_providers.CKAN import CKAN

        invalid_refs = [
            "",
            "not-a-url",
            "https://example.com/",
            "10.1234/something",
            "just-a-slug",
        ]
        for ref in invalid_refs:
            provider = CKAN()
            assert not provider.validate_provider(ref), f"Should reject: {ref!r}"

    def test_ckan_provider_can_be_used(self):
        """Test that CKAN provider can be instantiated and inherits CKANProvider."""
        from geoextent.lib.content_providers.CKAN import CKAN
        from geoextent.lib.content_providers.CKANProvider import CKANProvider

        provider = CKAN()
        assert isinstance(provider, CKANProvider)
        assert hasattr(provider, "validate_provider")
        assert hasattr(provider, "download")

    def test_ckan_supports_metadata_extraction(self):
        """Test that CKAN provider reports metadata extraction support."""
        from geoextent.lib.content_providers.CKAN import CKAN

        provider = CKAN()
        assert provider.supports_metadata_extraction

    def test_ckan_sets_dynamic_host(self):
        """Test that self.host is set dynamically from the URL."""
        from geoextent.lib.content_providers.CKAN import CKAN

        provider = CKAN()
        provider.validate_provider(
            "https://geokur-dmp.geo.tu-dresden.de/dataset/cropland-extent"
        )
        assert provider.host is not None
        assert "api" in provider.host
        assert "geokur-dmp.geo.tu-dresden.de" in provider.host["api"]

    def test_ckan_subpath_url(self):
        """Test that URLs with subpaths (e.g., /data/dataset/) are handled."""
        from geoextent.lib.content_providers.CKAN import CKAN

        provider = CKAN()
        # open.canada.ca uses /data/en/dataset/ or /data/dataset/
        assert provider.validate_provider(
            "https://open.canada.ca/data/en/dataset/test-dataset"
        )
        assert provider.dataset_id == "test-dataset"
        assert "/data/en/" in provider.host["api"] or "/data/" in provider.host["api"]

    # ------------------------------------------------------------------ #
    # Network tests (auto-marked slow by conftest)
    # ------------------------------------------------------------------ #

    def test_ckan_metadata_only_extraction(self):
        """Provider sample: metadata-only extraction from GeoKur CKAN instance."""
        dataset = self.TEST_DATASETS["geokur_cropland"]
        try:
            result = geoextent.fromRemote(
                dataset["url"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result.get("format") == "remote"

        # GeoKur cropland-extent has spatial metadata (global extent)
        assert "bbox" in result, "Should extract spatial extent from CKAN metadata"
        bbox = result["bbox"]
        assert len(bbox) == 4

        # Verify temporal extent
        if dataset["has_temporal"]:
            assert "tbox" in result, "Should extract temporal extent from CKAN metadata"

    def test_ckan_uk_metadata_extraction(self):
        """Test metadata extraction from UK data.gov.uk CKAN instance."""
        dataset = self.TEST_DATASETS["uk_bishkek"]
        try:
            result = geoextent.fromRemote(
                dataset["url"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result.get("format") == "remote"

        # UK instance uses bbox-* extras pattern
        if "bbox" in result:
            bbox = result["bbox"]
            assert len(bbox) == 4
            expected = dataset["expected_bbox_approx"]
            # bbox is [minlat, minlon, maxlat, maxlon] in output (EPSG:4326 native)
            assert bbox[0] == pytest.approx(
                expected["south"], abs=1.0
            ), f"South mismatch: {bbox}"
            assert bbox[1] == pytest.approx(
                expected["west"], abs=1.0
            ), f"West mismatch: {bbox}"
            assert bbox[2] == pytest.approx(
                expected["north"], abs=1.0
            ), f"North mismatch: {bbox}"
            assert bbox[3] == pytest.approx(
                expected["east"], abs=1.0
            ), f"East mismatch: {bbox}"

    def test_ckan_govdata_metadata_extraction(self):
        """Test metadata extraction from German GovData CKAN instance."""
        dataset = self.TEST_DATASETS["govdata_rhine"]
        try:
            result = geoextent.fromRemote(
                dataset["url"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result.get("format") == "remote"

        # GovData uses top-level spatial GeoJSON field
        assert "bbox" in result, "Should extract spatial extent from GovData metadata"
        bbox = result["bbox"]
        assert len(bbox) == 4

        # Rhine region should be roughly in Germany
        # bbox output is [minlat, minlon, maxlat, maxlon]
        assert bbox[0] == pytest.approx(
            50.0, abs=5.0
        ), f"South latitude out of range: {bbox}"
        assert bbox[1] == pytest.approx(
            7.5, abs=2.5
        ), f"West longitude out of range: {bbox}"

    def test_ckan_dynamic_host_discovery(self):
        """Test that the API probe can verify a CKAN instance."""
        from geoextent.lib.content_providers.CKAN import CKAN

        provider = CKAN()
        try:
            # Probe a known CKAN host to verify the mechanism works
            assert provider._is_ckan_instance(
                "geokur-dmp.geo.tu-dresden.de",
                "https://geokur-dmp.geo.tu-dresden.de",
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_ckan_ireland_data_download(self):
        """Test data download from data.gov.ie CKAN instance (Shapefile with Points)."""
        dataset = self.TEST_DATASETS["ireland_libraries"]
        try:
            result = geoextent.fromRemote(
                dataset["url"],
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result.get("format") == "remote"

        # Should extract bbox from downloaded Shapefile (8 library locations near Dublin)
        assert "bbox" in result, "Should extract spatial extent from downloaded data"
        bbox = result["bbox"]
        assert len(bbox) == 4
        expected = dataset["expected_bbox_approx"]
        # bbox output is [minlat, minlon, maxlat, maxlon] (EPSG:4326 native)
        assert (
            expected["south"] < bbox[0] < expected["north"]
        ), f"South latitude: {bbox}"
        assert expected["west"] < bbox[1] < expected["east"], f"West longitude: {bbox}"
        assert (
            expected["south"] < bbox[2] < expected["north"]
        ), f"North latitude: {bbox}"
        assert expected["west"] < bbox[3] < expected["east"], f"East longitude: {bbox}"

    def test_ckan_australia_data_download(self):
        """Test data download from data.gov.au CKAN instance (GeoJSON with MultiPolygons)."""
        dataset = self.TEST_DATASETS["australia_gisborne"]
        try:
            result = geoextent.fromRemote(
                dataset["url"],
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result.get("format") == "remote"

        # Should extract bbox from downloaded GeoJSON (34 MultiPolygon features near Melbourne)
        assert "bbox" in result, "Should extract spatial extent from downloaded data"
        bbox = result["bbox"]
        assert len(bbox) == 4
        expected = dataset["expected_bbox_approx"]
        # bbox output is [minlat, minlon, maxlat, maxlon] (EPSG:4326 native)
        assert (
            expected["south"] < bbox[0] < expected["north"]
        ), f"South latitude: {bbox}"
        assert expected["west"] < bbox[1] < expected["east"], f"West longitude: {bbox}"
        assert (
            expected["south"] < bbox[2] < expected["north"]
        ), f"North latitude: {bbox}"
        assert expected["west"] < bbox[3] < expected["east"], f"East longitude: {bbox}"

    def test_ckan_geokur_spatial_metadata_api(self):
        """Test spatial metadata extraction via provider API."""
        from geoextent.lib.content_providers.CKAN import CKAN

        provider = CKAN()
        dataset = self.TEST_DATASETS["geokur_cropland"]

        try:
            assert provider.validate_provider(dataset["url"])
            spatial = provider._extract_spatial_metadata()
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert spatial is not None, "Should extract spatial metadata"
        assert "bbox" in spatial
        assert "crs" in spatial
        assert spatial["crs"] == "4326"
        # GeoKur cropland-extent has a MultiPolygon — geometry should be preserved
        assert "geometry" in spatial, "Original GeoJSON geometry should be preserved"
        assert spatial["geometry"]["type"] in (
            "Polygon",
            "MultiPolygon",
        ), f"Unexpected geometry type: {spatial['geometry']['type']}"

    def test_ckan_geokur_temporal_metadata_api(self):
        """Test temporal metadata extraction via provider API."""
        from geoextent.lib.content_providers.CKAN import CKAN

        provider = CKAN()
        dataset = self.TEST_DATASETS["geokur_cropland"]

        try:
            assert provider.validate_provider(dataset["url"])
            temporal = provider._extract_temporal_metadata()
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert temporal is not None, "Should extract temporal metadata"
        assert isinstance(temporal, list)
        assert len(temporal) == 2
        assert temporal[0] == dataset["temporal_start"]
        assert temporal[1] == dataset["temporal_end"]
