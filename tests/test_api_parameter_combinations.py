import pytest
import geoextent.lib.extent as geoextent
import tempfile
import os
from help_functions_test import tolerance


class TestParameterCombinations:
    """Test various parameter combinations for geoextent functions"""

    def test_from_file_both_bbox_and_tbox_enabled(self):
        """Test from_file with both bbox and tbox enabled"""
        result = geoextent.from_file(
            "tests/testdata/geojson/muenster_ring_zeit.geojson", bbox=True, tbox=True
        )
        assert result is not None
        assert "bbox" in result
        assert "crs" in result
        # Note: This file may not have temporal data, which is fine

    def test_from_file_both_disabled_should_fail(self):
        """Test from_file with both bbox and tbox disabled should raise exception"""
        with pytest.raises(Exception, match="No extraction options enabled"):
            geoextent.from_file(
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
                bbox=False,
                tbox=False,
            )

    def test_from_file_only_bbox_enabled(self):
        """Test from_file with only bbox enabled"""
        result = geoextent.from_file(
            "tests/testdata/geojson/muenster_ring_zeit.geojson", bbox=True, tbox=False
        )
        assert result is not None
        assert "bbox" in result
        assert "crs" in result
        assert "tbox" not in result

    def test_from_file_only_tbox_enabled(self):
        """Test from_file with only tbox enabled"""
        # Use a GeoJSON file with temporal data
        result = geoextent.from_file(
            "tests/testdata/geojson/muenster_ring_zeit.geojson", bbox=False, tbox=True
        )
        assert result is not None
        # tbox might or might not be present depending on temporal data in the file
        assert "bbox" not in result
        assert "crs" not in result

    def test_from_file_csv_with_num_sample_parameter(self):
        """Test from_file with CSV file and num_sample parameter"""
        # Test with different num_sample values using an existing CSV file
        csv_file = "tests/testdata/csv/cities_NL_TIME.csv"
        result1 = geoextent.from_file(csv_file, bbox=True, tbox=True, num_sample=5)
        result2 = geoextent.from_file(csv_file, bbox=True, tbox=True, num_sample=10)
        result3 = geoextent.from_file(csv_file, bbox=True, tbox=True, num_sample=100)

        # All should succeed (num_sample affects internal processing but not final result significantly)
        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        # bbox might be present depending on CSV content
        if "bbox" in result1:
            assert "bbox" in result2
            assert "bbox" in result3

    def test_from_file_num_sample_ignored_for_non_csv(self):
        """Test that num_sample parameter is ignored for non-CSV files"""
        # Should work without error but num_sample should be ignored
        result = geoextent.from_file(
            "tests/testdata/geojson/muenster_ring_zeit.geojson",
            bbox=True,
            tbox=True,
            num_sample=10,
        )
        assert result is not None
        assert "bbox" in result

    def test_from_directory_both_bbox_and_tbox_enabled(self):
        """Test from_directory with both bbox and tbox enabled"""
        result = geoextent.from_directory(
            "tests/testdata/geojson", bbox=True, tbox=True
        )
        assert "bbox" in result
        assert "format" in result

    def test_from_directory_with_details_enabled(self):
        """Test from_directory with details parameter"""
        result = geoextent.from_directory(
            "tests/testdata/geojson", bbox=True, tbox=True, details=True
        )
        assert "details" in result
        assert isinstance(result["details"], dict)

    def test_from_directory_with_details_disabled(self):
        """Test from_directory with details disabled (default)"""
        result = geoextent.from_directory(
            "tests/testdata/geojson", bbox=True, tbox=True, details=False
        )
        assert "details" not in result

    def test_from_directory_both_disabled_should_fail(self):
        """Test from_directory with both bbox and tbox disabled should raise exception"""
        with pytest.raises(Exception, match="No extraction options enabled"):
            geoextent.from_directory("tests/testdata/geojson", bbox=False, tbox=False)

    def test_from_directory_only_bbox_enabled(self):
        """Test from_directory with only bbox enabled"""
        result = geoextent.from_directory(
            "tests/testdata/geojson", bbox=True, tbox=False
        )
        assert "bbox" in result
        assert "tbox" not in result

    def test_from_directory_only_tbox_enabled(self):
        """Test from_directory with only tbox enabled"""
        result = geoextent.from_directory("tests/testdata/csv", bbox=False, tbox=True)
        assert "tbox" in result
        assert "bbox" not in result

    def test_from_directory_with_timeout_parameter(self):
        """Test from_directory with timeout parameter"""
        # Use a reasonable timeout that shouldn't be reached
        result = geoextent.from_directory(
            "tests/testdata/geojson", bbox=True, tbox=True, timeout=30
        )
        assert "bbox" in result
        # timeout field should not be present if timeout wasn't reached
        assert "timeout" not in result

    def test_from_directory_with_very_short_timeout(self):
        """Test from_directory with very short timeout"""
        # Use a very short timeout that might be reached
        result = geoextent.from_directory(
            "tests/testdata", bbox=True, tbox=True, timeout=0.001
        )
        # Should either complete normally or include timeout field
        assert "format" in result
        # If timeout was reached, it should be indicated
        if "timeout" in result:
            assert result["timeout"] == 0.001

    def test_from_file_default_parameters(self):
        """Test from_file with default parameters (bbox=True, tbox=True)"""
        result = geoextent.from_file(
            "tests/testdata/geojson/muenster_ring_zeit.geojson"
        )
        # Default behavior should extract bbox
        assert "bbox" in result
        assert "crs" in result

    def test_from_directory_default_parameters(self):
        """Test from_directory with default parameters (bbox=False, tbox=False)"""
        # Default parameters should fail because both are False by default
        with pytest.raises(Exception, match="No extraction options enabled"):
            geoextent.from_directory("tests/testdata/geojson")


