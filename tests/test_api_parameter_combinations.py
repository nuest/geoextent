import pytest
import geoextent.lib.extent as geoextent
import tempfile
import os
from help_functions_test import tolerance


class TestParameterCombinations:
    """Test various parameter combinations for geoextent functions"""

    def test_fromFile_both_bbox_and_tbox_enabled(self):
        """Test fromFile with both bbox and tbox enabled"""
        result = geoextent.fromFile(
            "tests/testdata/geojson/muenster_ring_zeit.geojson", bbox=True, tbox=True
        )
        assert result is not None
        assert "bbox" in result
        assert "crs" in result
        # Note: This file may not have temporal data, which is fine

    def test_fromFile_both_disabled_should_fail(self):
        """Test fromFile with both bbox and tbox disabled should raise exception"""
        with pytest.raises(Exception, match="No extraction options enabled"):
            geoextent.fromFile(
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
                bbox=False,
                tbox=False,
            )

    def test_fromFile_only_bbox_enabled(self):
        """Test fromFile with only bbox enabled"""
        result = geoextent.fromFile(
            "tests/testdata/geojson/muenster_ring_zeit.geojson", bbox=True, tbox=False
        )
        assert result is not None
        assert "bbox" in result
        assert "crs" in result
        assert "tbox" not in result

    def test_fromFile_only_tbox_enabled(self):
        """Test fromFile with only tbox enabled"""
        # Use a GeoJSON file with temporal data
        result = geoextent.fromFile(
            "tests/testdata/geojson/muenster_ring_zeit.geojson", bbox=False, tbox=True
        )
        assert result is not None
        # tbox might or might not be present depending on temporal data in the file
        assert "bbox" not in result
        assert "crs" not in result

    def test_fromFile_csv_with_num_sample_parameter(self):
        """Test fromFile with CSV file and num_sample parameter"""
        # Test with different num_sample values using an existing CSV file
        csv_file = "tests/testdata/csv/cities_NL_TIME.csv"
        result1 = geoextent.fromFile(csv_file, bbox=True, tbox=True, num_sample=5)
        result2 = geoextent.fromFile(csv_file, bbox=True, tbox=True, num_sample=10)
        result3 = geoextent.fromFile(csv_file, bbox=True, tbox=True, num_sample=100)

        # All should succeed (num_sample affects internal processing but not final result significantly)
        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        # bbox might be present depending on CSV content
        if "bbox" in result1:
            assert "bbox" in result2
            assert "bbox" in result3

    def test_fromFile_num_sample_ignored_for_non_csv(self):
        """Test that num_sample parameter is ignored for non-CSV files"""
        # Should work without error but num_sample should be ignored
        result = geoextent.fromFile(
            "tests/testdata/geojson/muenster_ring_zeit.geojson",
            bbox=True,
            tbox=True,
            num_sample=10,
        )
        assert result is not None
        assert "bbox" in result

    def test_fromDirectory_both_bbox_and_tbox_enabled(self):
        """Test fromDirectory with both bbox and tbox enabled"""
        result = geoextent.fromDirectory("tests/testdata/geojson", bbox=True, tbox=True)
        assert "bbox" in result
        assert "format" in result

    def test_fromDirectory_with_details_enabled(self):
        """Test fromDirectory with details parameter"""
        result = geoextent.fromDirectory(
            "tests/testdata/geojson", bbox=True, tbox=True, details=True
        )
        assert "details" in result
        assert isinstance(result["details"], dict)

    def test_fromDirectory_with_details_disabled(self):
        """Test fromDirectory with details disabled (default)"""
        result = geoextent.fromDirectory(
            "tests/testdata/geojson", bbox=True, tbox=True, details=False
        )
        assert "details" not in result

    def test_fromDirectory_both_disabled_should_fail(self):
        """Test fromDirectory with both bbox and tbox disabled should raise exception"""
        with pytest.raises(Exception, match="No extraction options enabled"):
            geoextent.fromDirectory("tests/testdata/geojson", bbox=False, tbox=False)

    def test_fromDirectory_only_bbox_enabled(self):
        """Test fromDirectory with only bbox enabled"""
        result = geoextent.fromDirectory(
            "tests/testdata/geojson", bbox=True, tbox=False
        )
        assert "bbox" in result
        assert "tbox" not in result

    def test_fromDirectory_only_tbox_enabled(self):
        """Test fromDirectory with only tbox enabled"""
        result = geoextent.fromDirectory("tests/testdata/csv", bbox=False, tbox=True)
        assert "tbox" in result
        assert "bbox" not in result

    def test_fromDirectory_with_timeout_parameter(self):
        """Test fromDirectory with timeout parameter"""
        # Use a reasonable timeout that shouldn't be reached
        result = geoextent.fromDirectory(
            "tests/testdata/geojson", bbox=True, tbox=True, timeout=30
        )
        assert "bbox" in result
        # timeout field should not be present if timeout wasn't reached
        assert "timeout" not in result

    def test_fromDirectory_with_very_short_timeout(self):
        """Test fromDirectory with very short timeout"""
        # Use a very short timeout that might be reached
        result = geoextent.fromDirectory(
            "tests/testdata", bbox=True, tbox=True, timeout=0.001
        )
        # Should either complete normally or include timeout field
        assert "format" in result
        # If timeout was reached, it should be indicated
        if "timeout" in result:
            assert result["timeout"] == 0.001

    def test_fromFile_default_parameters(self):
        """Test fromFile with default parameters (bbox=True, tbox=True)"""
        result = geoextent.fromFile("tests/testdata/geojson/muenster_ring_zeit.geojson")
        # Default behavior should extract bbox
        assert "bbox" in result
        assert "crs" in result

    def test_fromDirectory_default_parameters(self):
        """Test fromDirectory with default parameters (bbox=False, tbox=False)"""
        # Default parameters should fail because both are False by default
        with pytest.raises(Exception, match="No extraction options enabled"):
            geoextent.fromDirectory("tests/testdata/geojson")


