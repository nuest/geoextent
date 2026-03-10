import json
import pytest
import geoextent.lib.extent as geoextent
from conftest import NETWORK_SKIP_EXCEPTIONS
from geoextent.lib.content_providers.GeoScienceWorld import (
    GeoScienceWorld,
    _parse_wkt_coordinates,
)


class TestGeoScienceWorldProvider:
    """Test GeoScienceWorld (GSW) content provider."""

    # -- Fast validation tests (no network) --

    def test_gsw_url_validation(self):
        """Test that GeoScienceWorld URLs are correctly validated"""
        provider = GeoScienceWorld()

        # article-abstract URL
        assert provider.validate_provider(
            "https://pubs.geoscienceworld.org/seg/tle/article-abstract/"
            "44/12/952/721805/Diagenesis-and-pore-pressure-induced-dim-spots-on"
        )
        assert provider.article_url is not None

        # article URL (without -abstract)
        provider2 = GeoScienceWorld()
        assert provider2.validate_provider(
            "https://pubs.geoscienceworld.org/gsl/pg/article/"
            "32/1/petgeo2024-095/722925/Combined-geophysical-and-tectonostratigraphic"
        )

        # georef/record URL
        provider3 = GeoScienceWorld()
        assert provider3.validate_provider(
            "https://pubs.geoscienceworld.org/georef/record/"
            "6/5348889/Diagenesis-and-pore-pressure-induced-dim-spots-on"
        )

        # Short journal path (no publisher prefix)
        provider4 = GeoScienceWorld()
        assert provider4.validate_provider(
            "https://pubs.geoscienceworld.org/minersoc/minmag/article-abstract/"
            "89/6/751/723683/Nancyrossite-FeGeO6H5-a-new-hydroxyperovskite"
        )

    def test_gsw_validation_invalid_identifiers(self):
        """Test that non-GeoScienceWorld URLs are rejected"""
        provider = GeoScienceWorld()
        # Non-GSW URLs should not match the fast path
        assert not provider.validate_provider("https://zenodo.org/record/4593540")

        provider2 = GeoScienceWorld()
        assert not provider2.validate_provider("https://example.com/dataset/123")

    def test_gsw_provider_instantiation(self):
        """Test basic provider creation and metadata"""
        provider = GeoScienceWorld()
        assert provider.name == "GeoScienceWorld"
        assert provider.supports_metadata_extraction is True
        info = provider.provider_info()
        assert info["name"] == "GeoScienceWorld"
        assert "pubs.geoscienceworld.org" in info["website"]

    def test_gsw_wkt_parsing(self):
        """Unit test for WKT POLYGON/POINT parsing from coordinates JSON"""
        # Polygon + Point
        points_json = (
            '{"Polygon":"POLYGON((43 -25.6667,50.5 -25.6667,'
            '50.5 -11.8667,43 -11.8667,43 -25.6667))",'
            '"Point":"POINT(46.75 -18.7667)"}'
        )
        geometries = _parse_wkt_coordinates(points_json)
        assert len(geometries) == 2

        poly_type, poly_coords = geometries[0]
        assert poly_type == "Polygon"
        assert len(poly_coords) == 5  # Closed ring
        assert poly_coords[0] == [43.0, -25.6667]
        assert poly_coords[-1] == [43.0, -25.6667]

        pt_type, pt_coords = geometries[1]
        assert pt_type == "Point"
        assert abs(pt_coords[0] - 46.75) < 0.001
        assert abs(pt_coords[1] - (-18.7667)) < 0.001

    def test_gsw_wkt_parsing_point_only(self):
        """Test WKT parsing with only Point geometry"""
        points_json = '{"Point":"POINT(10.5 52.3)"}'
        geometries = _parse_wkt_coordinates(points_json)
        assert len(geometries) == 1
        assert geometries[0][0] == "Point"
        assert geometries[0][1] == [10.5, 52.3]

    def test_gsw_wkt_parsing_invalid_json(self):
        """Test WKT parsing with invalid JSON returns empty list"""
        assert _parse_wkt_coordinates("not json") == []
        assert _parse_wkt_coordinates(None) == []
        assert _parse_wkt_coordinates("") == []

    def test_gsw_extract_coordinates_from_html(self):
        """Test coordinate extraction from mock HTML"""
        provider = GeoScienceWorld()
        html = """
        <html><body>
        <div class="geoRef-coordinates">
            <ul>
                <li class="geoRef-coordinate">
                    <a href="/search"><content><coordinates points='{"Polygon":"POLYGON((43 -25.6667,50.5 -25.6667,50.5 -11.8667,43 -11.8667,43 -25.6667))","Point":"POINT(46.75 -18.7667)"}'></coordinates></content></a>
                </li>
            </ul>
        </div>
        </body></html>
        """
        geoms = provider._extract_coordinates_from_html(html)
        assert len(geoms) == 2
        assert geoms[0][0] == "Polygon"
        assert geoms[1][0] == "Point"

    def test_gsw_extract_publication_date(self):
        """Test publication date extraction from meta tags"""
        provider = GeoScienceWorld()

        # citation_publication_date
        html = '<html><head><meta name="citation_publication_date" content="2024/12/01"></head></html>'
        assert provider._extract_publication_date(html) == "2024/12/01"

        # DC.Date fallback
        html = '<html><head><meta name="DC.Date" content="2024-06-15"></head></html>'
        assert provider._extract_publication_date(html) == "2024-06-15"

        # No date
        html = "<html><head></head></html>"
        assert provider._extract_publication_date(html) is None

    def test_gsw_normalize_date(self):
        """Test date normalization"""
        provider = GeoScienceWorld()
        assert provider._normalize_date("2024/12/01") == "2024-12-01"
        assert provider._normalize_date("2024-06-15") == "2024-06-15"
        assert provider._normalize_date("2024") == "2024-01-01"
        assert provider._normalize_date("2024-06") == "2024-06-01"
        assert provider._normalize_date(None) is None

    # -- Network tests (auto-marked slow via conftest) --

    def test_gsw_metadata_only_extraction(self):
        """Test metadata-only extraction from a GSW article (provider_sample smoke test).

        Uses the Mozambique Channel article which has known coordinates:
        S25deg40' - S11deg52', E43deg00' - E50deg30'
        """
        try:
            result = geoextent.from_remote(
                "https://pubs.geoscienceworld.org/seg/tle/article-abstract/"
                "44/12/952/721805/"
                "Diagenesis-and-pore-pressure-induced-dim-spots-on",
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or GeoScienceWorld unreachable")
        except Exception as e:
            if any(
                kw in str(e)
                for kw in ("Connection", "Max retries", "Timeout", "Cloudflare")
            ):
                pytest.skip(f"GeoScienceWorld unreachable: {e}")
            raise

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from GeoScienceWorld metadata"
        # Default output: [minlat, minlon, maxlat, maxlon]
        minlat, minlon, maxlat, maxlon = bbox
        # Mozambique Channel area: roughly S26 to S12, E43 to E51
        assert -30 < minlat < -10
        assert 40 < minlon < 55

    def test_gsw_georef_record_extraction(self):
        """Test extraction from a GeoRef record URL"""
        try:
            result = geoextent.from_remote(
                "https://pubs.geoscienceworld.org/georef/record/"
                "6/5348889/"
                "Diagenesis-and-pore-pressure-induced-dim-spots-on",
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or GeoScienceWorld unreachable")
        except Exception as e:
            if any(
                kw in str(e)
                for kw in ("Connection", "Max retries", "Timeout", "Cloudflare")
            ):
                pytest.skip(f"GeoScienceWorld unreachable: {e}")
            raise

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from GeoRef record"

    def test_gsw_doi_extraction(self):
        """Test extraction via DOI that resolves to GeoScienceWorld"""
        try:
            result = geoextent.from_remote(
                "10.1190/tle44120952.1",
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or DOI resolution failed")
        except Exception as e:
            if any(
                kw in str(e)
                for kw in ("Connection", "Max retries", "Timeout", "Cloudflare")
            ):
                pytest.skip(f"GeoScienceWorld unreachable: {e}")
            raise

        assert result is not None
        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from DOI resolving to GSW"

    def test_gsw_article_with_temporal(self):
        """Test that temporal extent is extracted from publication date"""
        try:
            result = geoextent.from_remote(
                "https://pubs.geoscienceworld.org/seg/tle/article-abstract/"
                "44/12/952/721805/"
                "Diagenesis-and-pore-pressure-induced-dim-spots-on",
                bbox=True,
                tbox=True,
                download_data=False,
            )
        except NETWORK_SKIP_EXCEPTIONS:
            pytest.skip("Network unavailable or GeoScienceWorld unreachable")
        except Exception as e:
            if any(
                kw in str(e)
                for kw in ("Connection", "Max retries", "Timeout", "Cloudflare")
            ):
                pytest.skip(f"GeoScienceWorld unreachable: {e}")
            raise

        assert result is not None
        tbox = result.get("tbox")
        # Publication date should give us a temporal extent
        if tbox is not None:
            assert len(tbox) == 2

    # -- Convex hull test (no network, mocked HTML) --

    def test_gsw_convex_hull_multiple_coordinates(self, tmp_path, monkeypatch):
        """Verify convex hull with multiple <coordinates> entries.

        Mocks the HTML fetch to return two non-overlapping coordinate regions.
        With convex_hull=True, the result should contain >4 unique vertices.
        """
        # Mock HTML with two separate coordinate entries
        mock_html = """
        <html>
        <head>
            <meta name="citation_publication_date" content="2024/06/01">
        </head>
        <body>
        <div class="geoRef-coordinates">
            <ul>
                <li class="geoRef-coordinate">
                    <a><content><coordinates points='{"Polygon":"POLYGON((10 50,20 50,20 55,10 55,10 50))","Point":"POINT(15 52.5)"}'></coordinates></content></a>
                </li>
                <li class="geoRef-coordinate">
                    <a><content><coordinates points='{"Polygon":"POLYGON((-80 25,-70 25,-70 35,-80 35,-80 25))","Point":"POINT(-75 30)"}'></coordinates></content></a>
                </li>
            </ul>
        </div>
        </body>
        </html>
        """

        def mock_fetch(self_inner, url):
            return mock_html

        monkeypatch.setattr(GeoScienceWorld, "_fetch_article_html", mock_fetch)

        # Also mock validate_provider to avoid DOI resolution
        original_validate = GeoScienceWorld.validate_provider

        def mock_validate(self_inner, reference):
            self_inner.reference = reference
            self_inner.article_url = reference
            return True

        monkeypatch.setattr(GeoScienceWorld, "validate_provider", mock_validate)

        result = geoextent.from_remote(
            "https://pubs.geoscienceworld.org/test/article-abstract/1/1/1/1/test",
            bbox=True,
            tbox=True,
            download_data=False,
            convex_hull=True,
        )

        assert result is not None
        assert result.get("convex_hull") is True

        bbox = result.get("bbox")
        assert bbox is not None, "Expected bbox from merged coordinates"
        # In convex hull mode, bbox is a GeoJSON Polygon dict
        assert isinstance(bbox, dict), f"Expected dict, got {type(bbox)}"
        assert bbox.get("type") == "Polygon"
        coords = bbox["coordinates"][0]
        # Two non-overlapping polygons should produce >4 unique vertices
        unique_coords = set(tuple(c) for c in coords[:-1])
        assert len(unique_coords) > 4, (
            f"Expected >4 unique vertices for convex hull of two disjoint "
            f"polygons, got {len(unique_coords)}: {unique_coords}"
        )

        tbox = result.get("tbox")
        assert tbox is not None
        assert tbox[0] == "2024-06-01"
        assert tbox[1] == "2024-06-01"
