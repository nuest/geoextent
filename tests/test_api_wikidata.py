import pytest
import geoextent.lib.extent as geoextent
from geoextent.lib.content_providers.Wikidata import Wikidata


class TestWikidataValidation:
    """Fast validation tests for Wikidata provider (no network calls)."""

    def test_wikidata_provider_instantiation(self):
        """Test that Wikidata provider can be instantiated."""
        provider = Wikidata()
        assert provider.name == "Wikidata"

    def test_wikidata_q_number_validation(self):
        """Test Q-number validation."""
        provider = Wikidata()
        assert provider.validate_provider("Q64") is True
        assert provider.qid == "Q64"

    def test_wikidata_q_number_lowercase_validation(self):
        """Test lowercase Q-number validation."""
        provider = Wikidata()
        assert provider.validate_provider("q64") is True
        assert provider.qid == "Q64"

    def test_wikidata_q_number_large_validation(self):
        """Test large Q-number validation."""
        provider = Wikidata()
        assert provider.validate_provider("Q60786916") is True
        assert provider.qid == "Q60786916"

    def test_wikidata_url_validation(self):
        """Test Wikidata wiki URL validation."""
        provider = Wikidata()
        assert provider.validate_provider("https://www.wikidata.org/wiki/Q64") is True
        assert provider.qid == "Q64"

    def test_wikidata_url_no_www_validation(self):
        """Test Wikidata URL without www prefix."""
        provider = Wikidata()
        assert provider.validate_provider("https://wikidata.org/wiki/Q64") is True
        assert provider.qid == "Q64"

    def test_wikidata_entity_url_validation(self):
        """Test Wikidata entity URI validation."""
        provider = Wikidata()
        assert provider.validate_provider("http://www.wikidata.org/entity/Q64") is True
        assert provider.qid == "Q64"

    def test_wikidata_entity_url_https_validation(self):
        """Test Wikidata entity URI with HTTPS."""
        provider = Wikidata()
        assert provider.validate_provider("https://www.wikidata.org/entity/Q35") is True
        assert provider.qid == "Q35"

    def test_wikidata_invalid_identifiers(self):
        """Test that non-Wikidata identifiers are not matched."""
        provider = Wikidata()

        assert provider.validate_provider("10.5281/zenodo.123456") is False
        assert provider.validate_provider("https://zenodo.org/records/123") is False
        assert provider.validate_provider("Q") is False
        assert provider.validate_provider("Q") is False
        assert provider.validate_provider("hello") is False
        assert provider.validate_provider("") is False

    def test_wikidata_url_patterns(self):
        """Test various Wikidata URL patterns."""
        urls = [
            ("https://www.wikidata.org/wiki/Q64", "Q64"),
            ("https://wikidata.org/wiki/Q35", "Q35"),
            ("http://www.wikidata.org/entity/Q60786916", "Q60786916"),
            ("https://www.wikidata.org/entity/Q26080", "Q26080"),
        ]

        for url, expected_qid in urls:
            provider = Wikidata()
            assert (
                provider.validate_provider(url) is True
            ), f"Should validate URL: {url}"
            assert (
                provider.qid == expected_qid
            ), f"QID mismatch for {url}: {provider.qid} != {expected_qid}"

    def test_wikidata_parse_wkt_point(self):
        """Test WKT Point parsing."""
        assert Wikidata._parse_wkt_point("Point(13.383333 52.516667)") == (
            13.383333,
            52.516667,
        )
        assert Wikidata._parse_wkt_point("Point(-73.935242 40.730610)") == (
            -73.935242,
            40.730610,
        )
        assert Wikidata._parse_wkt_point("invalid") is None
        assert Wikidata._parse_wkt_point("") is None

    def test_wikidata_extract_coordinates_full_bbox(self):
        """Test coordinate extraction with full extreme coordinates."""
        provider = Wikidata()
        sparql_result = {
            "results": {
                "bindings": [
                    {
                        "northLat": {"type": "literal", "value": "52.6754"},
                        "southLat": {"type": "literal", "value": "52.33859"},
                        "eastLon": {"type": "literal", "value": "13.76104"},
                        "westLon": {"type": "literal", "value": "13.08825"},
                        "coord": {
                            "type": "literal",
                            "value": "Point(13.383333 52.516667)",
                        },
                    }
                ]
            }
        }

        coords = provider._extract_coordinates(sparql_result)
        assert coords is not None
        bbox = coords["bbox"]
        assert bbox[0] == pytest.approx(13.08825, abs=0.001)  # west
        assert bbox[1] == pytest.approx(52.33859, abs=0.001)  # south
        assert bbox[2] == pytest.approx(13.76104, abs=0.001)  # east
        assert bbox[3] == pytest.approx(52.6754, abs=0.001)  # north

    def test_wikidata_extract_coordinates_point_only(self):
        """Test coordinate extraction with P625 point only."""
        provider = Wikidata()
        sparql_result = {
            "results": {
                "bindings": [
                    {
                        "coord": {
                            "type": "literal",
                            "value": "Point(13.38641 48.99549)",
                        },
                    }
                ]
            }
        }

        coords = provider._extract_coordinates(sparql_result)
        assert coords is not None
        bbox = coords["bbox"]
        # Single point: bbox with zero extent
        assert bbox[0] == pytest.approx(13.38641, abs=0.001)
        assert bbox[1] == pytest.approx(48.99549, abs=0.001)
        assert bbox[0] == bbox[2]  # minlon == maxlon
        assert bbox[1] == bbox[3]  # minlat == maxlat

    def test_wikidata_extract_coordinates_multiple_points(self):
        """Test coordinate extraction with multiple P625 points."""
        provider = Wikidata()
        sparql_result = {
            "results": {
                "bindings": [
                    {
                        "coord": {
                            "type": "literal",
                            "value": "Point(6.883333 53.533333)",
                        },
                    },
                    {
                        "coord": {
                            "type": "literal",
                            "value": "Point(8.6 55.233333)",
                        },
                    },
                ]
            }
        }

        coords = provider._extract_coordinates(sparql_result)
        assert coords is not None
        bbox = coords["bbox"]
        assert bbox[0] == pytest.approx(6.883333, abs=0.001)  # west
        assert bbox[1] == pytest.approx(53.533333, abs=0.001)  # south
        assert bbox[2] == pytest.approx(8.6, abs=0.001)  # east
        assert bbox[3] == pytest.approx(55.233333, abs=0.001)  # north

    def test_wikidata_extract_coordinates_empty(self):
        """Test coordinate extraction with no results."""
        provider = Wikidata()
        sparql_result = {"results": {"bindings": []}}
        assert provider._extract_coordinates(sparql_result) is None

    def test_wikidata_can_be_used_q_number(self):
        """Test that Q-numbers are properly recognized."""
        provider = Wikidata()
        q_numbers = ["Q64", "Q35", "Q26080", "Q60786916", "Q1234567"]
        for q in q_numbers:
            provider_fresh = Wikidata()
            assert (
                provider_fresh.validate_provider(q) is True
            ), f"Should validate Q-number: {q}"


