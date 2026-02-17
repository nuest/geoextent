"""
Wikidata content provider for geoextent.

Extracts geographic bounding boxes from Wikidata items using the SPARQL endpoint.

Supported identifiers:
- Q-numbers: Q64, Q35, Q60786916
- Wikidata URLs: https://www.wikidata.org/wiki/Q64
- Wikidata entity URIs: http://www.wikidata.org/entity/Q64

Coordinate extraction priority:
1. Extreme coordinates (P1332-P1335): northernmost, southernmost, easternmost, westernmost
2. Coordinate location (P625): single or multiple point locations (fallback)

When only P625 points are available, the bounding box is computed from all available points.
"""

import json
import logging
import os
import re
from urllib.parse import quote

import requests

from geoextent.lib.content_providers.providers import ContentProvider

logger = logging.getLogger("geoextent")

# Wikidata Q-number pattern: Q followed by digits
_Q_NUMBER_RE = re.compile(r"^Q(\d+)$", re.IGNORECASE)

# Wikidata URL patterns
_WIKIDATA_URL_RE = re.compile(
    r"^https?://(?:www\.)?wikidata\.org/(?:wiki|entity)/Q(\d+)$", re.IGNORECASE
)

# SPARQL endpoint
_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# User-Agent for Wikidata API requests (required by Wikidata)
_USER_AGENT = "nuest/geoextent (https://github.com/nuest/geoextent)"

# SPARQL query template for extracting coordinates from a single item
_SPARQL_QUERY = """
SELECT ?itemLabel ?northLat ?southLat ?eastLon ?westLon ?coord WHERE {{
  OPTIONAL {{ wd:{qid} wdt:P1332 ?north . BIND(geof:latitude(?north) AS ?northLat) }}
  OPTIONAL {{ wd:{qid} wdt:P1333 ?south . BIND(geof:latitude(?south) AS ?southLat) }}
  OPTIONAL {{ wd:{qid} wdt:P1334 ?east . BIND(geof:longitude(?east) AS ?eastLon) }}
  OPTIONAL {{ wd:{qid} wdt:P1335 ?west . BIND(geof:longitude(?west) AS ?westLon) }}
  OPTIONAL {{ wd:{qid} wdt:P625 ?coord }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
}}
""".strip()


