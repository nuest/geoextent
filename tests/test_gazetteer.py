"""Unit tests for pure/deterministic functions in gazetteer.py.

Tests cover string manipulation (find_shared_components) and input validation
without requiring network access or geocoder API keys.
"""

import pytest
from geoextent.lib.gazetteer import GazetteerService, PlacenameExtractor


# ---------------------------------------------------------------------------
# GazetteerService.find_shared_components
# ---------------------------------------------------------------------------
class TestFindSharedComponents:
    """Test the pure string-manipulation logic in find_shared_components."""

    def setup_method(self):
        # GazetteerService is abstract, but find_shared_components is concrete
        self.svc = GazetteerService.__new__(GazetteerService)

    def test_empty_list(self):
        assert self.svc.find_shared_components([]) is None

    def test_all_none(self):
        assert self.svc.find_shared_components([None, None, None]) is None

    def test_single_name(self):
        assert self.svc.find_shared_components(["Berlin, Germany"]) == "Berlin, Germany"

    def test_shared_component(self):
        result = self.svc.find_shared_components(["Berlin, Germany", "Munich, Germany"])
        assert result is not None
        assert "Germany" in result

    def test_no_shared_returns_shortest(self):
        result = self.svc.find_shared_components(["Berlin", "Tokyo"])
        assert result is not None
        # Falls back to shortest name
        assert result == "Tokyo"

    def test_multiple_shared(self):
        result = self.svc.find_shared_components(["A, B, C", "D, B, C"])
        assert "B" in result
        assert "C" in result

    def test_semicolon_delimiter(self):
        result = self.svc.find_shared_components(["Berlin; Germany", "Munich; Germany"])
        assert "Germany" in result

    def test_slash_delimiter(self):
        result = self.svc.find_shared_components(["Berlin/Germany", "Munich/Germany"])
        assert "Germany" in result

    def test_pipe_delimiter(self):
        result = self.svc.find_shared_components(["Berlin|Germany", "Munich|Germany"])
        assert "Germany" in result

    def test_mixed_none_values(self):
        result = self.svc.find_shared_components([None, "Berlin, Germany", None])
        assert result == "Berlin, Germany"


# ---------------------------------------------------------------------------
# PlacenameExtractor.__init__ validation
# ---------------------------------------------------------------------------
class TestPlacenameExtractorInit:
    def test_invalid_service_raises(self):
        with pytest.raises(ValueError, match="Unsupported gazetteer service"):
            PlacenameExtractor("invalid_service")

    def test_error_message_lists_services(self):
        with pytest.raises(ValueError) as exc_info:
            PlacenameExtractor("invalid_service")
        msg = str(exc_info.value)
        assert "geonames" in msg
        assert "nominatim" in msg
        assert "photon" in msg


# ---------------------------------------------------------------------------
# PlacenameExtractor.extract_placename_from_bbox input validation
# ---------------------------------------------------------------------------
class TestExtractPlacenameFromBboxValidation:
    """Test input validation without requiring network/geocoder setup."""

    def setup_method(self):
        # Create a PlacenameExtractor without calling __init__
        # to avoid requiring geocoder API credentials
        self.extractor = PlacenameExtractor.__new__(PlacenameExtractor)

    def test_none_bbox(self):
        result = self.extractor.extract_placename_from_bbox(None)
        assert result is None

    def test_wrong_length_bbox(self):
        result = self.extractor.extract_placename_from_bbox([1, 2, 3])
        assert result is None