class TestEdgeCasesAndErrors:
    """Test edge cases and error conditions"""

    def test_from_file_nonexistent_file(self):
        """Test from_file with nonexistent file returns None"""
        result = geoextent.from_file("tests/testdata/nonexistent.file", bbox=True)
        assert result is None

    def test_from_file_directory_instead_of_file(self):
        """Test from_file with directory path instead of file"""
        result = geoextent.from_file("tests/testdata", bbox=True)
        assert result is None

    def test_from_directory_nonexistent_directory(self):
        """Test from_directory with nonexistent directory"""
        with pytest.raises(Exception):
            geoextent.from_directory("tests/nonexistent_directory", bbox=True)

    def test_from_directory_file_instead_of_directory(self):
        """Test from_directory with file path instead of directory raises error"""
        with pytest.raises((NotADirectoryError, FileNotFoundError)):
            geoextent.from_directory(
                "tests/testdata/geojson/muenster_ring_zeit.geojson", bbox=True
            )

    def test_from_file_empty_file_path(self):
        """Test from_file with empty file path returns None"""
        result = geoextent.from_file("", bbox=True)
        assert result is None

    def test_from_directory_empty_directory_path(self):
        """Test from_directory with empty directory path"""
        with pytest.raises(Exception):
            geoextent.from_directory("", bbox=True)

    def test_from_file_unsupported_file_format(self):
        """Test from_file with unsupported file format"""
        # Create a temporary file with unsupported extension
        with tempfile.NamedTemporaryFile(
            suffix=".unsupported", delete=False
        ) as tmp_file:
            tmp_file.write(b"some content")
            tmp_file_path = tmp_file.name

        try:
            result = geoextent.from_file(tmp_file_path, bbox=True)
            # The CSV handler may pick up arbitrary files but won't extract a bbox
            if result is not None:
                assert "bbox" not in result or result.get("bbox") is None
        finally:
            os.unlink(tmp_file_path)

    def test_from_directory_empty_directory(self):
        """Test from_directory with empty directory"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = geoextent.from_directory(tmp_dir, bbox=True)
            # Should handle empty directory gracefully
            assert "format" in result
            assert result["format"] == "folder"

    def test_from_file_csv_with_invalid_num_sample(self):
        """Test from_file with CSV and invalid num_sample values"""
        # Test with negative num_sample - still extracts bbox, just skips tbox sampling
        result1 = geoextent.from_file(
            "tests/testdata/csv/cities_NL_TIME.csv", bbox=True, tbox=True, num_sample=-1
        )
        assert result1 is not None
        assert "bbox" in result1

        # Test with zero num_sample - same behavior
        result2 = geoextent.from_file(
            "tests/testdata/csv/cities_NL_TIME.csv", bbox=True, tbox=True, num_sample=0
        )
        assert result2 is not None
        assert "bbox" in result2

    def test_from_file_csv_with_very_large_num_sample(self):
        """Test from_file with CSV and very large num_sample"""
        # Test with num_sample larger than file content - works fine
        result = geoextent.from_file(
            "tests/testdata/csv/cities_NL_TIME.csv",
            bbox=True,
            tbox=True,
            num_sample=999999,
        )
        assert result is not None
        assert "bbox" in result


class TestSpecificFileFormats:
    """Test parameter combinations with specific file formats"""

    def test_geojson_all_parameter_combinations(self):
        """Test all parameter combinations with GeoJSON files"""
        file_path = "tests/testdata/geojson/muenster_ring_zeit.geojson"

        # bbox=True, tbox=True
        result1 = geoextent.from_file(file_path, bbox=True, tbox=True)
        assert "bbox" in result1

        # bbox=True, tbox=False
        result2 = geoextent.from_file(file_path, bbox=True, tbox=False)
        assert "bbox" in result2
        assert "tbox" not in result2

        # bbox=False, tbox=True
        result3 = geoextent.from_file(file_path, bbox=False, tbox=True)
        assert "bbox" not in result3

    def test_csv_all_parameter_combinations(self):
        """Test all parameter combinations with CSV files"""
        file_path = "tests/testdata/csv/cities_NL_TIME.csv"

        # Test with different num_sample values
        for num_sample in [None, 5, 10, 50]:
            result = geoextent.from_file(
                file_path, bbox=True, tbox=True, num_sample=num_sample
            )
            assert "bbox" in result

    def test_kml_all_parameter_combinations(self):
        """Test all parameter combinations with KML files"""
        file_path = "tests/testdata/kml/aasee.kml"

        # bbox=True, tbox=True
        result1 = geoextent.from_file(file_path, bbox=True, tbox=True)
        assert "bbox" in result1

        # bbox=True, tbox=False
        result2 = geoextent.from_file(file_path, bbox=True, tbox=False)
        assert "bbox" in result2
        assert "tbox" not in result2

    def test_geotiff_all_parameter_combinations(self):
        """Test all parameter combinations with GeoTIFF files"""
        file_path = "tests/testdata/tif/wf_100m_klas.tif"

        # bbox=True, tbox=True
        result1 = geoextent.from_file(file_path, bbox=True, tbox=True)
        assert "bbox" in result1

        # bbox=True, tbox=False
        result2 = geoextent.from_file(file_path, bbox=True, tbox=False)
        assert "bbox" in result2
        assert "tbox" not in result2


class TestLegacyMode:
    """Test legacy coordinate order mode (lon, lat) vs default native EPSG:4326 (lat, lon)"""

    def test_from_file_legacy_mode(self):
        """Test that legacy=True returns coordinates in traditional GIS order (lon, lat)"""
        file_path = "tests/testdata/geojson/muenster_ring_zeit.geojson"

        # Default (native EPSG:4326): bbox = [minlat, minlon, maxlat, maxlon]
        result_native = geoextent.from_file(file_path, bbox=True, tbox=False)
        # Legacy: bbox = [minlon, minlat, maxlon, maxlat]
        result_legacy = geoextent.from_file(
            file_path, bbox=True, tbox=False, legacy=True
        )

        assert result_native is not None
        assert result_legacy is not None
        assert "bbox" in result_native
        assert "bbox" in result_legacy

        native_bbox = result_native["bbox"]
        legacy_bbox = result_legacy["bbox"]

        # Native [minlat, minlon, maxlat, maxlon] vs legacy [minlon, minlat, maxlon, maxlat]
        # So native[0] (minlat) == legacy[1] (minlat)
        assert abs(native_bbox[0] - legacy_bbox[1]) < tolerance
        assert abs(native_bbox[1] - legacy_bbox[0]) < tolerance
        assert abs(native_bbox[2] - legacy_bbox[3]) < tolerance
        assert abs(native_bbox[3] - legacy_bbox[2]) < tolerance

    def test_from_directory_legacy_mode(self):
        """Test that legacy=True works with from_directory"""
        dir_path = "tests/testdata/geojson"

        result_native = geoextent.from_directory(dir_path, bbox=True, tbox=False)
        result_legacy = geoextent.from_directory(
            dir_path, bbox=True, tbox=False, legacy=True
        )

        assert result_native is not None
        assert result_legacy is not None
        assert "bbox" in result_native
        assert "bbox" in result_legacy

        native_bbox = result_native["bbox"]
        legacy_bbox = result_legacy["bbox"]

        # Verify coordinate swap relationship
        assert abs(native_bbox[0] - legacy_bbox[1]) < tolerance
        assert abs(native_bbox[1] - legacy_bbox[0]) < tolerance
        assert abs(native_bbox[2] - legacy_bbox[3]) < tolerance
        assert abs(native_bbox[3] - legacy_bbox[2]) < tolerance

    def test_from_file_legacy_false_is_default(self):
        """Test that legacy=False gives the same result as omitting the parameter"""
        file_path = "tests/testdata/geojson/muenster_ring_zeit.geojson"

        result_default = geoextent.from_file(file_path, bbox=True, tbox=False)
        result_explicit = geoextent.from_file(
            file_path, bbox=True, tbox=False, legacy=False
        )

        assert result_default["bbox"] == result_explicit["bbox"]

    def test_legacy_mode_with_details(self):
        """Test that legacy mode also swaps coordinates in details"""
        dir_path = "tests/testdata/geojson"

        result_native = geoextent.from_directory(
            dir_path, bbox=True, tbox=False, details=True
        )
        result_legacy = geoextent.from_directory(
            dir_path, bbox=True, tbox=False, details=True, legacy=True
        )

        assert "details" in result_native
        assert "details" in result_legacy

        # Check that details entries also have swapped coordinates
        for filename in result_native["details"]:
            if filename in result_legacy["details"]:
                native_detail = result_native["details"][filename]
                legacy_detail = result_legacy["details"][filename]
                if (
                    isinstance(native_detail, dict)
                    and "bbox" in native_detail
                    and native_detail["bbox"] is not None
                    and isinstance(legacy_detail, dict)
                    and "bbox" in legacy_detail
                    and legacy_detail["bbox"] is not None
                ):
                    nb = native_detail["bbox"]
                    lb = legacy_detail["bbox"]
                    if isinstance(nb, list) and len(nb) == 4:
                        assert abs(nb[0] - lb[1]) < tolerance
                        assert abs(nb[1] - lb[0]) < tolerance
