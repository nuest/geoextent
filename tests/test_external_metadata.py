"""
Integration tests for external metadata retrieval from CrossRef and DataCite.

These tests use real DOIs and connect to actual metadata sources (no mocks).
Tests verify that metadata is correctly retrieved and formatted as an array.
"""

import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib import external_metadata


class TestExternalMetadataIntegration:
    """Integration tests for external metadata retrieval"""

    # Test DOIs from different sources
    DATACITE_DOI = "10.5281/zenodo.4593540"  # Zenodo (DataCite)
    CROSSREF_DOI = "10.1371/journal.pone.0230416"  # PLOS ONE (CrossRef)

    def test_datacite_metadata_retrieval(self):
        """Test metadata retrieval from DataCite API"""
        metadata = external_metadata.get_external_metadata(
            self.DATACITE_DOI, method="datacite"
        )

        # Should return a list with one entry
        assert isinstance(metadata, list)
        assert len(metadata) == 1

        # Verify metadata structure
        meta = metadata[0]
        assert meta["source"] == "DataCite"
        assert meta["doi"] == self.DATACITE_DOI
        assert "title" in meta
        assert "authors" in meta
        assert "publisher" in meta
        assert meta["publisher"] == "Zenodo"
        assert "publication_year" in meta
        assert "url" in meta
        assert "license" in meta

    def test_crossref_metadata_retrieval(self):
        """Test metadata retrieval from CrossRef API"""
        metadata = external_metadata.get_external_metadata(
            self.CROSSREF_DOI, method="crossref"
        )

        # Should return a list with one entry
        assert isinstance(metadata, list)
        assert len(metadata) == 1

        # Verify metadata structure
        meta = metadata[0]
        assert meta["source"] == "CrossRef"
        assert meta["doi"] == self.CROSSREF_DOI
        assert "title" in meta
        assert "The citation advantage" in meta["title"]
        assert "authors" in meta
        assert len(meta["authors"]) > 0
        assert "publisher" in meta
        assert "publication_year" in meta
        assert meta["publication_year"] == 2020
        assert "url" in meta
        assert "license" in meta

    def test_auto_method_datacite_doi(self):
        """Test auto method with DataCite DOI (should try CrossRef first, fallback to DataCite)"""
        metadata = external_metadata.get_external_metadata(
            self.DATACITE_DOI, method="auto"
        )

        # Should return a list with one entry from DataCite
        assert isinstance(metadata, list)
        assert len(metadata) == 1
        assert metadata[0]["source"] == "DataCite"

    def test_auto_method_crossref_doi(self):
        """Test auto method with CrossRef DOI (should get result from CrossRef)"""
        metadata = external_metadata.get_external_metadata(
            self.CROSSREF_DOI, method="auto"
        )

        # Should return a list with one entry from CrossRef
        assert isinstance(metadata, list)
        assert len(metadata) == 1
        assert metadata[0]["source"] == "CrossRef"

    def test_all_method_datacite_doi(self):
        """Test all method with DataCite DOI (should query both sources)"""
        metadata = external_metadata.get_external_metadata(
            self.DATACITE_DOI, method="all"
        )

        # Should return a list (may have 1 or 2 entries depending on DOI registration)
        assert isinstance(metadata, list)
        # At least one source should return data
        assert len(metadata) >= 1
        # If DataCite DOI is not in CrossRef, should only have DataCite result
        sources = [m["source"] for m in metadata]
        assert "DataCite" in sources

    def test_all_method_crossref_doi(self):
        """Test all method with CrossRef DOI (should query both sources)"""
        metadata = external_metadata.get_external_metadata(
            self.CROSSREF_DOI, method="all"
        )

        # Should return a list (may have 1 or 2 entries depending on DOI registration)
        assert isinstance(metadata, list)
        # At least one source should return data
        assert len(metadata) >= 1
        # Should have CrossRef result
        sources = [m["source"] for m in metadata]
        assert "CrossRef" in sources

    def test_wrong_source_returns_empty_list(self):
        """Test that querying wrong source returns empty list"""
        # Try to get DataCite DOI from CrossRef only
        metadata = external_metadata.get_external_metadata(
            self.DATACITE_DOI, method="crossref"
        )

        # Should return empty list
        assert isinstance(metadata, list)
        assert len(metadata) == 0

    def test_invalid_doi_returns_empty_list(self):
        """Test that invalid DOI returns empty list"""
        metadata = external_metadata.get_external_metadata(
            "10.invalid/fake.doi", method="auto"
        )

        # Should return empty list
        assert isinstance(metadata, list)
        assert len(metadata) == 0

    def test_doi_url_format(self):
        """Test that DOI URLs are correctly parsed"""
        # Test with DOI URL
        metadata = external_metadata.get_external_metadata(
            f"https://doi.org/{self.DATACITE_DOI}", method="datacite"
        )

        assert isinstance(metadata, list)
        assert len(metadata) == 1
        assert metadata[0]["doi"] == self.DATACITE_DOI

    def test_doi_prefix_format(self):
        """Test that doi: prefix is correctly parsed"""
        # Test with doi: prefix
        metadata = external_metadata.get_external_metadata(
            f"doi:{self.DATACITE_DOI}", method="datacite"
        )

        assert isinstance(metadata, list)
        assert len(metadata) == 1
        assert metadata[0]["doi"] == self.DATACITE_DOI


