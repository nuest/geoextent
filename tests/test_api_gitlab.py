"""Tests for GitLab content provider.

Tests cover:
- URL validation and reference parsing (no network)
- Provider metadata (no network)
- Data download extraction from public repositories (network)

Example repositories (one per GitLab instance where possible):
- gitlab.com/eaws/eaws-regions: GeoJSON, European avalanche warning regions (EAWS)
- gitlab.com/bazylizon/seismicity: CSV with dates, Upper Silesia seismicity 2014-2018
- gitlab.com/Weatherman_/radolan2map: GeoPackage, DWD radar network (EPSG:3035)
- git.rwth-aachen.de/nfdi4earth/crosstopics/knowledgehub-maps: GeoPackage, NFDI4Earth
"""

import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.content_providers.GitLab import GitLab
from conftest import NETWORK_SKIP_EXCEPTIONS

# --- Validation tests (no network, fast) ---


class TestGitLabValidation:
    """Fast validation tests that do not require network access."""

    def test_gitlab_url_validation(self):
        """Basic repo URL on gitlab.com."""
        provider = GitLab()
        assert provider.validate_provider("https://gitlab.com/bazylizon/seismicity")

    def test_gitlab_url_with_tree_path_validation(self):
        """URL with /-/tree/{ref}/{path}."""
        provider = GitLab()
        assert provider.validate_provider(
            "https://gitlab.com/eaws/eaws-regions/-/tree/master/public/outline"
        )

    def test_gitlab_url_with_git_suffix_validation(self):
        """URL ending in .git."""
        provider = GitLab()
        assert provider.validate_provider("https://gitlab.com/eaws/eaws-regions.git")

    def test_gitlab_nested_namespace_validation(self):
        """URL with nested namespace (group/subgroup/project)."""
        provider = GitLab()
        assert provider.validate_provider("https://gitlab.com/group/subgroup/project")

    def test_gitlab_known_self_hosted_validation(self):
        """Known self-hosted GitLab instance (no network needed)."""
        provider = GitLab()
        assert provider.validate_provider(
            "https://git.rwth-aachen.de/nfdi4earth/crosstopics/knowledgehub-maps"
        )

    def test_gitlab_hostname_contains_gitlab_validation(self):
        """Host with 'gitlab' in name detected without API probe."""
        provider = GitLab()
        assert provider.validate_provider("https://gitlab.example.edu/user/project")

    def test_gitlab_rejects_github_validation(self):
        """github.com URLs are not matched (handled by GitHub provider)."""
        provider = GitLab()
        assert not provider.validate_provider("https://github.com/user/repo")

    def test_gitlab_invalid_identifiers_validation(self):
        """Rejects non-GitLab identifiers."""
        invalid = [
            "https://github.com/user/repo",
            "10.5281/zenodo.820562",
            "https://zenodo.org/records/820562",
            "not-a-valid-identifier",
            "https://gitlab.com/",  # no project path
            "https://gitlab.com/useronly",  # only 1 segment
            "",
        ]
        for identifier in invalid:
            provider = GitLab()
            assert not provider.validate_provider(
                identifier
            ), f"Should reject: {identifier}"

    def test_gitlab_provider_info(self):
        """provider_info() returns expected structure."""
        info = GitLab.provider_info()
        assert info["name"] == "GitLab"
        assert "gitlab.com" in info["website"]
        assert len(info["examples"]) > 0
        assert "supported_identifiers" in info

    def test_gitlab_parse_reference_simple(self):
        """Parse simple namespace/project URL."""
        provider = GitLab()
        provider.validate_provider("https://gitlab.com/bazylizon/seismicity")
        parsed = provider._parse_reference(provider.reference)
        assert parsed["owner"] == "bazylizon"
        assert parsed["repo"] == "seismicity"
        assert parsed["ref"] is None
        assert parsed["path"] is None

    def test_gitlab_parse_reference_with_tree(self):
        """Parse URL with /-/tree/{ref}/{path}."""
        provider = GitLab()
        provider.validate_provider(
            "https://gitlab.com/eaws/eaws-regions/-/tree/master/public/outline"
        )
        parsed = provider._parse_reference(provider.reference)
        assert parsed["owner"] == "eaws"
        assert parsed["repo"] == "eaws-regions"
        assert parsed["ref"] == "master"
        assert parsed["path"] == "public/outline"

    def test_gitlab_parse_reference_nested_namespace(self):
        """Parse URL with nested namespace (group/subgroup/project)."""
        provider = GitLab()
        provider.validate_provider(
            "https://git.rwth-aachen.de/nfdi4earth/crosstopics/knowledgehub-maps/-/tree/main/maps"
        )
        parsed = provider._parse_reference(provider.reference)
        assert parsed["owner"] == "nfdi4earth/crosstopics"
        assert parsed["repo"] == "knowledgehub-maps"
        assert parsed["ref"] == "main"
        assert parsed["path"] == "maps"

    def test_gitlab_parse_reference_git_suffix(self):
        """.git suffix stripped from project name."""
        provider = GitLab()
        provider.validate_provider("https://gitlab.com/eaws/eaws-regions.git")
        parsed = provider._parse_reference(provider.reference)
        assert parsed["repo"] == "eaws-regions"

    def test_gitlab_supports_metadata_extraction(self):
        """GitLab does not support metadata-only extraction."""
        provider = GitLab()
        assert provider.supports_metadata_extraction is False

    def test_gitlab_provider_can_be_used(self):
        provider = GitLab()
        assert provider.name == "GitLab"
        assert hasattr(provider, "validate_provider")
        assert hasattr(provider, "download")