class TestWikidataExtraction:
    """Network-dependent tests for Wikidata provider."""

    def test_wikidata_metadata_only_extraction(self):
        """Test metadata-only extraction from Wikidata (provider_sample smoke test).

        Entity: Berlin (Q64) - German capital with full extreme coordinates.
        """
        result = geoextent.fromRemote(
            "Q64",
            bbox=True,
            tbox=False,
            download_data=False,
        )

        assert result is not None
        assert result["format"] == "remote"

    def test_wikidata_berlin_bbox_extraction(self):
        """Test full bbox extraction from Wikidata for Berlin (Q64).

        Berlin has P1332-P1335 extreme coordinates:
        North ~52.68, South ~52.34, East ~13.76, West ~13.09
        """
        result = geoextent.fromRemote(
            "Q64",
            bbox=True,
            tbox=False,
        )

        assert result is not None
        assert result["format"] == "remote"
        assert "bbox" in result

        bbox = result["bbox"]
        assert len(bbox) == 4
        # Berlin bbox in EPSG:4326 native order [minlat, minlon, maxlat, maxlon]
        assert 52.0 <= bbox[0] <= 52.5, f"South latitude {bbox[0]} out of range"
        assert 13.0 <= bbox[1] <= 13.2, f"West longitude {bbox[1]} out of range"
        assert 52.5 <= bbox[2] <= 53.0, f"North latitude {bbox[2]} out of range"
        assert 13.5 <= bbox[3] <= 14.0, f"East longitude {bbox[3]} out of range"
        assert result.get("crs") == "4326"

    def test_wikidata_denmark_bbox_extraction(self):
        """Test bbox extraction for Denmark (Q35).

        Denmark has full extreme coordinates:
        North ~57.75, South ~54.56, East ~15.20, West ~8.07
        """
        result = geoextent.fromRemote(
            "Q35",
            bbox=True,
            tbox=False,
        )

        assert result is not None
        assert "bbox" in result

        bbox = result["bbox"]
        assert len(bbox) == 4
        # Denmark bbox in EPSG:4326 native order [minlat, minlon, maxlat, maxlon]
        assert 54.0 <= bbox[0] <= 55.0, f"South latitude {bbox[0]} out of range"
        assert 7.0 <= bbox[1] <= 9.0, f"West longitude {bbox[1]} out of range"
        assert 57.0 <= bbox[2] <= 58.5, f"North latitude {bbox[2]} out of range"
        assert 14.0 <= bbox[3] <= 16.0, f"East longitude {bbox[3]} out of range"

    def test_wikidata_bavarian_forest_point_extraction(self):
        """Test point fallback for Bavarian Forest NP (Q60786916).

        This entity has only P625 (coordinate location), no extreme coordinates.
        Expected point: ~13.39°E, ~49.00°N
        """
        result = geoextent.fromRemote(
            "Q60786916",
            bbox=True,
            tbox=False,
        )

        assert result is not None
        assert "bbox" in result

        bbox = result["bbox"]
        assert len(bbox) == 4
        # Single point creates zero-extent bbox
        # In EPSG:4326 native order: [minlat, minlon, maxlat, maxlon]
        assert 48.5 <= bbox[0] <= 49.5, f"Latitude {bbox[0]} out of range"
        assert 13.0 <= bbox[1] <= 14.0, f"Longitude {bbox[1]} out of range"

    def test_wikidata_wadden_sea_multipoint_extraction(self):
        """Test multi-point bbox for Wadden Sea (Q26080).

        This entity has multiple P625 points but no extreme coordinates.
        Points roughly at (6.88, 53.53) and (8.6, 55.23).
        """
        result = geoextent.fromRemote(
            "Q26080",
            bbox=True,
            tbox=False,
        )

        assert result is not None
        assert "bbox" in result

        bbox = result["bbox"]
        assert len(bbox) == 4
        # Multi-point bbox in EPSG:4326 native order [minlat, minlon, maxlat, maxlon]
        assert 53.0 <= bbox[0] <= 54.0, f"South latitude {bbox[0]} out of range"
        assert 6.0 <= bbox[1] <= 7.5, f"West longitude {bbox[1]} out of range"
        assert 54.5 <= bbox[2] <= 56.0, f"North latitude {bbox[2]} out of range"
        assert 8.0 <= bbox[3] <= 9.5, f"East longitude {bbox[3]} out of range"

    def test_wikidata_url_extraction(self):
        """Test extraction using Wikidata URL instead of Q-number."""
        result = geoextent.fromRemote(
            "https://www.wikidata.org/wiki/Q64",
            bbox=True,
            tbox=False,
        )

        assert result is not None
        assert result["format"] == "remote"
        assert "bbox" in result

    def test_wikidata_entity_url_extraction(self):
        """Test extraction using Wikidata entity URI."""
        result = geoextent.fromRemote(
            "http://www.wikidata.org/entity/Q64",
            bbox=True,
            tbox=False,
        )

        assert result is not None
        assert result["format"] == "remote"
        assert "bbox" in result

    def test_wikidata_identifier_variants_extraction(self):
        """Test that Q-number and URLs produce the same extraction result."""
        variants = [
            "Q64",
            "https://www.wikidata.org/wiki/Q64",
            "http://www.wikidata.org/entity/Q64",
        ]

        results = []
        for identifier in variants:
            result = geoextent.fromRemote(
                identifier,
                bbox=True,
                tbox=False,
            )
            assert result is not None, f"Failed for identifier: {identifier}"
            assert result["format"] == "remote", f"Wrong format for: {identifier}"
            assert "bbox" in result, f"No bbox for identifier: {identifier}"
            results.append(result["bbox"])

        # All variants should produce the same bounding box
        for i in range(4):
            assert (
                abs(results[0][i] - results[1][i]) < 0.001
            ), f"Coordinate {i} differs between Q64 and wiki URL"
            assert (
                abs(results[0][i] - results[2][i]) < 0.001
            ), f"Coordinate {i} differs between Q64 and entity URI"
