"""Tests for automatic metadata fallback when data download yields no files.

Fast validation tests (no network) and network tests for GKHub packages
where files are disabled but metadata is available.
"""

import inspect

import pytest

import geoextent.lib.extent as geoextent
from conftest import NETWORK_SKIP_EXCEPTIONS

# ---------------------------------------------------------------------------
# Fast validation tests (no network, not marked slow)
# ---------------------------------------------------------------------------


def test_metadata_fallback_default_validation():
    """Verify fromRemote has metadata_fallback parameter with default True."""
    sig = inspect.signature(geoextent.fromRemote)
    param = sig.parameters.get("metadata_fallback")
    assert param is not None, "fromRemote should have a metadata_fallback parameter"
    assert param.default is True, "metadata_fallback should default to True"


def test_no_metadata_fallback_cli_flag_validation():
    """Verify argparse registers --no-metadata-fallback correctly."""
    from geoextent.__main__ import get_arg_parser

    parser = get_arg_parser()
    # Parse with --no-metadata-fallback
    args = parser.parse_args(
        [
            "--no-metadata-fallback",
            "-b",
            "tests/testdata/geojson/muenster_ring_zeit.geojson",
        ]
    )
    assert args.metadata_fallback is False

    # Parse without flag (default True)
    args_default = parser.parse_args(
        ["-b", "tests/testdata/geojson/muenster_ring_zeit.geojson"]
    )
    assert args_default.metadata_fallback is True


# ---------------------------------------------------------------------------
# Network tests (auto-marked slow by conftest)
# ---------------------------------------------------------------------------


def test_gkhub_package_metadata_fallback():
    """GKHub package with files disabled should fall back to metadata extraction.

    The package https://gkhub.earthobservations.org/packages/msaw9-hzd25
    has "files": {"enabled": false}, so data download yields no files.
    With metadata_fallback=True (default), geoextent should automatically
    fall back to metadata-only extraction and return a bounding box.
    """
    try:
        result = geoextent.fromRemote(
            "https://gkhub.earthobservations.org/packages/msaw9-hzd25",
            bbox=True,
            tbox=False,
        )
    except NETWORK_SKIP_EXCEPTIONS as e:
        pytest.skip(f"Network error: {e}")

    assert result is not None
    assert "bbox" in result, "Should have bbox from metadata fallback"
    assert result["bbox"] is not None, "bbox should not be None"
    assert result.get("extraction_method") == "metadata_fallback"


def test_gkhub_package_no_metadata_fallback():
    """GKHub package with metadata_fallback=False should return no bbox.

    Without metadata fallback, the empty download folder produces no spatial extent.
    """
    try:
        result = geoextent.fromRemote(
            "https://gkhub.earthobservations.org/packages/msaw9-hzd25",
            bbox=True,
            tbox=False,
            metadata_fallback=False,
        )
    except NETWORK_SKIP_EXCEPTIONS as e:
        pytest.skip(f"Network error: {e}")

    assert result is not None
    # With fallback disabled, no data files means no bbox
    assert result.get("bbox") is None, "Should have no bbox without metadata fallback"
    assert result.get("extraction_method") != "metadata_fallback"
