"""
Tests to verify fromRemote works correctly with single string inputs
"""

import unittest
from unittest.mock import patch, MagicMock
from geoextent.lib import extent


class TestFromRemoteWrapper(unittest.TestCase):
    """Test cases for fromRemote with single string inputs"""

    @patch("geoextent.lib.extent._extract_from_remote")
    def test_fromRemote_processes_single_identifier(self, mock_extract):
        """Test that fromRemote handles single string identifier correctly"""
        # Mock _extract_from_remote to return extent data
        mock_extract.return_value = {
            "bbox": [5.0, 50.0, 6.0, 51.0],
            "crs": "4326",
            "tbox": ["2020-01-01", "2020-12-31"],
        }

        # Call fromRemote with a single identifier
        result = extent.fromRemote("10.5281/zenodo.4593540", bbox=True, tbox=True)

        # Verify it returns the expected format
        self.assertIn("bbox", result)
        self.assertIn("tbox", result)
        self.assertEqual(result["format"], "remote")  # Should preserve 'remote' format
        self.assertEqual(result["bbox"], [5.0, 50.0, 6.0, 51.0])

    @patch("geoextent.lib.extent._extract_from_remote")
    def test_fromRemote_raises_exception_on_error(self, mock_extract):
        """Test that fromRemote raises exceptions for single identifier errors"""
        # Mock _extract_from_remote to raise an error
        mock_extract.side_effect = Exception("Provider not found")

        # Verify exception is raised
        with self.assertRaises(Exception) as context:
            extent.fromRemote("invalid-identifier", bbox=True)

        self.assertIn("Provider not found", str(context.exception))

    @patch("geoextent.lib.extent._extract_from_remote")
    def test_fromRemote_passes_all_parameters(self, mock_extract):
        """Test that fromRemote passes all parameters through correctly"""
        # Mock _extract_from_remote to return extent data
        mock_extract.return_value = {"bbox": [1, 2, 3, 4], "crs": "4326"}

        result = extent.fromRemote(
            "10.5281/zenodo.123",
            bbox=True,
            tbox=True,
            convex_hull=True,
            details=True,
            max_download_size="50MB",
            max_download_method="smallest",
            download_skip_nogeo=True,
            max_download_workers=2,
        )

        # Verify the instance method was called with correct parameters
        call_kwargs = mock_extract.call_args[1]
        self.assertTrue(call_kwargs["bbox"])
        self.assertTrue(call_kwargs["tbox"])
        self.assertTrue(call_kwargs["convex_hull"])
        self.assertTrue(call_kwargs["details"])
        self.assertEqual(call_kwargs["max_download_size"], "50MB")
        self.assertEqual(call_kwargs["max_download_method"], "smallest")
        self.assertTrue(call_kwargs["download_skip_nogeo"])
        self.assertEqual(call_kwargs["max_download_workers"], 2)

    @patch("geoextent.lib.extent._extract_from_remote")
    def test_fromRemote_backward_compatibility(self, mock_extract):
        """Test that fromRemote maintains backward compatibility with existing code"""
        # Mock _extract_from_remote to return extent data
        mock_extract.return_value = {
            "bbox": [7.6, 51.95, 7.65, 52.0],
            "crs": "4326",
            "tbox": ["2019-01-01", "2019-12-31"],
        }

        # This is how existing code would call fromRemote
        result = extent.fromRemote(
            "https://doi.org/10.5281/zenodo.4593540", bbox=True, tbox=True
        )

        # Verify the structure is backward compatible
        self.assertEqual(result["format"], "remote")
        self.assertIsInstance(result["bbox"], list)
        self.assertEqual(len(result["bbox"]), 4)
        self.assertIsInstance(result["tbox"], list)
        self.assertEqual(len(result["tbox"]), 2)


if __name__ == "__main__":
    unittest.main()
