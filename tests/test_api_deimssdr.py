"""Tests for DEIMS-SDR provider integration.

Tests cover:
- URL validation (no network)
- Metadata-only extraction for all 7 candidate datasets and 3 test sites
- Geometry types: POINT, POLYGON, MULTIPOLYGON
- Temporal extent handling (including null end dates)
- Edge cases: placeholder DOI text, complex polygons, ongoing datasets
- Integration with --no-metadata-fallback
- Follow delegation to external providers (Zenodo, PANGAEA, etc.)
"""

import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.content_providers.DEIMSSDR import DEIMSSDR
from conftest import NETWORK_SKIP_EXCEPTIONS

# Tolerance for coordinate comparisons
_TOL = 0.01


# --- Validation tests (no network, fast) ---


class TestDEIMSSDRValidation:
    """Fast validation tests that do not require network access."""

    def test_deimssdr_dataset_url_validation(self):
        provider = DEIMSSDR()
        assert provider.validate_provider(
            "https://deims.org/dataset/1a179105-8f6d-416c-98a4-c819006a1255"
        )
        assert provider.resource_type == "dataset"
        assert provider.resource_uuid == "1a179105-8f6d-416c-98a4-c819006a1255"

    def test_deimssdr_site_url_validation(self):
        provider = DEIMSSDR()
        assert provider.validate_provider(
            "https://deims.org/8eda49e9-1f4e-4f3e-b58e-e0bb25dc32a6"
        )
        assert provider.resource_type == "site"
        assert provider.resource_uuid == "8eda49e9-1f4e-4f3e-b58e-e0bb25dc32a6"

    def test_deimssdr_api_dataset_url_validation(self):
        provider = DEIMSSDR()
        assert provider.validate_provider(
            "https://deims.org/api/datasets/3d87da8b-2b07-41c7-bf05-417832de4fa2"
        )
        assert provider.resource_type == "dataset"

    def test_deimssdr_api_site_url_validation(self):
        provider = DEIMSSDR()
        assert provider.validate_provider(
            "https://deims.org/api/sites/8eda49e9-1f4e-4f3e-b58e-e0bb25dc32a6"
        )
        assert provider.resource_type == "site"

    def test_deimssdr_invalid_identifiers(self):
        provider = DEIMSSDR()
        assert not provider.validate_provider("https://zenodo.org/records/820562")
        assert not provider.validate_provider("10.5281/zenodo.820562")
        assert not provider.validate_provider("Q64")
        assert not provider.validate_provider("not-a-url")
        # Bare UUID without deims.org hostname should not match
        assert not provider.validate_provider("1a179105-8f6d-416c-98a4-c819006a1255")

    def test_deimssdr_supports_metadata_extraction(self):
        provider = DEIMSSDR()
        assert provider.supports_metadata_extraction is True


# --- Dataset extraction tests (network required) ---


