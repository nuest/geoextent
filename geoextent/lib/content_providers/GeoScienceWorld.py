"""
GeoScienceWorld (GSW) content provider for geoextent.

GeoScienceWorld is a publishing platform hosting geoscience journals from
multiple publishers (SEG, GSL, Mineralogical Society, etc.). Articles often
have GeoRef metadata with geographic coordinates embedded in the HTML as WKT
(POLYGON/POINT) inside ``<coordinates points='...'>`` elements.

The site is behind Cloudflare managed challenge protection. Uses ``curl_cffi``
with TLS fingerprint impersonation to bypass Cloudflare without a browser.

Supported identifiers:
- Article URLs: https://pubs.geoscienceworld.org/{pub}/{journal}/article-abstract/...
- Article URLs: https://pubs.geoscienceworld.org/{journal}/article/...
- GeoRef record URLs: https://pubs.geoscienceworld.org/georef/record/...
- DOIs from various publishers (10.1190, 10.1144, etc.) that resolve to GSW
"""

import json
import logging
import os
import re

from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

from ..exceptions import CloudflareBlockedError
from .providers import DoiProvider
from .journals._meta import parse_wkt as _parse_wkt

logger = logging.getLogger("geoextent")

# Regex for pubs.geoscienceworld.org URLs
_GSW_URL_RE = re.compile(
    r"https?://pubs\.geoscienceworld\.org/"
    r"(?:georef/record/|[^/]+/(?:[^/]+/)?article(?:-abstract)?/)"
)


def _parse_wkt_coordinates(points_json):
    """Parse WKT geometries from the JSON ``points`` attribute.

    Args:
        points_json: JSON string like ``{"Polygon":"POLYGON((...))","Point":"POINT(...)"}``

    Returns:
        list of (geometry_type, coordinates) tuples where coordinates are
        ``[[lon, lat], ...]`` for polygons or ``[lon, lat]`` for points.
        The WKT scalars are parsed by ``journals._meta.parse_wkt``, which is
        also used by the journal-platform providers.
    """
    try:
        data = json.loads(points_json)
    except (json.JSONDecodeError, TypeError):
        logger.debug("Failed to parse coordinates JSON: %s", points_json)
        return []

    geometries = []

    polygon_wkt = data.get("Polygon", "")
    if polygon_wkt:
        geom = _parse_wkt(polygon_wkt)
        if geom and geom.get("type") == "Polygon":
            rings = geom.get("coordinates") or []
            if rings and rings[0]:
                # GSW historically returned a flat outer-ring ``[[lon, lat], …]``.
                geometries.append(("Polygon", rings[0]))

    point_wkt = data.get("Point", "")
    if point_wkt:
        geom = _parse_wkt(point_wkt)
        if geom and geom.get("type") == "Point":
            geometries.append(("Point", geom["coordinates"]))

    return geometries