class TestEdgeCasesAndErrors:
    """Test edge cases and error conditions"""

    def test_fromFile_nonexistent_file(self):
        """Test fromFile with nonexistent file returns None"""
        result = geoextent.fromFile("tests/testdata/nonexistent.file", bbox=True)
        assert result is None

    def test_fromFile_directory_instead_of_file(self):
        """Test fromFile with directory path instead of file"""
        result = geoextent.fromFile("tests/testdata", bbox=True)
        assert result is None

    def test_fromDirectory_nonexistent_directory(self):
        """Test fromDirectory with nonexistent directory"""
        with pytest.raises(Exception):
            geoextent.fromDirectory("tests/nonexistent_directory", bbox=True)

    def test_fromDirectory_file_instead_of_directory(self):
        """Test fromDirectory with file path instead of directory raises error"""
        with pytest.raises((NotADirectoryError, FileNotFoundError)):
            geoextent.fromDirectory(
                "tests/testdata/geojson/muenster_ring_zeit.geojson", bbox=True
            )

    def test_fromFile_empty_file_path(self):
        """Test fromFile with empty file path returns None"""
        result = geoextent.fromFile("", bbox=True)
        assert result is None

    def test_fromDirectory_empty_directory_path(self):
        """Test fromDirectory with empty directory path"""
        with pytest.raises(Exception):
            geoextent.fromDirectory("", bbox=True)

    def test_fromFile_unsupported_file_format(self):
        """Test fromFile with unsupported file format"""
        # Create a temporary file with unsupported extension
        with tempfile.NamedTemporaryFile(
            suffix=".unsupported", delete=False
        ) as tmp_file:
            tmp_file.write(b"some content")
            tmp_file_path = tmp_file.name

        try:
            result = geoextent.fromFile(tmp_file_path, bbox=True)
            # The CSV handler may pick up arbitrary files but won't extract a bbox
            if result is not None:
                assert "bbox" not in result or result.get("bbox") is None
        finally:
            os.unlink(tmp_file_path)

    def test_fromDirectory_empty_directory(self):
        """Test fromDirectory with empty directory"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = geoextent.fromDirectory(tmp_dir, bbox=True)
            # Should handle empty directory gracefully
            assert "format" in result
            assert result["format"] == "folder"

    def test_fromFile_csv_with_invalid_num_sample(self):
        """Test fromFile with CSV and invalid num_sample values"""
        # Test with negative num_sample - still extracts bbox, just skips tbox sampling
        result1 = geoextent.fromFile(
            "tests/testdata/csv/cities_NL_TIME.csv", bbox=True, tbox=True, num_sample=-1
        )
        assert result1 is not None
        assert "bbox" in result1

        # Test with zero num_sample - same behavior
        result2 = geoextent.fromFile(
            "tests/testdata/csv/cities_NL_TIME.csv", bbox=True, tbox=True, num_sample=0
        )
        assert result2 is not None
        assert "bbox" in result2

    def test_fromFile_csv_with_very_large_num_sample(self):
        """Test fromFile with CSV and very large num_sample"""
        # Test with num_sample larger than file content - works fine
        result = geoextent.fromFile(
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
        result1 = geoextent.fromFile(file_path, bbox=True, tbox=True)
        assert "bbox" in result1

        # bbox=True, tbox=False
        result2 = geoextent.fromFile(file_path, bbox=True, tbox=False)
        assert "bbox" in result2
        assert "tbox" not in result2

        # bbox=False, tbox=True
        result3 = geoextent.fromFile(file_path, bbox=False, tbox=True)
        assert "bbox" not in result3

    def test_csv_all_parameter_combinations(self):
        """Test all parameter combinations with CSV files"""
        file_path = "tests/testdata/csv/cities_NL_TIME.csv"

        # Test with different num_sample values
        for num_sample in [None, 5, 10, 50]:
            result = geoextent.fromFile(
                file_path, bbox=True, tbox=True, num_sample=num_sample
            )
            assert "bbox" in result

    def test_kml_all_parameter_combinations(self):
        """Test all parameter combinations with KML files"""
        file_path = "tests/testdata/kml/aasee.kml"

        # bbox=True, tbox=True
        result1 = geoextent.fromFile(file_path, bbox=True, tbox=True)
        assert "bbox" in result1

        # bbox=True, tbox=False
        result2 = geoextent.fromFile(file_path, bbox=True, tbox=False)
        assert "bbox" in result2
        assert "tbox" not in result2

    def test_geotiff_all_parameter_combinations(self):
        """Test all parameter combinations with GeoTIFF files"""
        file_path = "tests/testdata/tif/wf_100m_klas.tif"

        # bbox=True, tbox=True
        result1 = geoextent.fromFile(file_path, bbox=True, tbox=True)
        assert "bbox" in result1

        # bbox=True, tbox=False
        result2 = geoextent.fromFile(file_path, bbox=True, tbox=False)
        assert "bbox" in result2
        assert "tbox" not in result2


class TestLegacyMode:
    """Test legacy coordinate order mode (lon, lat) vs default native EPSG:4326 (lat, lon)"""

    def test_fromFile_legacy_mode(self):
        """Test that legacy=True returns coordinates in traditional GIS order (lon, lat)"""
        file_path = "tests/testdata/geojson/muenster_ring_zeit.geojson"

        # Default (native EPSG:4326): bbox = [minlat, minlon, maxlat, maxlon]
        result_native = geoextent.fromFile(file_path, bbox=True, tbox=False)
        # Legacy: bbox = [minlon, minlat, maxlon, maxlat]
        result_legacy = geoextent.fromFile(
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

    def test_fromDirectory_legacy_mode(self):
        """Test that legacy=True works with fromDirectory"""
        dir_path = "tests/testdata/geojson"

        result_native = geoextent.fromDirectory(dir_path, bbox=True, tbox=False)
        result_legacy = geoextent.fromDirectory(
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

    def test_fromFile_legacy_false_is_default(self):
        """Test that legacy=False gives the same result as omitting the parameter"""
        file_path = "tests/testdata/geojson/muenster_ring_zeit.geojson"

        result_default = geoextent.fromFile(file_path, bbox=True, tbox=False)
        result_explicit = geoextent.fromFile(
            file_path, bbox=True, tbox=False, legacy=False
        )

        assert result_default["bbox"] == result_explicit["bbox"]

    def test_legacy_mode_with_details(self):
        """Test that legacy mode also swaps coordinates in details"""
        dir_path = "tests/testdata/geojson"

        result_native = geoextent.fromDirectory(
            dir_path, bbox=True, tbox=False, details=True
        )
        result_legacy = geoextent.fromDirectory(
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
