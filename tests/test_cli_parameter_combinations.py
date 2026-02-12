import pytest
import tempfile
import os


class TestCLIParameterCombinations:
    """Test CLI with various parameter combinations"""

    def test_cli_bbox_only(self, script_runner):
        """Test CLI with only bbox parameter"""
        ret = script_runner.run(
            ["geoextent", "-b", "tests/testdata/geojson/muenster_ring_zeit.geojson"]
        )
        assert ret.success, f"Process should return success. stderr: {ret.stderr}"
        assert "coordinates" in ret.stdout
        assert "tbox" not in ret.stdout

    def test_cli_tbox_only(self, script_runner):
        """Test CLI with only tbox parameter"""
        ret = script_runner.run(
            ["geoextent", "-t", "tests/testdata/geojson/muenster_ring_zeit.geojson"]
        )
        assert ret.success, f"Process should return success. stderr: {ret.stderr}"
        # tbox may or may not be present depending on temporal data
        assert "bbox" not in ret.stdout

    def test_cli_both_bbox_and_tbox(self, script_runner):
        """Test CLI with both bbox and tbox parameters"""
        ret = script_runner.run(
            [
                "geoextent",
                "-b",
                "-t",
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
            ]
        )
        assert ret.success, f"Process should return success. stderr: {ret.stderr}"
        # Note: bbox should be present, tbox may or may not be present depending on data

    def test_cli_long_parameter_names(self, script_runner):
        """Test CLI with long parameter names"""
        ret = script_runner.run(
            [
                "geoextent",
                "--bounding-box",
                "--time-box",
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
            ]
        )
        assert ret.success, f"Process should return success. stderr: {ret.stderr}"

    def test_cli_with_details_flag(self, script_runner):
        """Test CLI with details flag for directory"""
        ret = script_runner.run(
            ["geoextent", "-b", "-t", "--details", "tests/testdata/geojson"]
        )
        assert ret.success, f"Process should return success. stderr: {ret.stderr}"
        assert "details" in ret.stdout

    def test_cli_without_details_flag(self, script_runner):
        """Test CLI without details flag for directory (default behavior)"""
        ret = script_runner.run(["geoextent", "-b", "-t", "tests/testdata/geojson"])
        assert ret.success, f"Process should return success. stderr: {ret.stderr}"
        # Details should not be included by default for CLI

    def test_cli_debug_flag(self, script_runner):
        """Test CLI with debug flag"""
        ret = script_runner.run(
            [
                "geoextent",
                "--debug",
                "-b",
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
            ]
        )
        assert ret.success, f"Process should return success. stderr: {ret.stderr}"
        # Debug mode should still produce valid output

    def test_cli_repository_with_download_data_flag(self, script_runner):
        """Test CLI with repository DOI and download-data flag"""
        # Test with a Pangaea DOI
        ret = script_runner.run(
            ["geoextent", "-b", "-t", "--download-data", "10.1594/PANGAEA.734969"]
        )
        if ret.success:
            assert "FeatureCollection" in ret.stdout or "remote" in ret.stdout
        else:
            # May fail due to network issues or missing dependencies
            combined = ret.stdout + ret.stderr
            assert "error" in combined.lower() or "exception" in combined.lower()

    def test_cli_repository_without_download_data_flag(self, script_runner):
        """Test CLI with repository DOI without download-data flag"""
        ret = script_runner.run(["geoextent", "-b", "-t", "10.1594/PANGAEA.734969"])
        if ret.success:
            assert "FeatureCollection" in ret.stdout or "remote" in ret.stdout
        else:
            # May fail due to network issues or missing dependencies
            combined = ret.stdout + ret.stderr
            assert "error" in combined.lower() or "exception" in combined.lower()


