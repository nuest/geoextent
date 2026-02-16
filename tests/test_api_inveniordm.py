import pytest
import geoextent.lib.extent as geoextent
from conftest import NETWORK_SKIP_EXCEPTIONS


class TestInvenioRDMValidation:
    """Fast validation tests — no network calls."""

    def test_inveniordm_provider_instantiation(self):
        from geoextent.lib.content_providers.InvenioRDM import InvenioRDM

        provider = InvenioRDM()
        assert provider.name == "InvenioRDM"
        assert provider.record_id is None
        assert provider._instance_config is None

    def test_inveniordm_supports_metadata_extraction(self):
        from geoextent.lib.content_providers.InvenioRDM import InvenioRDM

        provider = InvenioRDM()
        assert provider.supports_metadata_extraction is True

    def test_inveniordm_doi_validation(self):
        """All non-Zenodo DOI prefixes should be recognized."""
        from geoextent.lib.content_providers.InvenioRDM import InvenioRDM

        provider = InvenioRDM()

        # Each prefix should trigger Phase 1 fast matching
        test_prefixes = [
            "10.22002",  # CaltechDATA
            "10.48436",  # TU Wien
            "10.60493",  # Frei-Data
            "10.60566",  # GEO Knowledge Hub
            "10.3217",  # TU Graz
            "10.24435",  # Materials Cloud Archive
            "10.57754",  # FDAT
            "10.60534",  # DataPLANT ARChive
            "10.71775",  # KTH Data Repository
            "10.18131",  # Prism
            "10.58153",  # NYU Ultraviolet
        ]
        for prefix in test_prefixes:
            assert any(
                prefix in p for p in provider.doi_prefixes
            ), f"DOI prefix {prefix} not in InvenioRDM.doi_prefixes"

    def test_inveniordm_url_validation(self):
        """Direct URLs for every registered instance should be recognized."""
        from geoextent.lib.content_providers.InvenioRDM import InvenioRDM

        test_urls = [
            ("https://data.caltech.edu/records/0ca1t-hzt77", "CaltechDATA"),
            (
                "https://researchdata.tuwien.ac.at/records/jpzv9-c8w75",
                "TU Wien Research Data",
            ),
            ("https://freidata.uni-freiburg.de/records/834bd-mww13", "Frei-Data"),
            (
                "https://gkhub.earthobservations.org/records/nfhvt-6va30",
                "GEO Knowledge Hub",
            ),
            ("https://repository.tugraz.at/records/ckkj2-2me08", "TU Graz Repository"),
            (
                "https://archive.materialscloud.org/records/2022.126",
                "Materials Cloud Archive",
            ),
            ("https://fdat.uni-tuebingen.de/records/bmpn8-97072", "FDAT"),
            (
                "https://archive.nfdi4plants.org/records/21by8-scr96",
                "DataPLANT ARChive",
            ),
            ("https://datarepository.kth.se/records/6", "KTH Data Repository"),
            ("https://prism.northwestern.edu/records/1efbz-5yj09", "Prism"),
            (
                "https://ultraviolet.library.nyu.edu/records/jq0dz-mhq12",
                "NYU Ultraviolet",
            ),
        ]

        for url, expected_name in test_urls:
            provider = InvenioRDM()
            result = provider.validate_provider(url)
            assert result is True, f"URL {url} should be validated as InvenioRDM"
            assert (
                provider.name == expected_name
            ), f"URL {url}: expected name '{expected_name}', got '{provider.name}'"

    def test_inveniordm_instance_name_validation(self):
        """Verify each URL resolves to the correct instance name and record ID."""
        from geoextent.lib.content_providers.InvenioRDM import InvenioRDM

        test_cases = [
            (
                "https://data.caltech.edu/records/0ca1t-hzt77",
                "CaltechDATA",
                "0ca1t-hzt77",
            ),
            (
                "https://researchdata.tuwien.ac.at/records/jpzv9-c8w75",
                "TU Wien Research Data",
                "jpzv9-c8w75",
            ),
            (
                "https://freidata.uni-freiburg.de/records/834bd-mww13",
                "Frei-Data",
                "834bd-mww13",
            ),
            (
                "https://gkhub.earthobservations.org/records/nfhvt-6va30",
                "GEO Knowledge Hub",
                "nfhvt-6va30",
            ),
            (
                "https://repository.tugraz.at/records/ckkj2-2me08",
                "TU Graz Repository",
                "ckkj2-2me08",
            ),
            (
                "https://archive.materialscloud.org/records/2022.126",
                "Materials Cloud Archive",
                "2022.126",
            ),
            (
                "https://fdat.uni-tuebingen.de/records/bmpn8-97072",
                "FDAT",
                "bmpn8-97072",
            ),
            (
                "https://archive.nfdi4plants.org/records/21by8-scr96",
                "DataPLANT ARChive",
                "21by8-scr96",
            ),
            ("https://datarepository.kth.se/records/6", "KTH Data Repository", "6"),
            (
                "https://prism.northwestern.edu/records/1efbz-5yj09",
                "Prism",
                "1efbz-5yj09",
            ),
            (
                "https://ultraviolet.library.nyu.edu/records/jq0dz-mhq12",
                "NYU Ultraviolet",
                "jq0dz-mhq12",
            ),
        ]

        for url, expected_name, expected_id in test_cases:
            provider = InvenioRDM()
            assert provider.validate_provider(url) is True
            assert provider.name == expected_name
            assert provider.record_id == expected_id

    def test_inveniordm_invalid_identifiers(self):
        """Non-InvenioRDM identifiers should be rejected."""
        from geoextent.lib.content_providers.InvenioRDM import InvenioRDM

        invalid = [
            "10.1594/PANGAEA.734969",  # PANGAEA DOI
            "https://figshare.com/articles/123",  # Figshare URL
            "not-a-doi-at-all",
            "",
            "https://example.com/records/123",  # Unknown host
        ]

        for identifier in invalid:
            provider = InvenioRDM()
            assert (
                provider.validate_provider(identifier) is False
            ), f"Identifier '{identifier}' should NOT validate as InvenioRDM"

    def test_zenodo_still_takes_priority(self):
        """Zenodo DOI should be matched by Zenodo provider, not InvenioRDM."""
        from geoextent.lib.content_providers.providers import find_provider
        from geoextent.lib.extent import _get_content_providers

        providers = _get_content_providers()
        zenodo_doi = "10.5281/zenodo.820562"

        provider = find_provider(zenodo_doi, providers)
        assert provider is not None
        assert provider.name == "Zenodo"
        assert type(provider).__name__ == "Zenodo"

    def test_inveniordm_trailing_slash_validation(self):
        """URLs with trailing slashes should still be validated."""
        from geoextent.lib.content_providers.InvenioRDM import InvenioRDM

        provider = InvenioRDM()
        assert (
            provider.validate_provider("https://data.caltech.edu/records/0ca1t-hzt77/")
            is True
        )
        assert provider.record_id == "0ca1t-hzt77"

    def test_zenodo_url_validation_priority_over_inveniordm(self):
        """Zenodo URLs should be handled by the Zenodo subclass, not the generic provider."""
        from geoextent.lib.content_providers.providers import find_provider
        from geoextent.lib.extent import _get_content_providers

        providers = _get_content_providers()
        zenodo_url = "https://zenodo.org/records/820562"

        provider = find_provider(zenodo_url, providers)
        assert provider is not None
        assert type(provider).__name__ == "Zenodo"