class TestDEIMSSDRDatasets:
    """Network tests for DEIMS-SDR dataset extraction."""

    def test_deimssdr_dataset_metadata_only_extraction(self):
        """Provider sample test: Rosalia forest (Austria), POLYGON geometry."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/1a179105-8f6d-416c-98a4-c819006a1255",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert result["crs"] == "4326"
        assert "tbox" in result
        # Temporal extent may shift as upstream metadata is updated;
        # check that start is in 2019 and end is in 2021
        assert result["tbox"][0].startswith("2019")
        assert result["tbox"][1].startswith("2021")
        # Rosalia forest is in Austria (~16.3E, ~47.7N);
        # use wide tolerance since upstream data files may change
        bbox = result["bbox"]
        assert bbox[0] == pytest.approx(47.65, abs=0.15)  # minlat
        assert bbox[1] == pytest.approx(16.3, abs=0.1)  # minlon
        assert bbox[2] == pytest.approx(47.65, abs=0.15)  # maxlat
        assert bbox[3] == pytest.approx(16.3, abs=0.1)  # maxlon

    def test_deimssdr_sierra_nevada_complex_polygon(self):
        """Sierra Nevada (Spain): very complex POLYGON (~23,574 vertices)."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/9ca7a359-17b0-41f7-b81b-c6aae9268b2a",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert result["tbox"] == ["2001-01-01", "2018-01-01"]
        # Sierra Nevada is in SE Spain (~-3.6W to -2.6W, ~36.9N to 37.2N)
        bbox = result["bbox"]
        assert bbox[1] == pytest.approx(-3.1, abs=0.6)  # minlon (west)
        assert bbox[3] == pytest.approx(-3.1, abs=0.6)  # maxlon (east)
        assert bbox[0] == pytest.approx(37.0, abs=0.5)  # minlat
        assert bbox[2] == pytest.approx(37.0, abs=0.5)  # maxlat

    def test_deimssdr_lake_paione_with_zenodo_doi(self):
        """Lake Paione Superiore (Italy): POLYGON, has external Zenodo DOI."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/3d87da8b-2b07-41c7-bf05-417832de4fa2",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert result["tbox"] == ["2014-08-21", "2020-09-30"]
        # Italian Alps area (~8.19-8.22E, ~46.12-46.17N)
        bbox = result["bbox"]
        assert bbox[1] == pytest.approx(8.19, abs=0.05)  # minlon
        assert bbox[0] == pytest.approx(46.12, abs=0.05)  # minlat

    def test_deimssdr_burgas_bay_seanoe(self):
        """Burgas Bay (Bulgaria): POLYGON, external SEANOE DOI."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/f88b59ce-3716-4823-9152-985e5ff84a7a",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert result["tbox"] == ["2022-06-27", "2022-07-30"]
        # Bulgaria/Black Sea (~27.4-27.9E, ~42.3-42.7N)
        bbox = result["bbox"]
        assert bbox[1] == pytest.approx(27.44, abs=0.1)
        assert bbox[0] == pytest.approx(42.31, abs=0.1)

    def test_deimssdr_moor_house_multipolygon(self):
        """Moor House (UK): MULTIPOLYGON geometry, ongoing (end date null)."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/4f9bf89d-5ecb-41bf-970a-9c69a02cc51b",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        # Null end date -> start used as end
        assert result["tbox"] == ["1960-01-01", "1960-01-01"]
        # Moor House is in northern England (~-2.4W, ~54.7N)
        bbox = result["bbox"]
        assert bbox[1] == pytest.approx(-2.4, abs=0.5)  # minlon (west)
        assert bbox[0] == pytest.approx(54.7, abs=0.5)  # minlat

    def test_deimssdr_meteorological_station_point(self):
        """Schröckalm (Austria): POINT geometry, ongoing."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/c93f0317-8a7e-44c9-8276-f4eae114c03d",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert result["tbox"] == ["2023-03-23", "2023-03-23"]
        # Schröckalm is in Austria (~14.67E, ~47.53N)
        bbox = result["bbox"]
        assert bbox[0] == pytest.approx(47.53, abs=0.1)
        assert bbox[1] == pytest.approx(14.67, abs=0.1)

    def test_deimssdr_bird_survey_placeholder_doi(self):
        """Bird survey (Germany): POLYGON, DOI field has placeholder text."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/5244d4e4-a206-11e2-b534-005056ab003f",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        # Null end date -> start used as end
        assert result["tbox"] == ["1999-02-28", "1999-02-28"]
        # NE Germany (~13.45-13.88E, ~53.29-53.44N)
        bbox = result["bbox"]
        assert bbox[1] == pytest.approx(13.45, abs=0.1)
        assert bbox[0] == pytest.approx(53.29, abs=0.1)


# --- Site extraction tests (network required) ---


class TestDEIMSSDRSites:
    """Network tests for DEIMS-SDR site-level extraction."""

    def test_deimssdr_site_zobelboden_austria(self):
        """LTER Zobelboden (Austria): complex POLYGON boundary."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/8eda49e9-1f4e-4f3e-b58e-e0bb25dc32a6",
                bbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert result["crs"] == "4326"
        # Zobelboden is in Austria (~14.4E, ~47.8N)
        bbox = result["bbox"]
        assert bbox[1] == pytest.approx(14.44, abs=0.1)
        assert bbox[0] == pytest.approx(47.84, abs=0.1)

    def test_deimssdr_site_rosalia_austria(self):
        """Lehrforst Rosalia (Austria): very complex POLYGON boundary."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/77c127c4-2ebe-453b-b5af-61858ff02e31",
                bbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        # Rosalia is in Austria (~16.28E, ~47.70N)
        bbox = result["bbox"]
        assert bbox[1] == pytest.approx(16.28, abs=0.1)
        assert bbox[0] == pytest.approx(47.70, abs=0.1)

    def test_deimssdr_site_algoa_bay_south_africa(self):
        """Algoa Bay (South Africa): Southern hemisphere POLYGON."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/6dfa31b5-f5d2-4579-b869-c329c2b76af6",
                bbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        # Algoa Bay is in South Africa (~24.6-26.9E, ~-34.3 to -33.6S)
        bbox = result["bbox"]
        assert bbox[0] == pytest.approx(-34.0, abs=1.0)  # minlat (southern hemisphere)
        assert bbox[1] == pytest.approx(24.61, abs=0.5)  # minlon
        assert bbox[3] == pytest.approx(26.91, abs=0.5)  # maxlon


# --- Integration tests ---