class Wikidata(ContentProvider):
    """Content provider for Wikidata geographic entities."""

    @classmethod
    def provider_info(cls):
        return {
            "name": "Wikidata",
            "description": "Wikidata is a free and open knowledge base that provides structured data to Wikipedia and other Wikimedia projects. Geographic extents are extracted via SPARQL queries for coordinate location (P625) and other geographic properties.",
            "website": "https://www.wikidata.org/",
            "supported_identifiers": [
                "https://www.wikidata.org/wiki/{qid}",
                "{qid}",
            ],
            "examples": [
                "Q64",
                "Q1731",
                "https://www.wikidata.org/wiki/Q64",
            ],
            "notes": "Accepts Wikidata Q-identifiers (e.g. Q64 for Berlin). Extracts coordinates via SPARQL. Supports metadata-only extraction.",
        }

    @property
    def supports_metadata_extraction(self):
        return True

    def __init__(self):
        super().__init__()
        self.name = "Wikidata"
        self.qid = None  # e.g. "Q64"
        self.reference = None
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": _USER_AGENT})

    def validate_provider(self, reference):
        """Check if the reference is a Wikidata Q-number or URL.

        Args:
            reference (str): Identifier to validate

        Returns:
            bool: True if this is a Wikidata identifier
        """
        self.reference = reference

        # Try Q-number (e.g. "Q64")
        m = _Q_NUMBER_RE.match(reference)
        if m:
            self.qid = f"Q{m.group(1)}"
            return True

        # Try Wikidata URL (e.g. "https://www.wikidata.org/wiki/Q64")
        m = _WIKIDATA_URL_RE.match(reference)
        if m:
            self.qid = f"Q{m.group(1)}"
            return True

        return False

    def _query_sparql(self, qid):
        """Query Wikidata SPARQL endpoint for coordinates of a single item.

        Args:
            qid (str): Wikidata Q-number (e.g. "Q64")

        Returns:
            dict: Parsed JSON response from SPARQL endpoint
        """
        query = _SPARQL_QUERY.format(qid=qid)
        logger.debug(f"SPARQL query for {qid}: {query}")

        response = self.session.get(
            _SPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _extract_coordinates(self, sparql_result):
        """Extract bbox from SPARQL result.

        Tries extreme coordinates (P1332-P1335) first, falls back to P625 points.

        Args:
            sparql_result (dict): Parsed SPARQL JSON response

        Returns:
            dict or None: {"bbox": [minlon, minlat, maxlon, maxlat], "label": str}
                         in internal lon/lat order, or None if no coordinates found
        """
        bindings = sparql_result.get("results", {}).get("bindings", [])
        if not bindings:
            return None

        label = None
        north = south = east = west = None
        points = []

        for binding in bindings:
            # Extract label
            if "itemLabel" in binding and not label:
                label = binding["itemLabel"]["value"]

            # Extract extreme coordinates
            if "northLat" in binding:
                north = float(binding["northLat"]["value"])
            if "southLat" in binding:
                south = float(binding["southLat"]["value"])
            if "eastLon" in binding:
                east = float(binding["eastLon"]["value"])
            if "westLon" in binding:
                west = float(binding["westLon"]["value"])

            # Extract P625 point coordinates (WKT format: "Point(lon lat)")
            if "coord" in binding:
                wkt = binding["coord"]["value"]
                point = self._parse_wkt_point(wkt)
                if point and point not in points:
                    points.append(point)

        # Strategy 1: Use extreme coordinates if all four are available
        if all(v is not None for v in [north, south, east, west]):
            logger.debug(
                f"Using extreme coordinates for bbox: N={north}, S={south}, E={east}, W={west}"
            )
            return {
                "bbox": [west, south, east, north],  # [minlon, minlat, maxlon, maxlat]
                "label": label,
            }

        # Strategy 2: Use partial extreme coordinates combined with P625 points
        if any(v is not None for v in [north, south, east, west]) and points:
            all_lats = [p[1] for p in points]
            all_lons = [p[0] for p in points]
            if north is not None:
                all_lats.append(north)
            if south is not None:
                all_lats.append(south)
            if east is not None:
                all_lons.append(east)
            if west is not None:
                all_lons.append(west)

            bbox = [min(all_lons), min(all_lats), max(all_lons), max(all_lats)]
            logger.debug(
                f"Using partial extreme coordinates + P625 points for bbox: {bbox}"
            )
            return {"bbox": bbox, "label": label}

        # Strategy 3: Use P625 points only
        if points:
            if len(points) == 1:
                # Single point: create a point geometry (bbox with zero extent)
                lon, lat = points[0]
                logger.debug(f"Using single P625 point: ({lon}, {lat})")
                return {
                    "bbox": [lon, lat, lon, lat],
                    "label": label,
                }
            else:
                # Multiple points: create bbox from extent of all points
                lons = [p[0] for p in points]
                lats = [p[1] for p in points]
                bbox = [min(lons), min(lats), max(lons), max(lats)]
                logger.debug(f"Using {len(points)} P625 points for bbox: {bbox}")
                return {"bbox": bbox, "label": label}

        logger.warning(f"No coordinates found for {self.qid}")
        return None

    @staticmethod
    def _parse_wkt_point(wkt):
        """Parse a WKT Point literal from Wikidata.

        Args:
            wkt (str): WKT string like "Point(13.383333 52.516667)"

        Returns:
            tuple or None: (longitude, latitude) or None if parsing fails
        """
        m = re.match(r"Point\(([+-]?[\d.]+)\s+([+-]?[\d.]+)\)", wkt, re.IGNORECASE)
        if m:
            return (float(m.group(1)), float(m.group(2)))
        return None

    def _create_geojson(self, coords, qid, folder):
        """Create a GeoJSON file from extracted coordinates.

        Args:
            coords (dict): {"bbox": [minlon, minlat, maxlon, maxlat], "label": str}
            qid (str): Wikidata Q-number
            folder (str): Target directory

        Returns:
            str: Path to created GeoJSON file
        """
        bbox = coords["bbox"]
        label = coords.get("label") or qid
        minlon, minlat, maxlon, maxlat = bbox

        # Determine geometry type based on bbox
        if minlon == maxlon and minlat == maxlat:
            # Point geometry
            geometry = {
                "type": "Point",
                "coordinates": [minlon, minlat],
            }
        else:
            # Polygon geometry (bounding box)
            geometry = {
                "type": "Polygon",
                "coordinates": [
                    [
                        [minlon, minlat],
                        [maxlon, minlat],
                        [maxlon, maxlat],
                        [minlon, maxlat],
                        [minlon, minlat],
                    ]
                ],
            }

        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "source": "Wikidata",
                        "qid": qid,
                        "label": label,
                        "url": f"https://www.wikidata.org/wiki/{qid}",
                    },
                }
            ],
        }

        filepath = os.path.join(folder, f"wikidata_{qid}.geojson")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)

        logger.debug(f"Created GeoJSON file: {filepath}")
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
        """Query Wikidata SPARQL and create GeoJSON from coordinates.

        Wikidata is metadata-only: the download_data parameter is accepted
        but ignored since there are no files to download.

        Args:
            folder (str): Target directory for GeoJSON output
            (other parameters accepted for API compatibility but not used)

        Returns:
            str: Path to output directory containing GeoJSON file(s)
        """
        logger.info(f"Extracting coordinates from Wikidata: {self.qid}")

        download_dir = os.path.join(folder, f"wikidata_{self.qid}")
        os.makedirs(download_dir, exist_ok=True)

        try:
            result = self._query_sparql(self.qid)
            coords = self._extract_coordinates(result)

            if coords is None:
                logger.warning(
                    f"No geographic coordinates found for Wikidata item {self.qid}"
                )
                return download_dir

            self._create_geojson(coords, self.qid, download_dir)
            return download_dir

        except requests.RequestException as e:
            logger.error(f"Error querying Wikidata SPARQL endpoint: {e}")
            raise
