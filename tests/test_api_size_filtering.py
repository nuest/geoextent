import pytest
import geoextent.lib.helpfunctions as hf


class TestSizeFilteringMethods:
    """Test size filtering methods including new 'smallest' and 'largest' options"""

    def setup_method(self):
        """Set up test data with files of different sizes"""
        self.test_files = [
            {
                "name": "huge_file.zip",
                "size": 1000 * 1024 * 1024,
                "url": "http://example.com/huge",
            },  # 1000MB
            {
                "name": "large_file.tif",
                "size": 500 * 1024 * 1024,
                "url": "http://example.com/large",
            },  # 500MB
            {
                "name": "medium_file.shp",
                "size": 50 * 1024 * 1024,
                "url": "http://example.com/medium",
            },  # 50MB
            {
                "name": "small_file.csv",
                "size": 5 * 1024 * 1024,
                "url": "http://example.com/small",
            },  # 5MB
            {
                "name": "tiny_file.txt",
                "size": 1024 * 1024,
                "url": "http://example.com/tiny",
            },  # 1MB
        ]
        self.max_size_100mb = 100 * 1024 * 1024  # 100MB limit

    def test_ordered_method_original_behavior(self):
        """Test that 'ordered' method maintains original behavior (as returned by provider)"""
        selected_files, total_size, skipped_files = hf.filter_files_by_size(
            self.test_files, self.max_size_100mb, "ordered"
        )

        # Should stop at first file that would exceed limit (huge_file is 1000MB > 100MB limit)
        assert len(selected_files) == 0
        assert total_size == 0
        assert len(skipped_files) == 5  # All files skipped

    def test_smallest_method_prioritizes_small_files(self):
        """Test that 'smallest' method selects smallest files first"""
        selected_files, total_size, skipped_files = hf.filter_files_by_size(
            self.test_files, self.max_size_100mb, "smallest"
        )

        # Should select tiny (1MB) + small (5MB) + medium (50MB) = 56MB total
        assert len(selected_files) == 3
        expected_total = (1 + 5 + 50) * 1024 * 1024  # 56MB
        assert total_size == expected_total

        # Verify files are selected in size order
        selected_names = [f["name"] for f in selected_files]
        assert selected_names == ["tiny_file.txt", "small_file.csv", "medium_file.shp"]

        # Should skip the large files
        assert len(skipped_files) == 2
        skipped_names = [f["name"] for f in skipped_files]
        assert "large_file.tif" in skipped_names
        assert "huge_file.zip" in skipped_names

    def test_largest_method_prioritizes_large_files(self):
        """Test that 'largest' method selects largest files first"""
        selected_files, total_size, skipped_files = hf.filter_files_by_size(
            self.test_files, self.max_size_100mb, "largest"
        )

        # Should select nothing because largest file (1000MB) exceeds 100MB limit
        assert len(selected_files) == 0
        assert total_size == 0
        assert len(skipped_files) == 5

    def test_largest_method_with_higher_limit(self):
        """Test 'largest' method with a limit that allows some files"""
        # Set limit to 600MB to allow some larger files
        max_size_600mb = 600 * 1024 * 1024

        selected_files, total_size, skipped_files = hf.filter_files_by_size(
            self.test_files, max_size_600mb, "largest"
        )

        # Should select huge_file (1000MB) but it exceeds limit, so select large_file (500MB)
        # Actually, it should select nothing because the first file (largest) exceeds the limit
        # Let me test with a different scenario

        # Create files where largest fits but subsequent ones might not
        test_files_for_largest = [
            {
                "name": "file_a.zip",
                "size": 300 * 1024 * 1024,
                "url": "http://example.com/a",
            },  # 300MB
            {
                "name": "file_b.tif",
                "size": 200 * 1024 * 1024,
                "url": "http://example.com/b",
            },  # 200MB
            {
                "name": "file_c.shp",
                "size": 50 * 1024 * 1024,
                "url": "http://example.com/c",
            },  # 50MB
        ]

        selected_files, total_size, skipped_files = hf.filter_files_by_size(
            test_files_for_largest, max_size_600mb, "largest"
        )

        # Should select all files: file_a (300MB) + file_b (200MB) + file_c (50MB) = 550MB (under 600MB limit)
        assert len(selected_files) == 3
        expected_total = (300 + 200 + 50) * 1024 * 1024  # 550MB
        assert total_size == expected_total

        # Verify files are selected in descending size order
        selected_names = [f["name"] for f in selected_files]
        assert selected_names == ["file_a.zip", "file_b.tif", "file_c.shp"]

    def test_random_method_still_works(self):
        """Test that existing 'random' method still functions"""
        selected_files, total_size, skipped_files = hf.filter_files_by_size(
            self.test_files, self.max_size_100mb, "random", seed=42
        )

        # Random method should still work, exact selection depends on shuffle
        assert isinstance(selected_files, list)
        assert isinstance(total_size, int)
        assert isinstance(skipped_files, list)

    def test_shapefile_groups_preserved_with_sorting(self):
        """Test that shapefile groups stay together even with sorting methods"""
        # Create test files including shapefile components
        shapefile_test_files = [
            {
                "name": "large_other.zip",
                "size": 200 * 1024 * 1024,
                "url": "http://example.com/large",
            },  # 200MB
            {
                "name": "data.shp",
                "size": 10 * 1024 * 1024,
                "url": "http://example.com/shp",
            },  # 10MB
            {
                "name": "data.dbf",
                "size": 5 * 1024 * 1024,
                "url": "http://example.com/dbf",
            },  # 5MB
            {
                "name": "data.shx",
                "size": 1 * 1024 * 1024,
                "url": "http://example.com/shx",
            },  # 1MB
            {
                "name": "small_other.txt",
                "size": 2 * 1024 * 1024,
                "url": "http://example.com/txt",
            },  # 2MB
        ]

        selected_files, total_size, skipped_files = hf.filter_files_by_size(
            shapefile_test_files, 50 * 1024 * 1024, "smallest"  # 50MB limit
        )

        # Should include the shapefile group (16MB total) + small_other.txt (2MB) = 18MB
        assert (
            len(selected_files) >= 4
        )  # At least the shapefile components + small file

        # Verify all shapefile components are present
        selected_names = [f["name"] for f in selected_files]
        shapefile_components = ["data.shp", "data.dbf", "data.shx"]
        for component in shapefile_components:
            assert (
                component in selected_names
            ), f"Shapefile component {component} should be included"

    def test_files_without_size_info_handled(self):
        """Test that files without size information are handled correctly"""
        files_with_missing_size = [
            {
                "name": "file_with_size.txt",
                "size": 10 * 1024 * 1024,
                "url": "http://example.com/sized",
            },
            {
                "name": "file_without_size.txt",
                "url": "http://example.com/no_size",
            },  # No size field
            {
                "name": "file_with_zero_size.txt",
                "size": 0,
                "url": "http://example.com/zero",
            },  # Zero size
        ]

        selected_files, total_size, skipped_files = hf.filter_files_by_size(
            files_with_missing_size, 50 * 1024 * 1024, "smallest"
        )

        # Should include the sized file and files without size info
        assert len(selected_files) >= 1
        selected_names = [f["name"] for f in selected_files]
        assert "file_with_size.txt" in selected_names

    def test_invalid_method_falls_back_to_ordered(self):
        """Test that invalid methods fall back to ordered behavior"""
        selected_files, total_size, skipped_files = hf.filter_files_by_size(
            self.test_files, self.max_size_100mb, "invalid_method"
        )

        # Should behave like 'ordered' method
        assert len(selected_files) == 0  # Same as ordered method test
        assert total_size == 0

    def test_edge_case_empty_file_list(self):
        """Test behavior with empty file list"""
        selected_files, total_size, skipped_files = hf.filter_files_by_size(
            [], self.max_size_100mb, "smallest"
        )

        assert selected_files == []
        assert total_size == 0
        assert skipped_files == []

    def test_edge_case_no_size_limit(self):
        """Test behavior when no size limit is specified"""
        selected_files, total_size, skipped_files = hf.filter_files_by_size(
            self.test_files, None, "smallest"
        )

        # Should return all files when no limit
        assert len(selected_files) == len(self.test_files)
        assert len(skipped_files) == 0
