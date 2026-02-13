import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.content_providers.MendeleyData import MendeleyData


class TestMendeleyDataValidation:
    """Fast validation tests for Mendeley Data provider (no network calls)."""

    TEST_DATASETS = {
        "geotiff": {
            "doi": "10.17632/ybx6zp2rfp.1",
            "url": "https://data.mendeley.com/datasets/ybx6zp2rfp/1",
            "id": "ybx6zp2rfp",
        },
        "geopackage": {
            "doi": "10.17632/yzddsc67gy.1",
            "url": "https://data.mendeley.com/datasets/yzddsc67gy/1",
            "id": "yzddsc67gy",
        },
        "multi_format": {
            "doi": "10.17632/8h9295v4t3.2",
            "url": "https://data.mendeley.com/datasets/8h9295v4t3/2",
            "id": "8h9295v4t3",
        },
    }

    def test_mendeley_data_provider_instantiation(self):
        """Test that MendeleyData provider can be instantiated."""
        provider = MendeleyData()
        assert provider.name == "Mendeley Data"
        assert provider.record_id is None
        assert provider.version is None

    def test_mendeley_data_doi_validation(self):
        """Test DOI-based validation for Mendeley Data."""
        provider = MendeleyData()

        for dataset_info in self.TEST_DATASETS.values():
            assert provider.validate_provider(dataset_info["doi"]) is True
            assert provider.record_id == dataset_info["id"]

    def test_mendeley_data_url_validation(self):
        """Test URL-based validation for Mendeley Data."""
        provider = MendeleyData()

        for dataset_info in self.TEST_DATASETS.values():
            assert provider.validate_provider(dataset_info["url"]) is True
            assert provider.record_id == dataset_info["id"]

    def test_mendeley_data_invalid_identifiers(self):
        """Test that non-Mendeley identifiers are rejected."""
        provider = MendeleyData()

        invalid_refs = [
            "10.5281/zenodo.4593540",
            "10.6084/m9.figshare.12345678",
            "https://zenodo.org/record/820562",
            "https://figshare.com/articles/123456",
            "not-a-doi-at-all",
            "",
        ]

        for ref in invalid_refs:
            assert provider.validate_provider(ref) is False

    def test_mendeley_data_doi_url_validation(self):
        """Test DOI URL format (https://doi.org/10.17632/...)."""
        provider = MendeleyData()

        # Versioned DOI URL
        assert (
            provider.validate_provider("https://doi.org/10.17632/ybx6zp2rfp.1") is True
        )
        assert provider.record_id == "ybx6zp2rfp"

        # Unversioned DOI URL
        assert provider.validate_provider("https://doi.org/10.17632/ybx6zp2rfp") is True
        assert provider.record_id == "ybx6zp2rfp"

    def test_mendeley_data_landing_page_url_validation(self):
        """Test landing page URLs with and without version."""
        provider = MendeleyData()

        # With version
        assert (
            provider.validate_provider(
                "https://data.mendeley.com/datasets/ybx6zp2rfp/1"
            )
            is True
        )
        assert provider.record_id == "ybx6zp2rfp"
        assert provider.version == "1"

        # Without version
        assert (
            provider.validate_provider("https://data.mendeley.com/datasets/ybx6zp2rfp")
            is True
        )
        assert provider.record_id == "ybx6zp2rfp"
        assert provider.version is None

    def test_mendeley_data_version_validation(self):
        """Test that version is correctly extracted from DOI and URL."""
        provider = MendeleyData()

        provider.validate_provider("10.17632/ybx6zp2rfp.1")
        assert provider.version == "1"

        provider.validate_provider("10.17632/8h9295v4t3.2")
        assert provider.version == "2"

    def test_mendeley_data_doi_without_version_validation(self):
        """Test DOI without explicit version number.

        Even without a version in the DOI, the DOI resolves to a URL
        containing the version (e.g., /datasets/ybx6zp2rfp/1), so
        the version gets extracted from the resolved URL.
        """
        provider = MendeleyData()

        assert provider.validate_provider("10.17632/ybx6zp2rfp") is True
        assert provider.record_id == "ybx6zp2rfp"
        # Version is extracted from the resolved URL even when not in the DOI
        assert provider.version is not None