class TestExternalMetadataWithFromRemote:
    """Test external metadata integration with fromRemote API"""

    DATACITE_DOI = "10.5281/zenodo.4593540"  # Zenodo (DataCite)

    def test_fromremote_with_ext_metadata_auto(self):
        """Test fromRemote with ext_metadata=True and method=auto"""
        result = geoextent.fromRemote(
            self.DATACITE_DOI,
            bbox=True,
            ext_metadata=True,
            ext_metadata_method="auto",
            download_data=False,
        )

        # Should have external_metadata field
        assert "external_metadata" in result
        assert isinstance(result["external_metadata"], list)
        assert len(result["external_metadata"]) >= 1
        assert result["external_metadata"][0]["source"] == "DataCite"

    def test_fromremote_with_ext_metadata_datacite(self):
        """Test fromRemote with ext_metadata=True and method=datacite"""
        result = geoextent.fromRemote(
            self.DATACITE_DOI,
            bbox=True,
            ext_metadata=True,
            ext_metadata_method="datacite",
            download_data=False,
        )

        # Should have external_metadata field
        assert "external_metadata" in result
        assert isinstance(result["external_metadata"], list)
        assert len(result["external_metadata"]) == 1
        assert result["external_metadata"][0]["source"] == "DataCite"

    def test_fromremote_with_ext_metadata_crossref_empty(self):
        """Test fromRemote with wrong source returns empty array"""
        result = geoextent.fromRemote(
            self.DATACITE_DOI,
            bbox=True,
            ext_metadata=True,
            ext_metadata_method="crossref",
            download_data=False,
        )

        # Should have external_metadata field even if empty
        assert "external_metadata" in result
        assert isinstance(result["external_metadata"], list)
        assert len(result["external_metadata"]) == 0

    def test_fromremote_with_ext_metadata_all(self):
        """Test fromRemote with ext_metadata=True and method=all"""
        result = geoextent.fromRemote(
            self.DATACITE_DOI,
            bbox=True,
            ext_metadata=True,
            ext_metadata_method="all",
            download_data=False,
        )

        # Should have external_metadata field
        assert "external_metadata" in result
        assert isinstance(result["external_metadata"], list)
        # Should have at least DataCite result
        assert len(result["external_metadata"]) >= 1
        sources = [m["source"] for m in result["external_metadata"]]
        assert "DataCite" in sources

    def test_fromremote_without_ext_metadata(self):
        """Test fromRemote without ext_metadata flag"""
        result = geoextent.fromRemote(
            self.DATACITE_DOI, bbox=True, ext_metadata=False, download_data=False
        )

        # Should NOT have external_metadata field
        assert "external_metadata" not in result

    def test_fromremote_metadata_array_structure(self):
        """Test that external_metadata is always an array with correct structure"""
        result = geoextent.fromRemote(
            self.DATACITE_DOI,
            bbox=True,
            ext_metadata=True,
            ext_metadata_method="datacite",
            download_data=False,
        )

        # Verify structure
        assert isinstance(result["external_metadata"], list)
        for metadata in result["external_metadata"]:
            assert isinstance(metadata, dict)
            assert "source" in metadata
            assert "doi" in metadata
            assert "title" in metadata
            assert "authors" in metadata
            assert isinstance(metadata["authors"], list)
            assert "publisher" in metadata
            assert "publication_year" in metadata
            assert isinstance(metadata["publication_year"], int)
            assert "url" in metadata
