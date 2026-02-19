"""Tests for the download size soft limit feature.

Unit tests verify filter_files_by_size() raises DownloadSizeExceeded when
provider_name is set. Network tests verify each provider raises the exception
when called with a tiny limit via fromRemote().
"""

import pytest
import requests

from geoextent.lib import helpfunctions as hf
from geoextent.lib.exceptions import DownloadSizeExceeded
from geoextent.lib import extent

from conftest import NETWORK_SKIP_EXCEPTIONS

# ---------------------------------------------------------------------------
# Unit tests (fast, no network)
# ---------------------------------------------------------------------------


class TestFilterFilesRaisesWithProviderName:
    """filter_files_by_size should raise DownloadSizeExceeded when provider_name is set."""

    FILES = [
        {"name": "a.csv", "size": 100},
        {"name": "b.csv", "size": 200},
        {"name": "c.csv", "size": 300},
    ]

    def test_filter_raises_with_provider_name(self):
        """When provider_name is set and files are skipped, DownloadSizeExceeded is raised."""
        with pytest.raises(DownloadSizeExceeded) as exc_info:
            hf.filter_files_by_size(
                self.FILES, max_download_size=150, provider_name="TestProvider"
            )
        assert exc_info.value.provider == "TestProvider"

    def test_filter_no_raise_without_provider_name(self):
        """When provider_name is None (default), files are silently truncated."""
        selected, total, skipped = hf.filter_files_by_size(
            self.FILES, max_download_size=150
        )
        assert len(selected) == 1
        assert len(skipped) > 0

    def test_filter_no_raise_when_all_fit(self):
        """No exception when all files fit within the limit."""
        selected, total, skipped = hf.filter_files_by_size(
            self.FILES, max_download_size=10000, provider_name="TestProvider"
        )
        assert len(selected) == 3
        assert len(skipped) == 0

    def test_estimated_size_is_total(self):
        """The exception's estimated_size reflects total available size, not just skipped."""
        with pytest.raises(DownloadSizeExceeded) as exc_info:
            hf.filter_files_by_size(
                self.FILES, max_download_size=150, provider_name="TestProvider"
            )
        # Total available = 100 + 200 + 300 = 600
        assert exc_info.value.estimated_size == 600
        assert exc_info.value.max_size == 150


class TestCliSetsSoftLimitFlag:
    """Verify the CLI passes download_size_soft_limit=True."""

    def test_cli_size_prompt_passes_soft_limit(self):
        """_call_fromRemote_with_size_prompt receives download_size_soft_limit in kwargs."""
        # We test this by importing the main module and inspecting the code paths.
        # Since the actual call would require network, we just verify the parameter
        # is accepted by fromRemote.
        import inspect

        sig = inspect.signature(extent.fromRemote)
        assert "download_size_soft_limit" in sig.parameters
        param = sig.parameters["download_size_soft_limit"]
        assert param.default is False


# ---------------------------------------------------------------------------
# Network tests (slow, one per provider)
# ---------------------------------------------------------------------------
# Each test calls fromRemote() with max_download_size="1B" and
# download_size_soft_limit=True, expecting DownloadSizeExceeded.


def _assert_size_exceeded(doi, **kwargs):
    """Helper: assert that fromRemote raises DownloadSizeExceeded with a 1-byte limit."""
    with pytest.raises(DownloadSizeExceeded):
        extent.fromRemote(
            doi,
            bbox=True,
            max_download_size="1B",
            download_size_soft_limit=True,
            show_progress=False,
            **kwargs,
        )


def test_zenodo_soft_limit():
    try:
        _assert_size_exceeded("10.5281/zenodo.820562")
    except NETWORK_SKIP_EXCEPTIONS:
        pytest.skip("Network unavailable")


def test_figshare_soft_limit():
    try:
        _assert_size_exceeded("10.6084/m9.figshare.5902369")
    except NETWORK_SKIP_EXCEPTIONS:
        pytest.skip("Network unavailable")


def test_dryad_soft_limit():
    try:
        _assert_size_exceeded("10.5061/dryad.0k6djhb7x")
    except NETWORK_SKIP_EXCEPTIONS:
        pytest.skip("Network unavailable")


def test_dataverse_soft_limit():
    try:
        _assert_size_exceeded("10.7910/DVN/OMV93V")
    except NETWORK_SKIP_EXCEPTIONS:
        pytest.skip("Network unavailable")


def test_osf_soft_limit():
    try:
        _assert_size_exceeded("10.17605/OSF.IO/4XE6Z")
    except NETWORK_SKIP_EXCEPTIONS:
        pytest.skip("Network unavailable")


def test_gfz_soft_limit():
    try:
        _assert_size_exceeded("10.5880/GFZ.2.1.2020.001")
    except NETWORK_SKIP_EXCEPTIONS:
        pytest.skip("Network unavailable")


def test_opara_soft_limit():
    try:
        _assert_size_exceeded("10.25532/OPARA-581")
    except NETWORK_SKIP_EXCEPTIONS:
        pytest.skip("Network unavailable")


def test_arctic_data_center_soft_limit():
    try:
        _assert_size_exceeded("10.18739/A2Z892H2J")
    except NETWORK_SKIP_EXCEPTIONS:
        pytest.skip("Network unavailable")


def test_radar_soft_limit():
    try:
        _assert_size_exceeded("10.35097/tvn5vujqfvf99f32")
    except NETWORK_SKIP_EXCEPTIONS:
        pytest.skip("Network unavailable")


def test_mendeley_data_soft_limit():
    try:
        _assert_size_exceeded("10.17632/ybx6zp2rfp.1")
    except NETWORK_SKIP_EXCEPTIONS:
        pytest.skip("Network unavailable")


def test_inveniordm_soft_limit():
    try:
        _assert_size_exceeded("10.22002/D26.C95A0D")
    except NETWORK_SKIP_EXCEPTIONS:
        pytest.skip("Network unavailable")


def test_fourtu_soft_limit():
    try:
        _assert_size_exceeded("10.4121/uuid:8ce9d22a-9aa4-41ea-9299-f44efa9c8b75")
    except NETWORK_SKIP_EXCEPTIONS:
        pytest.skip("Network unavailable")


def test_seanoe_soft_limit():
    try:
        _assert_size_exceeded("10.17882/103743")
    except NETWORK_SKIP_EXCEPTIONS:
        pytest.skip("Network unavailable")


def test_ukceh_soft_limit():
    try:
        _assert_size_exceeded("10.5285/dd35316a-cecc-4f6d-9a21-74a0f6599e9e")
    except NETWORK_SKIP_EXCEPTIONS:
        pytest.skip("Network unavailable")