class TestMendeleyDataExtraction:
    """Network-dependent tests for Mendeley Data provider."""

    def test_mendeley_data_metadata_only_extraction(self):
        """Test metadata-only extraction (provider_sample smoke test).

        Mendeley Data does not expose geospatial metadata, so this returns
        a minimal result without bbox.
        """
        result = geoextent.fromRemote(
            "10.17632/ybx6zp2rfp.1",
            bbox=True,
            tbox=True,
            download_data=False,
        )

        assert result is not None
        assert result["format"] == "remote"

    def test_mendeley_data_identifier_variants_extraction(self):
        """Test that all identifier formats produce the same extraction result.

        Covers: versioned DOI, unversioned DOI, unversioned DOI URL,
        landing page URL with version, landing page URL without version.
        """
        variants = [
            "10.17632/ybx6zp2rfp.1",
            "10.17632/ybx6zp2rfp",
            "https://doi.org/10.17632/ybx6zp2rfp",
            "https://data.mendeley.com/datasets/ybx6zp2rfp/1",
            "https://data.mendeley.com/datasets/ybx6zp2rfp",
        ]

        results = []
        for identifier in variants:
            result = geoextent.fromRemote(
                identifier,
                bbox=True,
                download_data=True,
            )
            assert result is not None, f"Failed for identifier: {identifier}"
            assert result["format"] == "remote", f"Wrong format for: {identifier}"
            assert "bbox" in result, f"No bbox for identifier: {identifier}"
            results.append(result["bbox"])

        # All variants should produce the same bounding box
        reference_bbox = results[0]
        for i, bbox in enumerate(results[1:], 1):
            assert bbox == reference_bbox, (
                f"Identifier variant {variants[i]} produced bbox {bbox} "
                f"different from reference {reference_bbox}"
            )

    def test_mendeley_data_geotiff_extraction(self):
        """Test full extraction of a GeoTIFF dataset (tropical cloud forests)."""
        result = geoextent.fromRemote(
            "10.17632/ybx6zp2rfp.1",
            bbox=True,
            tbox=True,
            download_data=True,
        )

        assert result is not None
        assert result["format"] == "remote"
        assert "bbox" in result

        bbox = result["bbox"]
        assert len(bbox) == 4
        # Tropical montane cloud forest: global tropics coverage
        # Expected bbox: [-180.0, -23.55, 180.0, 23.55] (lat/lon EPSG:4326 order)
        assert -180.0 <= bbox[0] <= -170.0, f"South latitude {bbox[0]} out of range"
        assert -25.0 <= bbox[1] <= -20.0, f"West longitude {bbox[1]} out of range"
        assert 170.0 <= bbox[2] <= 180.0, f"North latitude {bbox[2]} out of range"
        assert 20.0 <= bbox[3] <= 25.0, f"East longitude {bbox[3]} out of range"

        assert result.get("crs") == "4326"

    def test_mendeley_data_geopackage_extraction(self):
        """Test extraction of a GeoPackage dataset (Emilia-Romagna floods)."""
        result = geoextent.fromRemote(
            "10.17632/yzddsc67gy.1",
            bbox=True,
            download_data=True,
        )

        assert result is not None
        assert result["format"] == "remote"
        assert "bbox" in result

        bbox = result["bbox"]
        assert len(bbox) == 4
        # Emilia-Romagna, Italy: ~44°N, ~12°E
        assert 43.0 <= bbox[0] <= 45.0, f"South latitude {bbox[0]} out of range"
        assert 11.0 <= bbox[1] <= 13.0, f"West longitude {bbox[1]} out of range"
        assert 44.0 <= bbox[2] <= 46.0, f"North latitude {bbox[2]} out of range"
        assert 12.0 <= bbox[3] <= 14.0, f"East longitude {bbox[3]} out of range"

        assert result.get("crs") == "4326"

    def test_mendeley_data_multi_format_full_extraction(self):
        """Test full extraction of multi-format dataset (Galicia mills).

        Dataset contains 3 ZIP files with Shapefile, GML, GeoJSON, and KML data
        covering the historical Galicia region (modern southern Poland / western Ukraine).
        """
        result = geoextent.fromRemote(
            "10.17632/8h9295v4t3.2",
            bbox=True,
            download_data=True,
        )

        assert result is not None
        assert result["format"] == "remote"
        assert "bbox" in result

        bbox = result["bbox"]
        assert len(bbox) == 4
        # Galicia region: roughly 47-52°N, 19-26°E
        # Grid-based data extends from origin (0,0) to ~51°N, 32°E
        assert bbox[0] >= -1.0, f"South latitude {bbox[0]} unexpectedly negative"
        assert bbox[2] <= 55.0, f"North latitude {bbox[2]} too high"
        assert bbox[3] <= 35.0, f"East longitude {bbox[3]} too high"

        assert result.get("crs") == "4326"

    def test_mendeley_data_multi_format_size_limited(self):
        """Test size-limited extraction producing different results.

        The multi-format dataset has 3 ZIP files sorted by size:
          - C_georeferencing_controlpoints.zip (256 KB) — only .txt files, no geospatial data
          - B_mills_dataset.zip (1.8 MB) — Shapefiles, GML, GeoJSON, KML
          - A_Galicia_borders.zip (3.3 MB) — borders in multiple formats

        With a 2MB limit, only C (256 KB) fits before the budget breaks on B,
        yielding no bbox since C contains no geospatial files.

        With a 3MB limit, C + B both fit (~2 MB combined), yielding a bbox
        from the mills geospatial data.
        """
        # Small limit: only non-geospatial control points fit
        result_small = geoextent.fromRemote(
            "10.17632/8h9295v4t3.2",
            bbox=True,
            download_data=True,
            max_download_size="2MB",
        )
        assert result_small is not None
        assert result_small["format"] == "remote"
        assert "bbox" not in result_small, (
            "With 2MB limit, only non-geospatial control point files should be downloaded, "
            "resulting in no bbox"
        )

        # Larger limit: mills dataset (1.8MB) + control points (256KB) fit
        result_large = geoextent.fromRemote(
            "10.17632/8h9295v4t3.2",
            bbox=True,
            download_data=True,
            max_download_size="3MB",
        )
        assert result_large is not None
        assert result_large["format"] == "remote"
        assert "bbox" in result_large, (
            "With 3MB limit, the mills geospatial dataset should be included, "
            "yielding a bounding box"
        )

        bbox = result_large["bbox"]
        assert len(bbox) == 4
        assert result_large.get("crs") == "4326"
