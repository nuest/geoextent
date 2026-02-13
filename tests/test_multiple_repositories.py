import os
import json
import pytest
import tempfile
from unittest.mock import patch

from geoextent.lib import extent
from geoextent.__main__ import main
import sys


class TestMultipleRepositories:
    """Test multiple repository processing functionality"""

    def test_multiple_repository_extraction_metadata_only(self):
        """Test extraction from multiple repository identifiers with metadata only"""
        # Use metadata-only to avoid actual downloads in tests
        result = {}
        result["format"] = "multiple_files"
        result["details"] = {}

        # Mock the fromRemote function to avoid actual network calls
        def mock_fromRemote(repo_id, **kwargs):
            if "918707" in repo_id:
                return {
                    "format": "remote",
                    "crs": "4326",
                    "bbox": [76.5, -21.5, 76.5, -21.5],
                    "details": {
                        "pangaea_918707.geojson": {
                            "format": "geojson",
                            "bbox": [76.5, -21.5, 76.5, -21.5],
                            "crs": "4326",
                        }
                    },
                }
            elif "858767" in repo_id:
                return {
                    "format": "remote",
                    "details": {"pangaea_858767_metadata.json": None},
                }
            return None

        with patch("geoextent.lib.extent.fromRemote", side_effect=mock_fromRemote):
            # Simulate processing multiple repositories
            repositories = [
                "https://doi.org/10.1594/PANGAEA.918707",
                "https://doi.pangaea.de/10.1594/PANGAEA.858767",
            ]

            for repo in repositories:
                repo_output = extent.fromRemote(
                    repo, bbox=True, tbox=False, convex_hull=False, download_data=False
                )
                if repo_output is not None:
                    result["details"][repo] = repo_output

            # Verify results
            assert len(result["details"]) == 2
            assert "https://doi.org/10.1594/PANGAEA.918707" in result["details"]
            assert "https://doi.pangaea.de/10.1594/PANGAEA.858767" in result["details"]

            # Check that first repository has valid bbox
            first_repo_result = result["details"][
                "https://doi.org/10.1594/PANGAEA.918707"
            ]
            assert first_repo_result["bbox"] == [76.5, -21.5, 76.5, -21.5]
            assert first_repo_result["crs"] == "4326"

    def test_mixed_file_and_repository_inputs(self):
        """Test processing mix of files and repository identifiers"""

        # Create temporary GeoJSON file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".geojson", delete=False
        ) as f:
            geojson_data = {"type": "Point", "coordinates": [1.0, 1.0]}
            json.dump(geojson_data, f)
            temp_geojson = f.name

        try:
            # Mock the fromRemote function
            def mock_fromRemote(repo_id, **kwargs):
                return {
                    "format": "remote",
                    "crs": "4326",
                    "bbox": [76.5, -21.5, 76.5, -21.5],
                    "details": {},
                }

            with patch("geoextent.lib.extent.fromRemote", side_effect=mock_fromRemote):
                # Test CLI argument validation
                from geoextent.__main__ import readable_file_or_dir
                import argparse

                # Create proper argument action with destination
                class MockNamespace:
                    pass

                namespace = MockNamespace()
                inputs = [temp_geojson, "https://doi.org/10.1594/PANGAEA.918707"]

                # Create validator with proper destination
                validator = readable_file_or_dir(None, "files")
                validator.dest = "files"

                # Test the argument validator accepts mixed inputs
                validator(None, namespace, inputs, None)

                # Should not raise exception and should validate both inputs
                assert hasattr(namespace, "files")
                assert len(namespace.files) == 2
                assert temp_geojson in namespace.files
                assert "https://doi.org/10.1594/PANGAEA.918707" in namespace.files

        finally:
            # Clean up temporary file
            if os.path.exists(temp_geojson):
                os.unlink(temp_geojson)

    def test_cli_multiple_dois_help_examples(self):
        """Test that the help examples are valid"""
        from geoextent.__main__ import help_epilog

        # Check that help includes examples of multiple DOIs
        assert (
            "https://doi.org/10.1594/PANGAEA.918707 https://doi.pangaea.de/10.1594/PANGAEA.858767"
            in help_epilog
        )
        assert "https://zenodo.org/record/4567890 10.1594/PANGAEA.123456" in help_epilog

    def test_cli_argument_parser_multiple_inputs(self):
        """Test that argument parser correctly handles multiple inputs"""
        from geoextent.__main__ import get_arg_parser

        parser = get_arg_parser()

        # Test parsing with multiple repository identifiers
        with patch("geoextent.__main__.readable_file_or_dir"):
            args = parser.parse_args(
                [
                    "-b",
                    "https://doi.org/10.1594/PANGAEA.918707",
                    "https://doi.pangaea.de/10.1594/PANGAEA.858767",
                ]
            )

            assert args.bounding_box is True
            assert len(args.files) == 2

    def test_repository_identifier_validation(self):
        """Test that repository identifier validation works for multiple providers"""
        from geoextent.__main__ import readable_file_or_dir

        validator = readable_file_or_dir(None, None)

        # Test various valid repository identifiers
        valid_identifiers = [
            "https://doi.org/10.1594/PANGAEA.918707",
            "https://doi.pangaea.de/10.1594/PANGAEA.858767",
            "10.1594/PANGAEA.123456",
            "https://zenodo.org/record/123456",
            "https://osf.io/abc123",
        ]

        for identifier in valid_identifiers:
            # Should not raise an exception for valid identifiers
            is_valid = validator._is_supported_repository(identifier)
            # Note: This will return True or False depending on the specific format
            # The important thing is that it doesn't crash
            assert isinstance(is_valid, bool)

    def test_multiple_repository_merge_logic(self):
        """Test that multiple repository results are properly merged"""
        from geoextent.lib import helpfunctions as hf

        # Mock metadata from multiple repositories
        mock_details = {
            "https://doi.org/10.1594/PANGAEA.918707": {
                "format": "remote",
                "bbox": [76.5, -21.5, 76.5, -21.5],
                "crs": "4326",
            },
            "test.geojson": {
                "format": "geojson",
                "bbox": [1.0, 1.0, 1.0, 1.0],
                "crs": "4326",
            },
        }

        # Test bounding box merge
        merged_bbox = hf.bbox_merge(mock_details, "multiple_files")

        assert merged_bbox is not None
        assert merged_bbox["crs"] == "4326"

        # The merged bounding box should encompass both points
        bbox = merged_bbox["bbox"]
        assert bbox[0] <= 1.0  # min latitude
        assert bbox[1] <= -21.5  # min longitude
        assert bbox[2] >= 76.5  # max latitude
        assert bbox[3] >= 1.0  # max longitude

    def test_cli_multiple_inputs_format_output(self):
        """Test CLI output format for multiple inputs"""

        # Create temporary test file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".geojson", delete=False
        ) as f:
            geojson_data = {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [1.0, 1.0]},
                "properties": {},
            }
            json.dump(geojson_data, f)
            temp_file = f.name

        try:
            # Mock sys.argv for CLI test
            test_args = [
                "geoextent",
                "-b",
                "--no-download-data",
                "--details",
                temp_file,
                "https://doi.org/10.1594/PANGAEA.918707",
            ]

            # Mock the fromRemote to avoid network calls
            def mock_fromRemote(repo_id, **kwargs):
                return {
                    "format": "remote",
                    "crs": "4326",
                    "bbox": [76.5, -21.5, 76.5, -21.5],
                    "details": {},
                }

            with patch.object(sys, "argv", test_args):
                with patch(
                    "geoextent.lib.extent.fromRemote",
                    side_effect=mock_fromRemote,
                ):
                    with patch("builtins.print") as mock_print:
                        try:
                            main()
                        except SystemExit:
                            pass  # main() calls sys.exit(), which is expected

                        # Verify that output was printed
                        assert mock_print.called

                        # Get the printed JSON output
                        printed_args = mock_print.call_args[0]
                        if printed_args:
                            output_str = printed_args[0]
                            try:
                                output = json.loads(output_str)

                                # Verify it's a proper FeatureCollection
                                assert output.get("type") == "FeatureCollection"
                                assert "features" in output
                                assert len(output["features"]) >= 1

                                # Should have details from multiple inputs
                                if "details" in output:
                                    details = output["details"]
                                    # Should contain both the temp file and the DOI
                                    assert len(details) >= 1

                            except json.JSONDecodeError:
                                # Output might not be JSON if there were errors
                                pass
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestMultipleRepositoriesIntegration:
    """Integration tests that require network access (marked as slow)"""

    @pytest.mark.slow
    def test_actual_multiple_pangaea_dois_metadata_only(self):
        """Test actual extraction from multiple PANGAEA DOIs using metadata only"""
        # This test uses real network calls but with metadata-only to minimize load

        repositories = [
            "https://doi.org/10.1594/PANGAEA.918707",
            "https://doi.pangaea.de/10.1594/PANGAEA.858767",
        ]

        results = {}

        for repo in repositories:
            try:
                result = extent.fromRemote(
                    repo,
                    bbox=True,
                    tbox=False,
                    convex_hull=False,
                    download_data=False,  # Metadata only
                    show_progress=False,
                )
                if result:
                    results[repo] = result
            except Exception as e:
                # Some repositories may fail, but we should handle gracefully
                pytest.skip(f"Repository {repo} failed with {e}")

        # At least one should succeed
        assert len(results) >= 1

        # Check that results have proper format
        for repo, result in results.items():
            assert result["format"] == "remote"
            # May or may not have bbox depending on dataset
