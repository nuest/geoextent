"""
Tests for bulk remote extraction functionality
"""

import unittest
from unittest.mock import patch, MagicMock
from geoextent.lib import extent


class TestMultiRemoteExtraction(unittest.TestCase):
    """Test cases for fromRemote function"""

    def test_fromRemote_validates_non_empty(self):
        """Test that fromRemote validates list is not empty"""
        with self.assertRaises(ValueError) as context:
            extent.fromRemote([], bbox=True)
        self.assertIn("cannot be empty", str(context.exception))

    def test_fromRemote_accepts_string_or_list(self):
        """Test that fromRemote accepts both string and list inputs"""
        # String input should not raise ValueError
        with patch("geoextent.lib.extent._extract_from_remote") as mock_extract:
            mock_extract.return_value = {"bbox": [1, 2, 3, 4], "crs": "4326"}

            # This should work without raising
            result = extent.fromRemote("10.5281/zenodo.123", bbox=True)
            self.assertIsInstance(result, dict)

            # List input should also work
            result = extent.fromRemote(["10.5281/zenodo.123"], bbox=True)
            self.assertIsInstance(result, dict)

    @patch("geoextent.lib.extent._extract_from_remote")
    def test_fromRemote_processes_multiple_identifiers(self, mock_extract):
        """Test that fromRemote processes multiple remote identifiers"""
        # Mock successful responses
        mock_extract.side_effect = [
            {"bbox": [5.0, 50.0, 6.0, 51.0], "crs": "4326"},
            {"bbox": [7.0, 52.0, 8.0, 53.0], "crs": "4326"},
        ]

        identifiers = ["10.5281/zenodo.123", "10.25532/OPARA-456"]
        result = extent.fromRemote(identifiers, bbox=True)

        # Verify structure
        self.assertEqual(result["format"], "remote_bulk")
        self.assertIn("details", result)
        self.assertIn("extraction_metadata", result)

        # Verify metadata
        self.assertEqual(result["extraction_metadata"]["total_resources"], 2)
        self.assertEqual(result["extraction_metadata"]["successful"], 2)
        self.assertEqual(result["extraction_metadata"]["failed"], 0)

        # Verify each identifier was processed
        self.assertIn(identifiers[0], result["details"])
        self.assertIn(identifiers[1], result["details"])

        # Verify _extract_from_remote was called for each identifier
        self.assertEqual(mock_extract.call_count, 2)

    @patch("geoextent.lib.extent._extract_from_remote")
    def test_fromRemote_handles_errors_gracefully(self, mock_extract):
        """Test that fromRemote handles individual failures"""
        # Mock with first succeeds, second fails, third succeeds
        mock_extract.side_effect = [
            {"bbox": [5.0, 50.0, 6.0, 51.0], "crs": "4326"},
            Exception("Provider not found"),
            {"bbox": [7.0, 52.0, 8.0, 53.0], "crs": "4326"},
        ]

        identifiers = ["10.5281/zenodo.123", "invalid-doi", "10.25532/OPARA-789"]
        result = extent.fromRemote(identifiers, bbox=True)

        # Verify metadata reflects partial success
        self.assertEqual(result["extraction_metadata"]["total_resources"], 3)
        self.assertEqual(result["extraction_metadata"]["successful"], 2)
        self.assertEqual(result["extraction_metadata"]["failed"], 1)

        # Verify error is recorded
        self.assertIn("invalid-doi", result["details"])
        self.assertIn("error", result["details"]["invalid-doi"])

    @patch("geoextent.lib.extent._extract_from_remote")
    @patch("geoextent.lib.helpfunctions.bbox_merge")
    def test_fromRemote_merges_bboxes(self, mock_bbox_merge, mock_extract):
        """Test that fromRemote merges bounding boxes correctly"""
        # Mock responses with bboxes
        mock_extract.side_effect = [
            {"bbox": [5.0, 50.0, 6.0, 51.0], "crs": "4326"},
            {"bbox": [7.0, 52.0, 8.0, 53.0], "crs": "4326"},
        ]

        # Mock merged bbox
        mock_bbox_merge.return_value = {"bbox": [5.0, 50.0, 8.0, 53.0], "crs": "4326"}

        identifiers = ["10.5281/zenodo.123", "10.25532/OPARA-456"]
        result = extent.fromRemote(identifiers, bbox=True)

        # Verify merged bbox is present
        self.assertIn("bbox", result)
        self.assertEqual(result["bbox"], [5.0, 50.0, 8.0, 53.0])
        self.assertEqual(result["crs"], "4326")

        # Verify merge function was called
        mock_bbox_merge.assert_called_once()

    @patch("geoextent.lib.extent._extract_from_remote")
    @patch("geoextent.lib.helpfunctions.tbox_merge")
    def test_fromRemote_merges_temporal_extents(self, mock_tbox_merge, mock_extract):
        """Test that fromRemote merges temporal extents correctly"""
        # Mock responses with temporal extents
        mock_extract.side_effect = [
            {"tbox": ["2020-01-01", "2020-12-31"]},
            {"tbox": ["2021-01-01", "2021-12-31"]},
        ]

        # Mock merged tbox
        mock_tbox_merge.return_value = ["2020-01-01", "2021-12-31"]

        identifiers = ["10.5281/zenodo.123", "10.25532/OPARA-456"]
        result = extent.fromRemote(identifiers, tbox=True)

        # Verify merged tbox is present
        self.assertIn("tbox", result)
        self.assertEqual(result["tbox"], ["2020-01-01", "2021-12-31"])

        # Verify merge function was called
        mock_tbox_merge.assert_called_once()

    @patch("geoextent.lib.extent._extract_from_remote")
    def test_fromRemote_passes_parameters_to_fromRemote(self, mock_extract):
        """Test that all parameters are correctly passed to _extract_from_remote"""
        mock_extract.return_value = {}

        extent.fromRemote(
            ["10.5281/zenodo.123"],
            bbox=True,
            tbox=True,
            convex_hull=True,
            details=True,
            max_download_size="100MB",
            max_download_method="smallest",
            download_skip_nogeo=True,
            max_download_workers=8,
        )

        # Verify parameters were passed to _extract_from_remote
        call_kwargs = mock_extract.call_args[1]
        self.assertTrue(call_kwargs["bbox"])
        self.assertTrue(call_kwargs["tbox"])
        self.assertTrue(call_kwargs["convex_hull"])
        self.assertTrue(call_kwargs["details"])
        self.assertEqual(call_kwargs["max_download_size"], "100MB")
        self.assertEqual(call_kwargs["max_download_method"], "smallest")
        self.assertTrue(call_kwargs["download_skip_nogeo"])
        self.assertEqual(call_kwargs["max_download_workers"], 8)


if __name__ == "__main__":
    unittest.main()