class GeoScienceWorld(DoiProvider):
    """Content provider for GeoScienceWorld (GSW).

    Extracts geographic coordinates from GeoRef metadata embedded in article
    HTML pages as WKT (POLYGON/POINT) inside ``<coordinates>`` elements.
    Temporal extent is extracted from publication date meta tags.

    This is a metadata-only provider — no data files are downloaded.
    """

    # No doi_prefixes: GSW hosts articles from many publishers (10.1190,
    # 10.1144, 10.1180, etc.). Phase 1 skips, Phase 2 validates via URL.
    doi_prefixes = ()

    @classmethod
    def provider_info(cls):
        return {
            "name": "GeoScienceWorld",
            "description": (
                "GeoScienceWorld is a publishing platform hosting geoscience "
                "journals from multiple publishers (SEG, GSL, Mineralogical "
                "Society, etc.). Articles include GeoRef metadata with "
                "geographic coordinates as WKT."
            ),
            "website": "https://pubs.geoscienceworld.org/",
            "supported_identifiers": [
                "https://pubs.geoscienceworld.org/{pub}/{journal}/article-abstract/{vol}/{issue}/{page}/{id}/{slug}",
                "https://pubs.geoscienceworld.org/georef/record/{type}/{id}/{slug}",
                "DOIs from various publishers that resolve to GSW",
            ],
            "doi_prefix": "Various (10.1190, 10.1144, 10.1180, ...)",
            "examples": [
                "https://pubs.geoscienceworld.org/seg/tle/article-abstract/44/12/952/721805/Diagenesis-and-pore-pressure-induced-dim-spots-on",
                "10.1190/tle44120952.1",
            ],
        }

    def __init__(self):
        super().__init__()
        self.name = "GeoScienceWorld"
        self.article_url = None

    @property
    def supports_metadata_extraction(self):
        return True

    def validate_provider(self, reference):
        """Validate if the reference points to a GeoScienceWorld article.

        Fast path: regex match on pubs.geoscienceworld.org URLs.
        DOI path: resolve DOI via doi.org, check if redirect lands on GSW.
        """
        self.reference = reference

        # Fast path: direct GSW URL
        if _GSW_URL_RE.match(reference):
            self.article_url = reference
            return True

        # DOI path: resolve and check
        url = self.get_url
        if _GSW_URL_RE.match(url):
            self.article_url = url
            return True

        return False

    def _fetch_article_html(self, url):
        """Fetch article HTML using curl_cffi with TLS impersonation.

        Uses Chrome TLS fingerprint impersonation to bypass Cloudflare's
        managed challenge without requiring a real browser.

        Raises:
            CloudflareBlockedError: If Cloudflare blocks the request (HTTP 403
                or ``cf-mitigated`` header present). Lets callers distinguish
                a transient block from a genuine "no metadata" outcome.

        Returns:
            str or None: HTML content, or None on non-Cloudflare failure
        """
        try:
            resp = cffi_requests.get(url, impersonate="chrome", timeout=30)
        except Exception as e:
            logger.warning("Failed to fetch GeoScienceWorld page %s: %s", url, e)
            return None

        if resp.status_code == 403 or resp.headers.get("cf-mitigated"):
            raise CloudflareBlockedError(
                url, provider="GeoScienceWorld", status_code=resp.status_code
            )

        try:
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Failed to fetch GeoScienceWorld page %s: %s", url, e)
            return None

        return resp.text

    def _extract_coordinates_from_html(self, html):
        """Parse ``<coordinates points='...'>`` elements from HTML.

        Returns:
            list of (geometry_type, coordinates) tuples
        """
        soup = BeautifulSoup(html, "html.parser")
        all_geometries = []

        for coord_elem in soup.find_all("coordinates"):
            points_attr = coord_elem.get("points")
            if points_attr:
                geoms = _parse_wkt_coordinates(points_attr)
                all_geometries.extend(geoms)

        return all_geometries

    def _extract_publication_date(self, html):
        """Extract publication date from HTML meta tags.

        Checks ``citation_publication_date`` and ``DC.Date`` meta tags.

        Returns:
            str or None: Date string (YYYY-MM-DD or YYYY/MM/DD)
        """
        soup = BeautifulSoup(html, "html.parser")

        # Try citation_publication_date first
        meta = soup.find("meta", attrs={"name": "citation_publication_date"})
        if meta and meta.get("content"):
            return meta["content"].strip()

        # Fall back to DC.Date
        meta = soup.find("meta", attrs={"name": "DC.Date"})
        if meta and meta.get("content"):
            return meta["content"].strip()

        return None

    def _normalize_date(self, date_str):
        """Normalize date string to YYYY-MM-DD format.

        Handles YYYY/MM/DD and YYYY-MM-DD inputs.

        Returns:
            str: Normalized date in YYYY-MM-DD format
        """
        if not date_str:
            return None
        # Replace / with -
        normalized = date_str.replace("/", "-")
        # Ensure we have at least YYYY-MM-DD
        parts = normalized.split("-")
        if len(parts) == 1:
            return f"{parts[0]}-01-01"
        elif len(parts) == 2:
            return f"{parts[0]}-{parts[1]}-01"
        return normalized[:10]

    def _create_metadata_geojson(self, folder, geometries, pub_date):
        """Write GeoJSON from extracted coordinates.

        Creates one Feature per coordinate entry.

        Returns:
            str or None: Path to created GeoJSON file, or None if no data
        """
        if not geometries and pub_date is None:
            logger.debug("GeoScienceWorld: no spatial or temporal metadata")
            return None

        properties = {
            "source": "GeoScienceWorld",
            "url": self.article_url,
        }
        if pub_date:
            normalized = self._normalize_date(pub_date)
            if normalized:
                properties["start_time"] = normalized
                properties["end_time"] = normalized

        features = []
        for geom_type, coords in geometries:
            if geom_type == "Polygon":
                # Ensure ring is closed
                if coords and coords[0] != coords[-1]:
                    coords = coords + [coords[0]]
                geometry = {
                    "type": "Polygon",
                    "coordinates": [coords],
                }
            elif geom_type == "Point":
                geometry = {
                    "type": "Point",
                    "coordinates": coords,
                }
            else:
                continue

            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": dict(properties),
                }
            )

        # If no spatial features but we have temporal, create a null-geometry feature
        if not features and pub_date:
            features.append(
                {
                    "type": "Feature",
                    "geometry": None,
                    "properties": properties,
                }
            )

        if not features:
            return None

        geojson_data = {
            "type": "FeatureCollection",
            "features": features,
        }

        # Generate a safe filename from the URL
        safe_name = re.sub(r"[^a-zA-Z0-9]", "_", self.article_url or "gsw")
        safe_name = safe_name[:80]  # Truncate to reasonable length
        geojson_file = os.path.join(folder, f"gsw_{safe_name}.geojson")
        with open(geojson_file, "w") as f:
            json.dump(geojson_data, f, indent=2)

        parts = []
        if geometries:
            parts.append(f"{len(geometries)} coordinate(s)")
        if pub_date:
            parts.append(f"date={pub_date}")
        logger.info(
            "Created GeoJSON metadata file for GeoScienceWorld article (%s)",
            ", ".join(parts),
        )
        return geojson_file

    def download(
        self,
        folder,
        throttle=False,
        download_data=True,
        show_progress=True,
        max_size_bytes=None,
        max_download_method="ordered",
        max_download_method_seed=None,
        download_skip_nogeo=False,
        download_skip_nogeo_exts=None,
        max_download_workers=4,
        progress_callback=None,
    ):
        """Extract metadata from a GeoScienceWorld article.

        This is always metadata-only — no data files are downloaded.
        The ``download_data`` parameter is accepted for API compatibility
        but ignored.
        """
        logger.info("Processing GeoScienceWorld article: %s", self.article_url)

        html = self._fetch_article_html(self.article_url)
        if html is None:
            logger.warning("Could not fetch GeoScienceWorld article.")
            return

        geometries = self._extract_coordinates_from_html(html)
        pub_date = self._extract_publication_date(html)

        result = self._create_metadata_geojson(folder, geometries, pub_date)
        if result is None:
            logger.warning(
                "GeoScienceWorld article has no extractable spatial or "
                "temporal metadata."
            )