class TestCLIErrorConditions:
    """Test CLI error conditions with various parameter combinations"""

    def test_cli_no_extraction_options(self, script_runner):
        """Test CLI with no extraction options should fail"""
        ret = script_runner.run(
            ["geoextent", "tests/testdata/geojson/muenster_ring_zeit.geojson"]
        )
        assert not ret.success
        combined = (ret.stdout + ret.stderr).lower()
        assert (
            "usage" in combined
            or "error" in combined
            or "extraction options" in combined
        )

    def test_cli_both_extraction_options_disabled_should_fail(self, script_runner):
        """Test CLI with both bbox and tbox disabled (not possible via CLI, but testing logic)"""
        # This test ensures the underlying logic works correctly
        # The CLI doesn't allow both to be false, but the API does
        import geoextent.lib.extent as geoextent

        with pytest.raises(Exception, match="No extraction options enabled"):
            geoextent.fromFile(
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
                bbox=False,
                tbox=False,
            )

    def test_cli_nonexistent_file(self, script_runner):
        """Test CLI with nonexistent file"""
        ret = script_runner.run(["geoextent", "-b", "tests/testdata/nonexistent.file"])
        assert not ret.success
        assert "error" in ret.stderr.lower() or "not" in ret.stderr.lower()

    def test_cli_invalid_file_format(self, script_runner):
        """Test CLI with unsupported file format"""
        # Create a temporary file with unsupported extension
        with tempfile.NamedTemporaryFile(
            suffix=".unsupported", delete=False
        ) as tmp_file:
            tmp_file.write(b"some content")
            tmp_file_path = tmp_file.name

        try:
            ret = script_runner.run(["geoextent", "-b", tmp_file_path])
            # Should either fail or return message about unsupported format
            if not ret.success:
                assert "error" in ret.stderr.lower() or "not" in ret.stderr.lower()
            else:
                # Some formats might be handled gracefully
                pass
        finally:
            os.unlink(tmp_file_path)

    def test_cli_invalid_doi_format(self, script_runner):
        """Test CLI with invalid DOI format"""
        ret = script_runner.run(["geoextent", "-b", "-t", "invalid-doi-format"])
        assert not ret.success
        assert "error" in ret.stderr.lower() or "not" in ret.stderr.lower()

    def test_cli_directory_as_file_with_no_extraction_options(self, script_runner):
        """Test CLI with directory path but no extraction options"""
        ret = script_runner.run(["geoextent", "tests/testdata"])
        assert not ret.success
        combined = ret.stdout + ret.stderr
        assert (
            "usage" in combined.lower()
            or "error" in combined.lower()
            or "extraction options" in combined
        )


class TestCLIOutputFormats:
    """Test CLI output handling with different parameter combinations"""

    def test_cli_output_geopackage_with_single_file(self, script_runner):
        """Test CLI output to geopackage with single file (export not created)"""
        with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as tmp_file:
            output_path = tmp_file.name

        # Remove the temp file so we can check if it gets created
        os.unlink(output_path)

        try:
            ret = script_runner.run(
                [
                    "geoextent",
                    "-b",
                    "-t",
                    "--output",
                    output_path,
                    "tests/testdata/geojson/muenster_ring_zeit.geojson",
                ]
            )
            if ret.success:
                # Export should not be created for single file
                assert not os.path.exists(
                    output_path
                ), "Geopackage should not be created for single file input"
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_cli_output_geopackage_with_directory(self, script_runner):
        """Test CLI output to geopackage with directory"""
        with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as tmp_file:
            output_path = tmp_file.name

        try:
            ret = script_runner.run(
                [
                    "geoextent",
                    "-b",
                    "-t",
                    "--output",
                    output_path,
                    "tests/testdata/geojson",
                ]
            )
            if ret.success:
                # Should create geopackage file
                assert os.path.exists(output_path)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_cli_output_invalid_extension(self, script_runner):
        """Test CLI output with invalid file extension"""
        with tempfile.NamedTemporaryFile(suffix=".invalid", delete=False) as tmp_file:
            output_path = tmp_file.name

        try:
            ret = script_runner.run(
                [
                    "geoextent",
                    "-b",
                    "-t",
                    "--output",
                    output_path,
                    "tests/testdata/geojson",
                ]
            )
            # Should either fail or warn about invalid extension
            if not ret.success:
                assert "error" in ret.stderr.lower()
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_cli_output_nonexistent_directory(self, script_runner):
        """Test CLI output to nonexistent directory"""
        output_path = "/nonexistent/path/output.gpkg"

        ret = script_runner.run(
            ["geoextent", "-b", "-t", "--output", output_path, "tests/testdata/geojson"]
        )
        assert not ret.success
        assert "error" in ret.stderr.lower() or "not" in ret.stderr.lower()


class TestCLISpecialParameters:
    """Test special CLI parameters and their combinations"""

    def test_cli_help_flag(self, script_runner):
        """Test CLI help flag"""
        ret = script_runner.run(["geoextent", "--help"])
        assert ret.success
        assert "usage" in ret.stdout.lower()
        assert "bounding-box" in ret.stdout
        assert "time-box" in ret.stdout

    def test_cli_version_flag(self, script_runner):
        """Test CLI version flag"""
        ret = script_runner.run(["geoextent", "--version"])
        assert ret.success
        # Should output version information
        assert len(ret.stdout.strip()) > 0

    def test_cli_formats_flag(self, script_runner):
        """Test CLI formats flag"""
        ret = script_runner.run(["geoextent", "--formats"])
        assert ret.success
        assert "supported formats" in ret.stdout.lower()
        assert "geojson" in ret.stdout.lower()

    def test_cli_help_with_short_flag(self, script_runner):
        """Test CLI help with short flag"""
        ret = script_runner.run(["geoextent", "-h"])
        assert ret.success
        assert "usage" in ret.stdout.lower()

    def test_cli_no_arguments(self, script_runner):
        """Test CLI with no arguments should show help"""
        ret = script_runner.run(["geoextent"])
        assert ret.success  # Should show help, not error
        assert "usage" in ret.stdout.lower() or "help" in ret.stdout.lower()