# --- Network tests (slow, data download extraction) ---


class TestGitLabExtraction:
    """Network tests for GitLab data download and extraction.

    One test per GitLab instance, covering GeoJSON, CSV with dates,
    and GeoPackage formats across gitlab.com and self-hosted instances.
    """

    def test_gitlab_metadata_only_extraction(self):
        """Provider sample: bazylizon/seismicity — small CSV with coordinates.

        Lightweight provider sample test for CI smoke-testing.
        Upper Silesia (Poland) seismicity data, 46 KB CSV.
        """
        try:
            result = geoextent.fromRemote(
                "https://gitlab.com/bazylizon/seismicity",
                bbox=True,
                tbox=False,
                download_skip_nogeo=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        # Upper Silesia, Poland — verify reasonable bounds
        assert bbox[0] == pytest.approx(49.95, abs=0.1)  # minlat
        assert bbox[2] == pytest.approx(50.38, abs=0.1)  # maxlat

    def test_gitlab_eaws_geojson(self):
        """Provider sample: eaws/eaws-regions — European avalanche warning GeoJSON.

        Downloads 43 country/region outlines as GeoJSON files.
        EAWS is the European Avalanche Warning Services, an operational
        research coordination body (https://www.avalanches.org/).

        Merged bbox covers European avalanche regions from Iberian Peninsula
        to Scandinavia and eastward to the Carpathians.
        """
        try:
            result = geoextent.fromRemote(
                "https://gitlab.com/eaws/eaws-regions/-/tree/master/public/outline",
                bbox=True,
                tbox=False,
                download_skip_nogeo=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4

        # EPSG:4326 native order: [minlat, minlon, maxlat, maxlon]
        # Regions span from Spain/Canary Islands to Scandinavia
        assert bbox[0] == pytest.approx(37.6, abs=1)  # minlat (southern Spain)
        assert bbox[1] == pytest.approx(-23.8, abs=1)  # minlon (Canary Islands)
        assert bbox[2] == pytest.approx(78.4, abs=1)  # maxlat (Svalbard/Norway)
        assert bbox[3] == pytest.approx(29.5, abs=1)  # maxlon (eastern Finland/Turkey)

    def test_gitlab_seismicity_csv_with_dates(self):
        """gitlab.com: bazylizon/seismicity — CSV with coordinates and dates.

        Upper Silesia (Poland) seismicity analysis 2014-2018.
        CSV has columns: Date;Time t0 UTC;Mag;Lat [deg];Lon [deg]
        1077 earthquake records.
        """
        try:
            result = geoextent.fromRemote(
                "https://gitlab.com/bazylizon/seismicity",
                bbox=True,
                tbox=True,
                download_skip_nogeo=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Spatial: Upper Silesia, Poland
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        # EPSG:4326 native order: [minlat, minlon, maxlat, maxlon]
        assert bbox[0] == pytest.approx(49.95, abs=0.05)  # minlat
        assert bbox[1] == pytest.approx(18.44, abs=0.05)  # minlon
        assert bbox[2] == pytest.approx(50.38, abs=0.05)  # maxlat
        assert bbox[3] == pytest.approx(19.37, abs=0.05)  # maxlon

        # Temporal: data starts 2014-01-02
        assert result.get("tbox") is not None
        tbox = result["tbox"]
        assert tbox[0] == "2014-01-02"

    def test_gitlab_radolan2map_geopackage(self):
        """gitlab.com: Weatherman_/radolan2map — GeoPackage with EPSG:3035.

        DWD (German Weather Service) radar network stations and coverage buffers.
        Two GeoPackage files in EPSG:3035 (European LAEA), reprojected to WGS84.
        """
        try:
            result = geoextent.fromRemote(
                "https://gitlab.com/Weatherman_/radolan2map/-/tree/master/example/shapes/RadarNetwork",
                bbox=True,
                tbox=False,
                download_skip_nogeo=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Spatial: German radar network coverage (extends slightly beyond borders)
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        # EPSG:4326 native order: [minlat, minlon, maxlat, maxlon]
        assert bbox[0] == pytest.approx(46.5, abs=0.5)  # minlat (southern coverage)
        assert bbox[1] == pytest.approx(3.9, abs=0.5)  # minlon (western coverage)
        assert bbox[2] == pytest.approx(55.4, abs=0.5)  # maxlat (northern coverage)
        assert bbox[3] == pytest.approx(16.4, abs=0.5)  # maxlon (eastern coverage)

    def test_gitlab_rwth_aachen_self_hosted(self):
        """git.rwth-aachen.de: NFDI4Earth knowledgehub-maps — self-hosted instance.

        Tests that the provider works with self-hosted GitLab instances.
        Downloads GeoPackage files with NFDI4Earth dataset locations.
        """
        try:
            result = geoextent.fromRemote(
                "https://git.rwth-aachen.de/nfdi4earth/crosstopics/knowledgehub-maps/-/tree/main/maps/200_datasets/data",
                bbox=True,
                tbox=False,
                download_skip_nogeo=True,
            )
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

        assert result is not None
        assert result["format"] == "remote"

        # Spatial: NFDI4Earth datasets have global coverage
        assert result.get("bbox") is not None
        bbox = result["bbox"]
        assert len(bbox) == 4
        # Global extent — just verify south < north and reasonable bounds
        assert bbox[0] < bbox[2]  # minlat < maxlat
