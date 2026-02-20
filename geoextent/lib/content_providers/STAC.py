"""
STAC (SpatioTemporal Asset Catalog) content provider for geoextent.

STAC is an OGC Community Standard for describing geospatial information.
This provider extracts spatial and temporal extents from STAC Collections,
which contain pre-computed aggregate bounding boxes and time intervals.

Supported identifiers:
- STAC Collection URLs: https://{host}/collections/{id}
- STAC API URLs with /stac/ path segments
- Known STAC API hostnames (Element84, DLR, Terradue, WorldPop, etc.)

Metadata extraction approach:
- Fetch the STAC Collection JSON directly
- Extract extent.spatial.bbox and extent.temporal.interval
- Create a GeoJSON file with the bounding box polygon and temporal properties

This is a metadata-only provider — STAC Collections already contain exactly
the extent information geoextent needs, without downloading data files.
"""

import json
import logging
import os
import re
from urllib.parse import urlparse

import requests

from geoextent.lib.content_providers.providers import ContentProvider

logger = logging.getLogger("geoextent")

# Known STAC API hostnames (for fast-path URL matching without network)
_KNOWN_STAC_HOSTS = {
    "earth-search.aws.element84.com",
    "planetarycomputer.microsoft.com",
    "geoservice.dlr.de",
    "cmr.earthdata.nasa.gov",
    "stac.dataspace.copernicus.eu",
    "api.stac.worldpop.org",
    "gep-supersites-stac.terradue.com",
    "api.lantmateriet.se",
}

# URL patterns that indicate a STAC resource
_STAC_PATH_RE = re.compile(
    r"/stac(?:/|$)"  # path contains /stac/ or ends with /stac
    r"|/collections/[^/]+$"  # ends with /collections/{id}
    r"|/collections/[^/]+/items",  # items endpoint
    re.IGNORECASE,
)


def _is_stac_json(data):
    """Check if a JSON dict is a STAC resource.

    Args:
        data (dict): Parsed JSON response

    Returns:
        str or None: STAC type ('Collection', 'Catalog', 'Feature') or None
    """
    if not isinstance(data, dict):
        return None
    if "stac_version" not in data:
        return None
    stac_type = data.get("type")
    if stac_type in ("Feature", "Collection", "Catalog"):
        return stac_type
    return None


def _bbox_to_polygon(bbox):
    """Convert a [west, south, east, north] bbox to a GeoJSON Polygon.

    Coordinates are in [longitude, latitude] order per RFC 7946.

    Args:
        bbox (list): [west, south, east, north]

    Returns:
        dict: GeoJSON Polygon geometry
    """
    west, south, east, north = bbox
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [west, south],
                [east, south],
                [east, north],
                [west, north],
                [west, south],
            ]
        ],
    }


