"""Tests for the --metadata-first feature.

The metadata-first strategy tries metadata-only extraction first (fast, no file download),
then falls back to data download if metadata didn't yield the requested extents.
"""

import pytest
import geoextent.lib.extent as geoextent
from conftest import NETWORK_SKIP_EXCEPTIONS


class TestMetadataFirstValidation:
    """Fast validation tests (no network)."""

    def test_metadata_first_and_no_download_data_mutually_exclusive(self):
        """--metadata-first and --no-download-data cannot be used together."""
        with pytest.raises(ValueError, match="mutually exclusive"):
            geoextent.fromRemote(
                "https://zenodo.org/record/820562",
                bbox=True,
                tbox=False,
                download_data=False,
                metadata_first=True,
            )

    def test_supports_metadata_extraction_base_class(self):
        """ContentProvider base class defaults to supports_metadata_extraction=False."""
        from geoextent.lib.content_providers.providers import ContentProvider

        provider = ContentProvider()
        assert provider.supports_metadata_extraction is False

    def test_supports_metadata_extraction_doi_provider(self):
        """DoiProvider inherits supports_metadata_extraction=False from ContentProvider."""
        from geoextent.lib.content_providers.providers import DoiProvider

        provider = DoiProvider()
        assert provider.supports_metadata_extraction is False

    def test_supports_metadata_extraction_ckan_provider(self):
        """CKANProvider overrides supports_metadata_extraction=True."""
        from geoextent.lib.content_providers.CKANProvider import CKANProvider

        provider = CKANProvider()
        assert provider.supports_metadata_extraction is True

    def test_supports_metadata_extraction_pangaea(self):
        """Pangaea overrides supports_metadata_extraction=True."""
        from geoextent.lib.content_providers.Pangaea import Pangaea

        provider = Pangaea()
        assert provider.supports_metadata_extraction is True

    def test_supports_metadata_extraction_bgr(self):
        """BGR overrides supports_metadata_extraction=True."""
        from geoextent.lib.content_providers.BGR import BGR

        provider = BGR()
        assert provider.supports_metadata_extraction is True

    def test_supports_metadata_extraction_wikidata(self):
        """Wikidata overrides supports_metadata_extraction=True."""
        from geoextent.lib.content_providers.Wikidata import Wikidata

        provider = Wikidata()
        assert provider.supports_metadata_extraction is True

    def test_supports_metadata_extraction_zenodo(self):
        """Zenodo does NOT support metadata extraction."""
        from geoextent.lib.content_providers.Zenodo import Zenodo

        provider = Zenodo()
        assert provider.supports_metadata_extraction is False

    def test_supports_metadata_extraction_figshare(self):
        """Figshare supports metadata extraction (published_date, custom_fields)."""
        from geoextent.lib.content_providers.Figshare import Figshare

        provider = Figshare()
        assert provider.supports_metadata_extraction is True

    def test_supports_metadata_extraction_fourtu(self):
        """4TU supports metadata extraction (geolocation via custom_fields)."""
        from geoextent.lib.content_providers.FourTU import FourTU

        provider = FourTU()
        assert provider.supports_metadata_extraction is True


class TestMetadataFirstNetwork:
    """Network tests for metadata-first extraction (auto-marked slow)."""

    def test_metadata_first_with_metadata_provider(self):
        """Senckenberg has metadata: metadata-first should succeed with extraction_method=metadata."""
        try:
            result = geoextent.fromRemote(
                "10.12761/sgn.2018.10225",
                bbox=True,
                tbox=False,
                metadata_first=True,
            )

            assert result is not None
            assert result.get("extraction_method") == "metadata"
            assert result.get("bbox") is not None
            assert result.get("crs") == "4326"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_metadata_first_with_wikidata(self):
        """Wikidata has metadata: metadata-first should succeed with extraction_method=metadata."""
        try:
            result = geoextent.fromRemote(
                "Q64",  # Berlin
                bbox=True,
                tbox=False,
                metadata_first=True,
            )

            assert result is not None
            assert result.get("extraction_method") == "metadata"
            assert result.get("bbox") is not None
            assert result.get("crs") == "4326"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_metadata_first_fourtu_point_vs_download(self):
        """4TU ReBioClim Dresden: metadata returns a point, download returns full extent.

        Metadata extraction yields a single point (51.050407, 13.737262) from custom_fields.
        Data download yields a larger bbox covering the full 500x500m grid cells over Dresden.
        With metadata-first, the metadata point should be returned (extraction_method=metadata).
        """
        url = "https://data.4tu.nl/datasets/3035126d-ee51-4dbd-a187-5f6b0be85e9f/1"

        try:
            # metadata-first should use metadata (point location)
            result_mf = geoextent.fromRemote(
                url,
                bbox=True,
                tbox=True,
                metadata_first=True,
            )
            assert result_mf is not None
            assert result_mf.get("extraction_method") == "metadata"
            bbox_mf = result_mf["bbox"]
            # Point: all four values should be approximately equal pairwise
            assert (
                abs(bbox_mf[0] - bbox_mf[2]) < 0.001
            ), "Metadata bbox should be a point (lat)"
            assert (
                abs(bbox_mf[1] - bbox_mf[3]) < 0.001
            ), "Metadata bbox should be a point (lon)"
            assert abs(bbox_mf[0] - 51.050407) < 0.01
            assert abs(bbox_mf[1] - 13.737262) < 0.01

            # tbox should also be extracted from custom_fields
            assert result_mf.get("tbox") is not None
            assert result_mf["tbox"][0].startswith("2025-05")

            # Full download should yield a different (larger) bbox
            result_dl = geoextent.fromRemote(
                url,
                bbox=True,
                tbox=False,
                download_data=True,
            )
            assert result_dl is not None
            bbox_dl = result_dl["bbox"]
            # Download bbox should be wider than the metadata point
            bbox_width_dl = abs(bbox_dl[3] - bbox_dl[1])
            bbox_height_dl = abs(bbox_dl[2] - bbox_dl[0])
            assert (
                bbox_width_dl > 0.1
            ), f"Download bbox should be wider than a point, got width {bbox_width_dl}"
            assert (
                bbox_height_dl > 0.1
            ), f"Download bbox should be taller than a point, got height {bbox_height_dl}"

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_metadata_first_with_no_metadata_provider(self):
        """Zenodo has no metadata: metadata-first should fall back to extraction_method=download."""
        try:
            result = geoextent.fromRemote(
                "https://zenodo.org/record/820562",
                bbox=True,
                tbox=False,
                metadata_first=True,
            )

            assert result is not None
            assert result.get("extraction_method") == "download"
            assert result.get("bbox") is not None

        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")

    def test_metadata_first_via_cli(self):
        """CLI integration: --metadata-first flag works end-to-end."""
        import subprocess
        import sys
        import json

        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "geoextent",
                    "-b",
                    "--metadata-first",
                    "Q64",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            assert proc.returncode == 0, f"CLI failed: {proc.stderr}"
            output = json.loads(proc.stdout)
            # CLI outputs GeoJSON FeatureCollection; extraction_method is in feature properties
            assert output.get("type") == "FeatureCollection"
            feature_props = output["features"][0]["properties"]
            assert feature_props.get("extraction_method") == "metadata"

        except subprocess.TimeoutExpired:
            pytest.skip("CLI timeout")
        except NETWORK_SKIP_EXCEPTIONS as e:
            pytest.skip(f"Network error: {e}")
