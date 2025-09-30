"""Tests for parallel download functionality."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from geoextent.lib.content_providers.providers import DoiProvider, ParallelDownloadManager


class TestParallelDownloadManager:
    """Test the ParallelDownloadManager class."""

    def test_parallel_download_manager_basic(self):
        """Test basic ParallelDownloadManager functionality."""
        # Create a test manager
        manager = ParallelDownloadManager(max_workers=2)

        # Mock download tasks
        tasks = [
            ("http://example.com/file1.txt", "/tmp/file1.txt", 100),
            ("http://example.com/file2.txt", "/tmp/file2.txt", 200),
            ("http://example.com/file3.txt", "/tmp/file3.txt", 150),
        ]

        # Mock the download method to just return the size
        def mock_download(task):
            url, filepath, size = task
            return size

        manager._download_single_file = mock_download

        # Test parallel download
        results = manager.download_files_parallel(tasks)

        # Verify results
        assert len(results) == 3, "Should have 3 results"
        for result in results:
            assert result['success'] == True, "All downloads should succeed"
            assert result['bytes_downloaded'] > 0, "Should have downloaded bytes"

    def test_parallel_download_manager_sequential_fallback(self):
        """Test that manager falls back to sequential when max_workers=1."""
        manager = ParallelDownloadManager(max_workers=1)
        tasks = [("url1", "file1", 100), ("url2", "file2", 200)]

        # Mock the download method
        def mock_download(task):
            return task[2]  # Return the size

        manager._download_single_file = mock_download

        # Should use sequential download
        results = manager.download_files_parallel(tasks)

        assert len(results) == 2, "Should have 2 results"
        for result in results:
            assert result['success'] == True, "All downloads should succeed"

    def test_parallel_download_error_handling(self):
        """Test error handling in parallel downloads."""
        manager = ParallelDownloadManager(max_workers=2)

        # Mock download method that fails for one file
        def mock_download(task):
            url, filepath, size = task
            if "fail" in filepath:
                raise Exception("Download failed")
            return size

        manager._download_single_file = mock_download

        tasks = [
            ("url1", "success.txt", 100),
            ("url2", "fail.txt", 200),
        ]

        results = manager.download_files_parallel(tasks)

        assert len(results) == 2, "Should have 2 results"
        assert results[0]['success'] != results[1]['success'], "One should succeed, one should fail"

        # Find the failed result
        failed_result = next(r for r in results if not r['success'])
        assert failed_result['error'] == "Download failed", "Should have error message"
        assert failed_result['bytes_downloaded'] == 0, "Failed download should have 0 bytes"


class TestDoiProviderParallel:
    """Test parallel download functionality in DoiProvider."""

    def test_should_use_parallel_downloads(self):
        """Test the logic for determining when to use parallel downloads."""
        provider = DoiProvider()

        # Test cases where parallel should NOT be used
        # Single file
        files = [{"name": "single.txt", "size": 10000000}]  # 10MB
        assert not provider._should_use_parallel_downloads(files, 4), "Single file should not use parallel"

        # max_workers = 1
        files = [{"name": "file1.txt", "size": 5000000}, {"name": "file2.txt", "size": 5000000}]
        assert not provider._should_use_parallel_downloads(files, 1), "max_workers=1 should not use parallel"

        # Too many files
        files = [{"name": f"file{i}.txt", "size": 1000} for i in range(25)]
        assert not provider._should_use_parallel_downloads(files, 4), "Too many files should not use parallel"

        # Small total size and small average file size
        files = [{"name": "small1.txt", "size": 1000}, {"name": "small2.txt", "size": 2000}]
        assert not provider._should_use_parallel_downloads(files, 4), "Small files should not use parallel"

        # Test cases where parallel SHOULD be used
        # Large total size
        files = [{"name": "big1.txt", "size": 6000000}, {"name": "big2.txt", "size": 6000000}]  # 12MB total
        assert provider._should_use_parallel_downloads(files, 4), "Large total size should use parallel"

        # Large average file size
        files = [{"name": "big1.txt", "size": 2000000}, {"name": "big2.txt", "size": 2000000}]  # 2MB each
        assert provider._should_use_parallel_downloads(files, 4), "Large average file size should use parallel"

    def test_download_files_batch_basic(self):
        """Test the batch download functionality."""
        provider = DoiProvider()

        # Mock the optimized download method
        def mock_download(url, filepath, chunk_size=None, show_progress=False):
            # Create a small file to simulate download
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write("test content")
            return len("test content")

        provider._download_file_optimized = mock_download

        # Create test files
        files = [
            {"name": "test1.txt", "url": "http://example.com/test1.txt", "size": 100},
            {"name": "test2.txt", "url": "http://example.com/test2.txt", "size": 200},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test batch download
            results = provider._download_files_batch(
                files,
                temp_dir,
                show_progress=False,
                max_workers=2
            )

            # Verify results
            assert len(results) == 2, "Should have 2 results"
            for result in results:
                assert result['success'] == True, "All downloads should succeed"

            # Verify files were created
            assert os.path.exists(os.path.join(temp_dir, "test1.txt")), "test1.txt should exist"
            assert os.path.exists(os.path.join(temp_dir, "test2.txt")), "test2.txt should exist"

    def test_download_files_batch_with_different_url_formats(self):
        """Test batch download with different URL key formats."""
        provider = DoiProvider()

        def mock_download(url, filepath, chunk_size=None, show_progress=False):
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(f"content from {url}")
            return len(f"content from {url}")

        provider._download_file_optimized = mock_download

        # Test different URL key formats that providers might use
        files = [
            {"name": "test1.txt", "url": "http://example.com/test1.txt", "size": 100},
            {"name": "test2.txt", "download_url": "http://example.com/test2.txt", "size": 200},
            {"name": "test3.txt", "link": "http://example.com/test3.txt", "size": 150},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            results = provider._download_files_batch(
                files,
                temp_dir,
                show_progress=False,
                max_workers=2
            )

            # All files should be downloaded successfully
            assert len(results) == 3, "Should have 3 results"
            for result in results:
                assert result['success'] == True, f"Download should succeed: {result}"


class TestCLIParallelIntegration:
    """Test CLI integration for parallel downloads."""

    def test_max_download_workers_cli_argument(self):
        """Test that --max-download-workers argument is properly parsed."""
        import argparse
        from geoextent.__main__ import get_arg_parser
        import tempfile

        parser = get_arg_parser()

        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
            tmp_file.write("test content")
            tmp_file_path = tmp_file.name

        try:
            # Test that the argument exists and works
            args = parser.parse_args(["--max-download-workers", "8", "-b", tmp_file_path])
            assert hasattr(args, "max_download_workers"), "Should have max_download_workers attribute"
            assert args.max_download_workers == 8, "Should set max_download_workers to 8"

            # Test default value
            args = parser.parse_args(["-b", tmp_file_path])
            assert args.max_download_workers == 4, "Should default to 4"

            # Test setting to 1 (disable parallel)
            args = parser.parse_args(["--max-download-workers", "1", "-b", tmp_file_path])
            assert args.max_download_workers == 1, "Should set max_download_workers to 1"

        finally:
            # Clean up
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)


class TestWarningMessages:
    """Test warning messages for unsupported filtering scenarios."""

    def test_dryad_filtering_support(self):
        """Test that Dryad now supports geospatial filtering."""
        from geoextent.lib.content_providers.Dryad import Dryad

        provider = Dryad()
        provider.reference = "https://datadryad.org/stash/dataset/doi:10.5061/dryad.example"

        # Mock the log to capture messages
        provider.log = Mock()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Call download with skip_nogeo=True - should now be supported
            provider.download(
                temp_dir,
                download_data=False,  # This will return early, avoiding actual download
                download_skip_nogeo=True,  # This should now be supported without warnings
                max_download_workers=4
            )

        # Check that NO warning about unsupported filtering was called
        warning_calls = [call for call in provider.log.warning.call_args_list
                        if "bulk ZIP downloads" in str(call) or "does not support" in str(call)]
        assert len(warning_calls) == 0, f"Should not warn about unsupported filtering, but got: {warning_calls}"

    def test_osf_filtering_support(self):
        """Test that OSF now supports geospatial filtering."""
        from geoextent.lib.content_providers.OSF import OSF

        provider = OSF()
        # Validate the provider first to set project_id
        provider.validate_provider("https://osf.io/9jg2u")

        # Mock the log to capture messages
        provider.log = Mock()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Call download with skip_nogeo=True - should now be supported
            provider.download(
                temp_dir,
                download_data=False,  # This will return early, avoiding actual download
                download_skip_nogeo=True,  # This should now be supported without warnings
                max_download_workers=4
            )

        # Check that NO warning about unsupported filtering was called
        warning_calls = [call for call in provider.log.warning.call_args_list
                        if "does not support selective file filtering" in str(call)]
        assert len(warning_calls) == 0, f"Should not warn about unsupported filtering, but got: {warning_calls}"

    def test_gfz_warning_for_skip_nogeo(self):
        """Test that GFZ warns when skip_nogeo is requested."""
        import logging
        from geoextent.lib.content_providers.GFZ import GFZ

        provider = GFZ()
        provider.reference = "https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=example"

        # Mock the logger to capture warnings
        logger_mock = Mock()

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('geoextent.lib.content_providers.GFZ.logger', logger_mock):
                provider.download(
                    temp_dir,
                    download_data=False,  # This will return early, avoiding actual download
                    download_skip_nogeo=True,  # This should trigger warning
                    max_download_workers=4
                )

        # Check that warning was called
        logger_mock.warning.assert_called()
        warning_calls = [call for call in logger_mock.warning.call_args_list
                        if "does not support selective file filtering" in str(call)]
        assert len(warning_calls) > 0, "Should have warned about lack of filtering support"