class STAC(ContentProvider):
    """Content provider for STAC (SpatioTemporal Asset Catalog).

    Extracts spatial and temporal extents from STAC Collection metadata.
    This is a metadata-only provider — no data files are downloaded.
    """

    @classmethod
    def provider_info(cls):
        return {
            "name": "STAC",
            "description": (
                "SpatioTemporal Asset Catalog (STAC) is an OGC Community "
                "Standard for describing geospatial information. Supports "
                "extraction of spatial bounding boxes and temporal intervals "
                "from STAC Collections served by any STAC-compliant API."
            ),
            "website": "https://stacspec.org/",
            "supported_identifiers": [
                "https://{host}/stac/v1/collections/{id}",
                "https://{host}/collections/{id}",
            ],
            "examples": [
                "https://earth-search.aws.element84.com/v1/collections/naip",
                "https://geoservice.dlr.de/eoc/ogc/stac/v1/collections/FOREST_STRUCTURE_DE_COVER_P1Y",
                "https://api.stac.worldpop.org/collections/CHE",
            ],
            "notes": (
                "Metadata-only provider. Extracts pre-computed spatial and "
                "temporal extents directly from STAC Collection JSON. No data "
                "files are downloaded. Supports STAC API v1.0 and v1.1."
            ),
        }

    @property
    def supports_metadata_extraction(self):
        return True

    def __init__(self):
        super().__init__()
        self.name = "STAC"
        self.reference = None
        self.collection_url = None
        self.collection_id = None
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "nuest/geoextent",
                "Accept": "application/json",
            }
        )

    def validate_provider(self, reference):
        """Check if the reference is a STAC resource URL.

        Uses a two-stage approach:
        1. Fast offline check: known hostnames and URL path patterns
        2. Network fallback: fetch URL and inspect JSON for stac_version

        Args:
            reference (str): URL to validate

        Returns:
            bool: True if this is a STAC resource URL
        """
        self.reference = reference

        # Must be an HTTP(S) URL
        try:
            parsed = urlparse(reference)
        except Exception:
            return False

        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Stage 1: Fast offline matching
        # Check known STAC API hostnames
        if hostname in _KNOWN_STAC_HOSTS:
            self.collection_url = reference
            self.collection_id = self._extract_collection_id(parsed.path)
            return True

        # Check URL path patterns
        if _STAC_PATH_RE.search(parsed.path):
            self.collection_url = reference
            self.collection_id = self._extract_collection_id(parsed.path)
            return True

        # Stage 2: Network fallback — fetch and check for stac_version
        try:
            response = self.session.get(reference, timeout=30)
            if response.status_code != 200:
                return False

            content_type = response.headers.get("content-type", "")
            if "json" not in content_type and "geo+json" not in content_type:
                return False

            data = response.json()
            stac_type = _is_stac_json(data)
            if stac_type:
                self.collection_url = reference
                self.collection_id = self._extract_collection_id(parsed.path)
                # Cache the fetched data to avoid re-fetching in download()
                self._cached_data = data
                self._cached_type = stac_type
                return True
        except Exception:
            logger.debug("STAC network validation failed for %s", reference)

        return False

    def _extract_collection_id(self, path):
        """Extract collection ID from URL path.

        Args:
            path (str): URL path component

        Returns:
            str: Collection ID or last path segment
        """
        # Match /collections/{id} pattern
        m = re.search(r"/collections/([^/]+)(?:/|$)", path)
        if m:
            return m.group(1)
        # Fall back to last non-empty path segment
        segments = [s for s in path.split("/") if s]
        return segments[-1] if segments else "unknown"

    def _fetch_collection(self):
        """Fetch STAC Collection JSON.

        Tries content negotiation: requests application/json explicitly.
        If the URL returns HTML (e.g. OGC API with content negotiation),
        retries with ?f=application/json query parameter.

        Returns:
            dict: Parsed STAC JSON, or None on failure
        """
        # Use cached data if available (from validate_provider network check)
        if hasattr(self, "_cached_data") and self._cached_data is not None:
            data = self._cached_data
            self._cached_data = None  # clear cache after use
            return data

        url = self.collection_url

        try:
            response = self.session.get(url, timeout=60)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            # If we got HTML back, try OGC API format parameter
            if "html" in content_type and "json" not in content_type:
                logger.debug(
                    "STAC URL returned HTML, retrying with ?f=application/json"
                )
                separator = "&" if "?" in url else "?"
                json_url = f"{url}{separator}f=application/json"
                response = self.session.get(json_url, timeout=60)
                response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.warning("Failed to fetch STAC resource %s: %s", url, e)
            return None

    def _extract_spatial(self, data):
        """Extract spatial extent from STAC JSON.

        For Collections: uses extent.spatial.bbox (first element).
        For Items: uses bbox field directly.

        Args:
            data (dict): Parsed STAC JSON

        Returns:
            dict or None: {'bbox': [w,s,e,n], 'geometry': GeoJSON Polygon} or None
        """
        stac_type = data.get("type")

        if stac_type == "Collection":
            try:
                bboxes = data["extent"]["spatial"]["bbox"]
                # First bbox is the overall extent
                bbox = bboxes[0]
                if len(bbox) >= 4:
                    return {
                        "bbox": bbox[:4],
                        "geometry": _bbox_to_polygon(bbox[:4]),
                    }
            except (KeyError, IndexError, TypeError):
                pass

        elif stac_type == "Feature":
            # STAC Item (GeoJSON Feature)
            bbox = data.get("bbox")
            if bbox and len(bbox) >= 4:
                return {
                    "bbox": bbox[:4],
                    "geometry": data.get("geometry") or _bbox_to_polygon(bbox[:4]),
                }

        return None

    def _extract_temporal(self, data):
        """Extract temporal extent from STAC JSON.

        For Collections: uses extent.temporal.interval (first element).
        For Items: uses properties.datetime or start_datetime/end_datetime.

        Handles open-ended ranges where end date is null.

        Args:
            data (dict): Parsed STAC JSON

        Returns:
            tuple or None: (start_date, end_date) strings (YYYY-MM-DD), or None.
                end_date may be None for open-ended ranges.
        """
        stac_type = data.get("type")

        if stac_type == "Collection":
            try:
                intervals = data["extent"]["temporal"]["interval"]
                # First interval is the overall range
                interval = intervals[0]
                start_dt = interval[0]
                end_dt = interval[1]  # may be null/None

                start_date = start_dt[:10] if start_dt else None
                end_date = end_dt[:10] if end_dt else None

                if start_date or end_date:
                    return (start_date, end_date)
            except (KeyError, IndexError, TypeError):
                pass

        elif stac_type == "Feature":
            props = data.get("properties", {})
            dt = props.get("datetime")
            if dt:
                return (dt[:10], dt[:10])
            start = props.get("start_datetime")
            end = props.get("end_datetime")
            if start or end:
                start_date = start[:10] if start else None
                end_date = end[:10] if end else None
                return (start_date, end_date)

        return None

    def _create_geojson(self, data, spatial, temporal, folder):
        """Create a GeoJSON file from extracted STAC metadata.

        Args:
            data (dict): Original STAC JSON
            spatial (dict or None): Spatial extent with 'bbox' and 'geometry'
            temporal (tuple or None): (start_date, end_date)
            folder (str): Target directory

        Returns:
            str or None: Path to created GeoJSON file, or None if no data
        """
        if spatial is None and temporal is None:
            logger.warning(
                "STAC resource %s: no spatial or temporal data found",
                self.collection_url,
            )
            return None

        properties = {
            "source": "STAC",
            "collection_id": self.collection_id or data.get("id", "unknown"),
            "url": self.collection_url,
        }

        # Add metadata from STAC JSON
        if data.get("title"):
            properties["title"] = data["title"]
        if data.get("description"):
            # Truncate long descriptions
            desc = data["description"]
            properties["description"] = desc[:500] if len(desc) > 500 else desc
        if data.get("stac_version"):
            properties["stac_version"] = data["stac_version"]

        if temporal:
            properties["start_time"] = temporal[0]
            properties["end_time"] = temporal[1]

        geometry = spatial["geometry"] if spatial else None

        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": properties,
                }
            ],
        }

        safe_id = re.sub(r"[^\w\-.]", "_", self.collection_id or "unknown")
        filename = f"stac_{safe_id}.geojson"
        filepath = os.path.join(folder, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)

        logger.debug("Created STAC GeoJSON file: %s", filepath)
        return filepath

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
    ):
        """Extract metadata from STAC and create GeoJSON.

        STAC Collections already contain pre-computed extents, so this
        provider always operates in metadata-only mode regardless of
        ``download_data``.

        Args:
            folder (str): Target directory for GeoJSON output
            (other parameters accepted for API compatibility)

        Returns:
            str: Path to output directory
        """
        logger.info("Extracting metadata from STAC resource: %s", self.collection_url)

        safe_id = re.sub(r"[^\w\-.]", "_", self.collection_id or "unknown")
        download_dir = os.path.join(folder, f"stac_{safe_id}")
        os.makedirs(download_dir, exist_ok=True)

        # Fetch STAC JSON
        data = self._fetch_collection()
        if data is None:
            logger.warning("Failed to fetch STAC resource: %s", self.collection_url)
            return download_dir

        stac_type = _is_stac_json(data)
        if not stac_type:
            logger.warning("URL %s did not return valid STAC JSON", self.collection_url)
            return download_dir

        logger.info(
            "STAC %s: %s (v%s)",
            stac_type,
            data.get("id", "unknown"),
            data.get("stac_version", "?"),
        )

        # Extract extents
        spatial = self._extract_spatial(data)
        temporal = self._extract_temporal(data)

        if spatial:
            logger.info("STAC spatial extent: %s", spatial["bbox"])
        else:
            logger.info("STAC: no spatial extent found")

        if temporal:
            logger.info("STAC temporal extent: %s to %s", temporal[0], temporal[1])
        else:
            logger.info("STAC: no temporal extent found")

        # Create GeoJSON file
        self._create_geojson(data, spatial, temporal, download_dir)

        return download_dir
