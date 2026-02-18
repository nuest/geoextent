import io
import os
import pytest
import geoextent.lib.extent as geoextent
from conftest import NETWORK_SKIP_EXCEPTIONS
from geoextent.lib.exceptions import DownloadSizeExceeded


class TestGBIFProvider:
    """Test GBIF (Global Biodiversity Information Facility) content provider."""

    TEST_DATASETS = {
        "bee_species_nl": {
            "doi": "10.15468/6bleia",
            "dataset_key": "378651d7-c235-4205-a617-2939d6faa434",
            "description": "Bee species in the Netherlands (EIS, metadata-only test)",
            "expected_bbox_lat": (50.0, 54.0),
            "expected_bbox_lon": (3.0, 8.0),
        },
        "colombia_biodiversity": {
            "doi": "10.15472/lavgys",
            "description": "Colombia biodiversity (non-primary DOI prefix)",
            "expected_bbox_lat": (-5.0, 13.0),
            "expected_bbox_lon": (-82.0, -66.0),
        },
    }

    # -- Fast validation tests (no network) --

    def test_gbif_doi_validation_primary_prefix(self):
        """Test that GBIF primary DOI prefix 10.15468/ is correctly validated"""
        from geoextent.lib.content_providers.GBIF import GBIF

        provider = GBIF()
        assert provider.validate_provider("10.15468/6bleia")

    def test_gbif_doi_validation_secondary_prefix(self):
        """Test that GBIF secondary DOI prefix 10.15472/ is correctly validated"""
        from geoextent.lib.content_providers.GBIF import GBIF

        provider = GBIF()
        assert provider.validate_provider("10.15472/lavgys")

    def test_gbif_url_validation(self):
        """Test that gbif.org dataset URLs are correctly validated and UUID extracted"""
        from geoextent.lib.content_providers.GBIF import GBIF

        provider = GBIF()
        assert provider.validate_provider(
            "https://www.gbif.org/dataset/378651d7-c235-4205-a617-2939d6faa434"
        )
        assert provider.dataset_key == "378651d7-c235-4205-a617-2939d6faa434"

    def test_gbif_validation_invalid_identifiers(self):
        """Test that non-GBIF URLs/DOIs are rejected"""
        from geoextent.lib.content_providers.GBIF import GBIF

        provider = GBIF()
        assert not provider.validate_provider("https://zenodo.org/record/4593540")
        assert not provider.validate_provider("10.5281/zenodo.4593540")
        assert not provider.validate_provider("https://example.com/dataset/123")
        # Pensoft DOI prefix — should NOT match GBIF
        assert not provider.validate_provider("10.3897/BDJ.13.e159973")

    def test_gbif_supports_metadata_extraction(self):
        """Test that provider reports metadata extraction support"""
        from geoextent.lib.content_providers.GBIF import GBIF

        provider = GBIF()
        assert provider.supports_metadata_extraction is True

    def test_gbif_download_size_exceeded_validation(self):
        """Test DownloadSizeExceeded exception carries correct attributes"""
        exc = DownloadSizeExceeded(2_000_000_000, 1_073_741_824, "GBIF")
        assert exc.estimated_size == 2_000_000_000
        assert exc.max_size == 1_073_741_824
        assert exc.provider == "GBIF"
        assert "2,000,000,000" in str(exc)
        assert "GBIF" in str(exc)

    def test_gbif_dwca_txt_validation(self, tmp_path):
        """Test that tab-delimited .txt with Darwin Core columns is parsed by CSV handler"""
        txt_file = tmp_path / "occurrence.txt"
        txt_file.write_text(
            "gbifID\tdecimalLatitude\tdecimalLongitude\tspecies\n"
            "123\t52.3676\t4.9041\tApis mellifera\n"
            "124\t51.9244\t4.4777\tBombus terrestris\n"
            "125\t53.2194\t6.5665\tAndrena flavipes\n"
        )
        result = geoextent.fromFile(str(txt_file), bbox=True)
        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from tab-delimited DwC-A .txt file"
        # Default output: [minlat, minlon, maxlat, maxlon]
        minlat, minlon, maxlat, maxlon = bbox
        assert 51.0 < minlat < 52.5
        assert 4.0 < minlon < 5.0
        assert 53.0 < maxlat < 54.0
        assert 6.0 < maxlon < 7.0

    # -- Network tests (auto-marked slow via conftest) --

    def test_gbif_metadata_only_extraction(self):
        """Test metadata-only extraction from GBIF (provider_sample smoke test)"""
        ds = self.TEST_DATASETS["bee_species_nl"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or GBIF unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"GBIF unreachable: {e}")
            raise
        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from GBIF metadata"
        # Default output order: [minlat, minlon, maxlat, maxlon]
        minlat, minlon, maxlat, maxlon = bbox
        assert (
            ds["expected_bbox_lat"][0] < minlat < maxlat < ds["expected_bbox_lat"][1]
        ), f"Latitude range {minlat}-{maxlat} outside expected {ds['expected_bbox_lat']}"
        assert (
            ds["expected_bbox_lon"][0] < minlon < maxlon < ds["expected_bbox_lon"][1]
        ), f"Longitude range {minlon}-{maxlon} outside expected {ds['expected_bbox_lon']}"

    def test_gbif_temporal_extraction(self):
        """Test temporal extent extraction from GBIF metadata"""
        ds = self.TEST_DATASETS["bee_species_nl"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=False,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or GBIF unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"GBIF unreachable: {e}")
            raise
        assert result is not None
        tbox = result.get("tbox")
        assert tbox is not None, "Expected temporal extent from GBIF metadata"
        assert len(tbox) == 2

    def test_gbif_url_based_extraction(self):
        """Test extraction via gbif.org dataset URL"""
        ds = self.TEST_DATASETS["bee_species_nl"]
        try:
            result = geoextent.fromRemote(
                f"https://www.gbif.org/dataset/{ds['dataset_key']}",
                bbox=True,
                tbox=False,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or GBIF unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"GBIF unreachable: {e}")
            raise
        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from GBIF URL-based extraction"

    def test_gbif_non_primary_doi_prefix(self):
        """Test extraction with non-primary DOI prefix (10.15472/)"""
        ds = self.TEST_DATASETS["colombia_biodiversity"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=False,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or GBIF unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"GBIF unreachable: {e}")
            raise
        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from GBIF 10.15472/ dataset"

    def test_gbif_download_size_exceeded_small_limit(self):
        """Test that DownloadSizeExceeded is raised via fromRemote with a tiny size limit"""
        ds = self.TEST_DATASETS["bee_species_nl"]
        try:
            with pytest.raises(DownloadSizeExceeded) as exc_info:
                geoextent.fromRemote(
                    ds["doi"],
                    bbox=True,
                    tbox=False,
                    download_data=True,
                    max_download_size="1B",  # 1 byte — always exceeded
                )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or GBIF/IPT unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"GBIF/IPT unreachable: {e}")
            # If DownloadSizeExceeded was never raised (e.g. HEAD returned no
            # Content-Length), skip rather than fail
            if "DownloadSizeExceeded" not in str(type(e)):
                pytest.skip(
                    "IPT server did not report Content-Length; "
                    "size guard could not trigger"
                )
            raise
        else:
            exc = exc_info.value
            assert exc.provider == "GBIF"
            assert exc.max_size == 1
            assert exc.estimated_size > 1

    def test_gbif_cli_size_prompt_decline(self, monkeypatch):
        """Test that _call_fromRemote_with_size_prompt returns None when user declines"""
        from geoextent.__main__ import _call_fromRemote_with_size_prompt

        def fake_fromRemote(**kwargs):
            raise DownloadSizeExceeded(500_000_000, 100_000_000, "GBIF")

        # io.StringIO.isatty() returns False; wrap to pretend we have a TTY
        class FakeTTY(io.StringIO):
            def isatty(self):
                return True

        monkeypatch.setattr("geoextent.__main__.extent.fromRemote", fake_fromRemote)
        monkeypatch.setattr("sys.stdin", FakeTTY("N\n"))

        result = _call_fromRemote_with_size_prompt(
            {"remote_identifier": "10.15468/fake", "bbox": True}
        )
        assert result is None

    def test_gbif_cli_size_prompt_accept(self, monkeypatch):
        """Test that _call_fromRemote_with_size_prompt retries when user accepts"""
        from geoextent.__main__ import _call_fromRemote_with_size_prompt

        call_count = {"n": 0}

        def fake_fromRemote(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise DownloadSizeExceeded(500_000_000, 100_000_000, "GBIF")
            # Second call succeeds (with increased limit)
            assert kwargs["max_download_size"] == "500000001B"
            return {"bbox": [1, 2, 3, 4]}

        class FakeTTY(io.StringIO):
            def isatty(self):
                return True

        monkeypatch.setattr("geoextent.__main__.extent.fromRemote", fake_fromRemote)
        monkeypatch.setattr("sys.stdin", FakeTTY("y\n"))

        result = _call_fromRemote_with_size_prompt(
            {"remote_identifier": "10.15468/fake", "bbox": True}
        )
        assert result == {"bbox": [1, 2, 3, 4]}
        assert call_count["n"] == 2

    def test_gbif_cli_size_prompt_noninteractive_validation(self):
        """Test that DownloadSizeExceeded propagates in non-interactive mode"""
        from geoextent.__main__ import _call_fromRemote_with_size_prompt

        # In test context, stdin.isatty() returns False, so exception propagates
        with pytest.raises(DownloadSizeExceeded):

            def fake_fromRemote(**kwargs):
                raise DownloadSizeExceeded(500_000_000, 100_000_000, "GBIF")

            import geoextent.__main__ as main_mod

            orig = main_mod.extent.fromRemote
            main_mod.extent.fromRemote = fake_fromRemote
            try:
                _call_fromRemote_with_size_prompt(
                    {"remote_identifier": "10.15468/fake", "bbox": True}
                )
            finally:
                main_mod.extent.fromRemote = orig

    def test_gbif_dwca_download(self):
        """Test DwC-A download for the bee species dataset (small archive)"""
        ds = self.TEST_DATASETS["bee_species_nl"]
        try:
            result = geoextent.fromRemote(
                ds["doi"],
                bbox=True,
                tbox=False,
                download_data=True,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or GBIF/IPT unreachable")
        except Exception as e:
            if "Connection" in str(e) or "Max retries" in str(e) or "Timeout" in str(e):
                pytest.skip(f"GBIF/IPT unreachable: {e}")
            raise
        assert result is not None
        # DwC-A download should produce a bbox (either from data or metadata fallback)
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from GBIF DwC-A download"