class TestDEIMSSDRIntegration:
    """Integration tests for DEIMS-SDR with various extraction modes."""

    def test_deimssdr_no_download_data(self):
        """With download_data=False, should still return metadata (DEIMS is always metadata)."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/3d87da8b-2b07-41c7-bf05-417832de4fa2",
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert "tbox" in result

    def test_deimssdr_no_metadata_fallback(self):
        """With metadata_fallback=False, should still work (DEIMS always produces metadata)."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/3d87da8b-2b07-41c7-bf05-417832de4fa2",
                bbox=True,
                tbox=True,
                metadata_fallback=False,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert "tbox" in result

    def test_deimssdr_metadata_first(self):
        """With metadata_first=True, should use metadata extraction."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/1a179105-8f6d-416c-98a4-c819006a1255",
                bbox=True,
                metadata_first=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result

    def test_deimssdr_bbox_only(self):
        """Extract only bbox (no tbox)."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/f88b59ce-3716-4823-9152-985e5ff84a7a",
                bbox=True,
                tbox=False,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert "tbox" not in result


# --- Follow validation tests (no network, fast) ---


class TestDEIMSSDRFollowValidation:
    """Fast tests for _extract_external_references() — no network required."""

    def _make_data(self, doi=None, online_locations=None):
        """Build a minimal DEIMS API response data dict."""
        online_dist = {}
        if doi is not None:
            online_dist["doi"] = doi
        if online_locations is not None:
            online_dist["onlineLocation"] = online_locations
        return {"attributes": {"onlineDistribution": online_dist}}

    def test_extract_external_references_doi_url(self):
        provider = DEIMSSDR()
        data = self._make_data(doi="https://doi.org/10.5281/zenodo.10519126")
        refs = provider._extract_external_references(data)
        assert refs == ["https://doi.org/10.5281/zenodo.10519126"]

    def test_extract_external_references_bare_doi(self):
        provider = DEIMSSDR()
        data = self._make_data(doi="10.1594/PANGAEA.924792")
        refs = provider._extract_external_references(data)
        assert refs == ["10.1594/PANGAEA.924792"]

    def test_extract_external_references_placeholder_ignored(self):
        provider = DEIMSSDR()
        data = self._make_data(doi="doi will be released soon after publication")
        refs = provider._extract_external_references(data)
        assert refs == []

    def test_extract_external_references_null_doi(self):
        provider = DEIMSSDR()
        data = self._make_data(doi=None)
        refs = provider._extract_external_references(data)
        assert refs == []

    def test_extract_external_references_online_location_fallback(self):
        provider = DEIMSSDR()
        data = self._make_data(
            doi=None,
            online_locations=[{"url": {"value": "https://doi.org/10.17882/88752"}}],
        )
        refs = provider._extract_external_references(data)
        assert refs == ["https://doi.org/10.17882/88752"]

    def test_extract_external_references_deduplication(self):
        """Same reference in both doi and onlineLocation should appear once."""
        provider = DEIMSSDR()
        data = self._make_data(
            doi="https://doi.org/10.5281/zenodo.10519126",
            online_locations=[
                {"url": {"value": "https://doi.org/10.5281/zenodo.10519126"}}
            ],
        )
        refs = provider._extract_external_references(data)
        assert refs == ["https://doi.org/10.5281/zenodo.10519126"]

    def test_extract_external_references_no_online_distribution(self):
        provider = DEIMSSDR()
        data = {"attributes": {}}
        refs = provider._extract_external_references(data)
        assert refs == []


# --- Follow delegation tests (network required) ---


class TestDEIMSSDRFollow:
    """Network tests for DEIMS-SDR follow delegation to external providers."""

    def test_deimssdr_follow_to_zenodo(self):
        """Lake Paione -> should follow to Zenodo for actual data."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/3d87da8b-2b07-41c7-bf05-417832de4fa2",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert "followed" in result
        assert result["followed"]["from"] == "DEIMS-SDR"
        assert result["followed"]["to"] == "Zenodo"
        assert "zenodo" in result["followed"]["via"].lower()

    def test_deimssdr_follow_to_pangaea(self):
        """Sierra Nevada -> should follow to PANGAEA for actual data."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/9ca7a359-17b0-41f7-b81b-c6aae9268b2a",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert "followed" in result
        assert result["followed"]["from"] == "DEIMS-SDR"
        assert result["followed"]["to"] == "PANGAEA"

    def test_deimssdr_no_follow_uses_deims_metadata(self):
        """Lake Paione with follow=False -> no followed key, DEIMS metadata bbox."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/3d87da8b-2b07-41c7-bf05-417832de4fa2",
                bbox=True,
                tbox=True,
                follow=False,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert "followed" not in result

    def test_deimssdr_follow_unsupported_falls_back(self):
        """Burgas Bay (SEANOE not supported) -> no followed key, DEIMS metadata used."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/f88b59ce-3716-4823-9152-985e5ff84a7a",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert "followed" not in result

    def test_deimssdr_follow_placeholder_doi_falls_back(self):
        """Bird survey (placeholder text DOI) -> no followed key."""
        try:
            result = geoextent.fromRemote(
                "https://deims.org/dataset/5244d4e4-a206-11e2-b534-005056ab003f",
                bbox=True,
                tbox=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert "bbox" in result
        assert "followed" not in result