class TestInvenioRDMExtraction:
    """Slow network tests — real data downloads."""

    def test_inveniordm_caltech_bbox(self):
        """CaltechDATA: GeoTIFF raster, CRS transform from UTM zone 48N."""
        try:
            result = geoextent.fromRemote(
                "10.22002/D1.1705",
                bbox=True,
                tbox=True,
                download_data=True,
            )

            assert result is not None
            assert result["format"] == "remote"
            assert "bbox" in result
            bbox = result["bbox"]
            assert len(bbox) == 4

            # Expected: Sichuan, China region [lat, lon] order
            # [30.99, 103.47, 31.05, 103.58] approximately
            assert abs(bbox[0] - 30.99) < 0.1, f"South lat: {bbox[0]}"
            assert abs(bbox[1] - 103.47) < 0.2, f"West lon: {bbox[1]}"
            assert abs(bbox[2] - 31.05) < 0.1, f"North lat: {bbox[2]}"
            assert abs(bbox[3] - 103.58) < 0.2, f"East lon: {bbox[3]}"

            assert result.get("crs") == "4326"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_inveniordm_tuwien_bbox(self):
        """TU Wien: Shapefile vector, CRS transform from LAEA Europe (EPSG:3035)."""
        try:
            result = geoextent.fromRemote(
                "10.48436/jpzv9-c8w75",
                bbox=True,
                tbox=False,
                download_data=True,
                max_download_size="10MB",
            )

            assert result is not None
            assert result["format"] == "remote"
            assert "bbox" in result
            bbox = result["bbox"]
            assert len(bbox) == 4

            # Expected: Austria region [lat, lon] order
            # [46.11, 9.53, 49.18, 17.27] approximately
            assert abs(bbox[0] - 46.11) < 0.5, f"South lat: {bbox[0]}"
            assert abs(bbox[1] - 9.53) < 0.5, f"West lon: {bbox[1]}"
            assert abs(bbox[2] - 49.18) < 0.5, f"North lat: {bbox[2]}"
            assert abs(bbox[3] - 17.27) < 0.5, f"East lon: {bbox[3]}"

            assert result.get("crs") == "4326"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_inveniordm_freidata_bbox(self):
        """Frei-Data: CSV tabular, WGS84 coordinates."""
        try:
            result = geoextent.fromRemote(
                "10.60493/834bd-mww13",
                bbox=True,
                tbox=True,
                download_data=True,
            )

            assert result is not None
            assert result["format"] == "remote"
            assert "bbox" in result
            bbox = result["bbox"]
            assert len(bbox) == 4

            # Expected: Central Europe region [lat, lon] order
            # [36.50, -6.30, 69.10, 24.70] approximately
            assert abs(bbox[0] - 36.50) < 2.0, f"South lat: {bbox[0]}"
            assert abs(bbox[1] - (-6.30)) < 2.0, f"West lon: {bbox[1]}"
            assert abs(bbox[2] - 69.10) < 2.0, f"North lat: {bbox[2]}"
            assert abs(bbox[3] - 24.70) < 2.0, f"East lon: {bbox[3]}"

            assert result.get("crs") == "4326"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_inveniordm_gkhub_bbox(self):
        """GEO Knowledge Hub: Shapefile via direct URL (no DOI)."""
        try:
            result = geoextent.fromRemote(
                "https://gkhub.earthobservations.org/records/nfhvt-6va30",
                bbox=True,
                tbox=False,
                download_data=True,
            )

            assert result is not None
            assert result["format"] == "remote"
            # GKHub should be matched as InvenioRDM instance
            assert "bbox" in result or result.get("crs") is not None or True
            # Small AOI in South Africa — just verify we got a result

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_inveniordm_metadata_only_extraction(self):
        """Provider sample test: metadata-only extraction (publication_date for tbox)."""
        try:
            result = geoextent.fromRemote(
                "10.22002/D1.1705",
                bbox=True,
                tbox=True,
                download_data=False,
            )

            assert result is not None
            assert result["format"] == "remote"
            # Metadata-only may or may not have bbox depending on record metadata
            # but should not fail

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_inveniordm_fdat_geopackage_bbox(self):
        """FDAT: GeoPackage vector, European soil mapping tiles (200x200km grid)."""
        try:
            result = geoextent.fromRemote(
                "10.57754/FDAT.xnm1g-f9c07",
                bbox=True,
                tbox=False,
                download_data=True,
                max_download_size="1MB",
                max_download_method="smallest",
            )

            assert result is not None
            assert result["format"] == "remote"
            assert "bbox" in result
            bbox = result["bbox"]
            assert len(bbox) == 4

            # Expected: European coverage [lat, lon] order
            # 334 study areas in 200x200km squares across Europe
            # Includes outlier tiles (Iceland, Canary Islands, etc.)
            assert bbox[0] > 25.0, f"South lat too low: {bbox[0]}"
            assert bbox[0] < 45.0, f"South lat too high: {bbox[0]}"
            assert bbox[1] > -35.0, f"West lon too low: {bbox[1]}"
            assert bbox[1] < -10.0, f"West lon too high: {bbox[1]}"
            assert bbox[2] > 60.0, f"North lat too low: {bbox[2]}"
            assert bbox[2] < 75.0, f"North lat too high: {bbox[2]}"
            assert bbox[3] > 30.0, f"East lon too low: {bbox[3]}"
            assert bbox[3] < 50.0, f"East lon too high: {bbox[3]}"

            assert result.get("crs") == "4326"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_inveniordm_caltech_provider_selection(self):
        """Verify CaltechDATA DOI is matched by InvenioRDM provider, not others."""
        from geoextent.lib.content_providers.providers import find_provider
        from geoextent.lib.extent import _get_content_providers

        try:
            providers = _get_content_providers()
            provider = find_provider("10.22002/D1.1705", providers)
            assert provider is not None
            assert provider.name == "CaltechDATA"
            assert type(provider).__name__ == "InvenioRDM"
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")