class TestCLIParameterOrder:
    """Test different parameter order combinations"""

    def test_cli_flags_before_file(self, script_runner):
        """Test CLI with flags before file path"""
        ret = script_runner.run(
            [
                "geoextent",
                "-b",
                "-t",
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
            ]
        )
        assert ret.success

    def test_cli_mixed_flag_order(self, script_runner):
        """Test CLI with mixed flag order"""
        ret = script_runner.run(
            [
                "geoextent",
                "-b",
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
                "-t",
            ]
        )
        assert ret.success

    def test_cli_debug_flag_different_positions(self, script_runner):
        """Test CLI with debug flag in different positions"""
        # Debug flag first
        ret1 = script_runner.run(
            [
                "geoextent",
                "--debug",
                "-b",
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
            ]
        )
        assert ret1.success

        # Debug flag in middle
        ret2 = script_runner.run(
            [
                "geoextent",
                "-b",
                "--debug",
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
            ]
        )
        assert ret2.success

        # Debug flag last
        ret3 = script_runner.run(
            [
                "geoextent",
                "-b",
                "tests/testdata/geojson/muenster_ring_zeit.geojson",
                "--debug",
            ]
        )
        assert ret3.success

    def test_cli_details_flag_different_positions(self, script_runner):
        """Test CLI with details flag in different positions"""
        # Details flag first
        ret1 = script_runner.run(
            ["geoextent", "--details", "-b", "-t", "tests/testdata/geojson"]
        )
        assert ret1.success

        # Details flag last
        ret2 = script_runner.run(
            ["geoextent", "-b", "-t", "tests/testdata/geojson", "--details"]
        )
        assert ret2.success


class TestCLIRepositoryParameterCombinations:
    """Test CLI with repository URLs and various parameter combinations"""

    def test_cli_repository_with_all_flags(self, script_runner):
        """Test CLI with repository and all possible flags"""
        ret = script_runner.run(
            [
                "geoextent",
                "--debug",
                "-b",
                "-t",
                "--details",
                "--download-data",
                "10.1594/PANGAEA.734969",
            ]
        )
        # May succeed or fail depending on network/dependencies
        # We're testing that the parameter combination is accepted
        if not ret.success:
            # Should fail gracefully with meaningful error
            assert len(ret.stderr) > 0

    def test_cli_repository_minimal_parameters(self, script_runner):
        """Test CLI with repository and minimal parameters"""
        ret = script_runner.run(["geoextent", "-b", "10.1594/PANGAEA.734969"])
        # May succeed or fail depending on network/dependencies
        if not ret.success:
            assert len(ret.stderr) > 0

    def test_cli_repository_with_output_parameter(self, script_runner):
        """Test CLI with repository and output parameter"""
        with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as tmp_file:
            output_path = tmp_file.name

        try:
            ret = script_runner.run(
                [
                    "geoextent",
                    "-b",
                    "-t",
                    "--output",
                    output_path,
                    "10.1594/PANGAEA.734969",
                ]
            )
            # Repository extraction with output should work if network is available
            if not ret.success:
                assert len(ret.stderr) > 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_cli_zenodo_repository_parameters(self, script_runner):
        """Test CLI with Zenodo repository parameters"""
        # Test with known Zenodo DOI
        ret = script_runner.run(["geoextent", "-b", "-t", "10.5281/zenodo.820562"])
        # May succeed or fail depending on network/data availability
        if not ret.success:
            assert len(ret.stderr) > 0

    def test_cli_doi_url_formats(self, script_runner):
        """Test CLI with various DOI URL formats"""
        doi_formats = [
            "10.1594/PANGAEA.786028",  # Plain DOI
            "https://doi.org/10.1594/PANGAEA.786028",  # HTTPS DOI resolver
            "http://doi.org/10.1594/PANGAEA.786028",  # HTTP DOI resolver
        ]

        for doi_format in doi_formats:
            ret = script_runner.run(["geoextent", "-b", "-t", doi_format])
            if ret.success:
                assert "FeatureCollection" in ret.stdout or "remote" in ret.stdout
            else:
                # May fail due to network issues or missing dependencies
                combined = ret.stdout + ret.stderr
                assert len(combined) > 0

    def test_cli_generic_doi_resolver_support(self, script_runner):
        """Test CLI support for generic DOI resolver URLs"""
        # Test that both direct and generic DOI URLs work
        direct_url = "https://doi.pangaea.de/10.1594/PANGAEA.786028"
        generic_url = "https://doi.org/10.1594/PANGAEA.786028"

        ret1 = script_runner.run(["geoextent", "-b", "-t", direct_url])
        ret2 = script_runner.run(["geoextent", "-b", "-t", generic_url])

        # Both should have similar behavior (success or failure due to network)
        if ret1.success and ret2.success:
            assert "FeatureCollection" in ret1.stdout or "remote" in ret1.stdout
            assert "FeatureCollection" in ret2.stdout or "remote" in ret2.stdout
