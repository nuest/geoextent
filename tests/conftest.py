"""Shared test configuration and automatic test markers.

Tests from repository provider files that make network calls are auto-marked as 'slow'.
Validation-only tests (DOI patterns, URL validation, provider instantiation) remain unmarked.

One representative test per provider is additionally marked as 'provider_sample' for
lightweight CI smoke-testing of provider connectivity.

Usage:
    pytest                          # Fast tests only (default, excludes slow & large_download)
    pytest -m provider_sample       # One real-network test per provider (~11 tests)
    pytest -m "not large_download"  # All tests except large downloads
    pytest -m slow                  # Only slow network tests
"""

import pytest
import requests

# Exceptions that indicate a network/connectivity issue (not a code bug).
# Use this in tests to skip on transient network failures without hiding real errors.
NETWORK_SKIP_EXCEPTIONS = (
    requests.RequestException,
    ConnectionError,
    TimeoutError,
    OSError,
)

# Repository provider test files that contain network-dependent tests
_PROVIDER_FILES = {
    "test_api_zenodo.py",
    "test_api_pangaea.py",
    "test_api_osf.py",
    "test_api_dataverse.py",
    "test_api_gfz.py",
    "test_api_pensoft.py",
    "test_api_opara.py",
    "test_api_senckenberg.py",
    "test_api_figshare.py",
    "test_api_dryad.py",
    "test_api_bgr.py",
    "test_api_mendeley_data.py",
    "test_api_ioer_data.py",
    "test_api_heidata.py",
    "test_api_edmond.py",
    "test_api_wikidata.py",
    "test_api_fourtu.py",
    "test_metadata_first.py",
    "test_external_metadata.py",
    "test_remote_single.py",
    "test_remote_multi.py",
    "test_parallel_downloads.py",
    "test_placename_real.py",
    "test_multiple_repositories.py",
    "test_cli_parameter_combinations.py",
    "test_doi_url_support.py",
}

# Test name patterns that are fast (validation-only, no network)
_FAST_PATTERNS = {
    "validation",
    "url_validation",
    "doi_validation",
    "url_patterns",
    "invalid_identifiers",
    "provider_instantiation",
    "known_host",
    "doi_pattern_recognition",
    "can_be_used",
    "parse_wkt_point",
    "extract_coordinates",
    "mutually_exclusive",
    "supports_metadata_extraction",
}

# One representative real-network test per provider for smoke-testing.
# These are lightweight metadata-only tests that still make actual API calls.
_PROVIDER_SAMPLE_TESTS = {
    "test_zenodo_metadata_only_extraction",
    "test_pangaea_repository_extraction_oceanography_dataset",
    "test_osf_metadata_extraction",
    "test_real_dataset_metadata_extraction",
    "test_gfz_metadata_only_extraction",
    "test_pensoft_coordinate_extraction",
    "test_opara_metadata_retrieval",
    "test_senckenberg_metadata_retrieval",
    "test_figshare_metadata_only_extraction",
    "test_dryad_metadata_only_extraction",
    "test_bgr_metadata_only_extraction",
    "test_mendeley_data_metadata_only_extraction",
    "test_ioer_data_metadata_only_extraction",
    "test_heidata_metadata_only_extraction",
    "test_edmond_metadata_only_extraction",
    "test_wikidata_metadata_only_extraction",
    "test_fourtu_metadata_only_extraction",
}


def pytest_collection_modifyitems(config, items):
    """Auto-mark slow tests based on file and test name patterns."""
    slow_marker = pytest.mark.slow
    provider_sample_marker = pytest.mark.provider_sample

    for item in items:
        # Get the test file name
        filename = item.fspath.basename if hasattr(item.fspath, "basename") else ""

        if filename in _PROVIDER_FILES:
            # Check if this specific test is a fast validation test
            test_name = item.name.lower()
            is_fast = any(pattern in test_name for pattern in _FAST_PATTERNS)

            if not is_fast:
                item.add_marker(slow_marker)

                # Mark representative provider sample tests
                if item.originalname in _PROVIDER_SAMPLE_TESTS:
                    item.add_marker(provider_sample_marker)
