"""Tests for parallel file extraction (-p / --parallel, workers parameter)."""

import pytest
import subprocess
import sys

from geoextent.lib import extent

# Expected values from existing test_api.py (EPSG:4326 native order: [lat, lon])
FOLDER_TWO_FILES_BBOX = [41.317038, 2.052333, 51.974624, 7.647256]
FOLDER_TWO_FILES_TBOX = ["2018-11-14", "2019-09-11"]

FOLDER_ONE_FILE_BBOX = [51.948814, 7.601680, 51.974624, 7.647256]
FOLDER_ONE_FILE_TBOX = ["2018-11-14", "2018-11-14"]

NESTED_FOLDER_BBOX = [34.7, 7.601680, 51.974624, 142.0]
NESTED_FOLDER_TBOX = ["2017-04-08", "2020-02-06"]


def _approx_bbox(bbox, abs_tol=0.01):
    return [pytest.approx(v, abs=abs_tol) for v in bbox]


class TestParallelMatchesSequential:
    """Verify parallel extraction produces identical results to sequential."""

    def test_parallel_matches_sequential(self):
        path = "tests/testdata/folders/folder_two_files"
        sequential = extent.from_directory(path, bbox=True, tbox=True, workers=1)
        parallel = extent.from_directory(path, bbox=True, tbox=True, workers=2)

        assert sequential["bbox"] == _approx_bbox(FOLDER_TWO_FILES_BBOX)
        assert parallel["bbox"] == _approx_bbox(FOLDER_TWO_FILES_BBOX)
        assert sequential["tbox"] == FOLDER_TWO_FILES_TBOX
        assert parallel["tbox"] == FOLDER_TWO_FILES_TBOX

    def test_parallel_single_file_fallback(self):
        """workers=4 with a single file should fall back to sequential gracefully."""
        path = "tests/testdata/folders/folder_one_file"
        result = extent.from_directory(path, bbox=True, tbox=True, workers=4)

        assert result["bbox"] == _approx_bbox(FOLDER_ONE_FILE_BBOX)
        assert result["tbox"] == FOLDER_ONE_FILE_TBOX

    def test_parallel_nested_folder(self):
        path = "tests/testdata/folders/nested_folder"
        result = extent.from_directory(
            path, bbox=True, tbox=True, workers=2, show_progress=False
        )

        assert result["bbox"] == _approx_bbox(NESTED_FOLDER_BBOX)
        assert result["tbox"] == NESTED_FOLDER_TBOX


class TestParallelDetails:
    """Verify details and convex_hull work with parallel extraction."""

    def test_parallel_with_details(self):
        path = "tests/testdata/folders/folder_two_files"
        result = extent.from_directory(
            path, bbox=True, tbox=True, details=True, workers=2
        )

        assert "details" in result
        assert len(result["details"]) > 0
        # All files from the directory should be in details
        for filename, file_meta in result["details"].items():
            assert file_meta is not None

    def test_parallel_with_convex_hull(self):
        path = "tests/testdata/folders/folder_two_files"
        result = extent.from_directory(
            path, bbox=True, convex_hull=True, workers=2, show_progress=False
        )

        assert "bbox" in result
        assert result["bbox"] is not None


class TestParallelWorkersZero:
    """Verify workers=0 resolves to auto-detect."""

    def test_workers_zero_resolves(self):
        path = "tests/testdata/folders/folder_two_files"
        result = extent.from_directory(
            path, bbox=True, tbox=True, workers=0, show_progress=False
        )

        assert result["bbox"] == _approx_bbox(FOLDER_TWO_FILES_BBOX)
        assert result["tbox"] == FOLDER_TWO_FILES_TBOX


class TestParallelCLI:
    """Verify CLI -p flag works."""

    def test_cli_parallel_flag(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "geoextent",
                "-p",
                "2",
                "-b",
                "-t",
                "--no-progress",
                "tests/testdata/folders/folder_two_files",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0
        assert "FeatureCollection" in result.stdout

    def test_cli_parallel_auto(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "geoextent",
                "-p",
                "-b",
                "-t",
                "--no-progress",
                "tests/testdata/folders/folder_two_files",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0
        assert "FeatureCollection" in result.stdout
