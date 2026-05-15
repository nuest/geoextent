"""
Gazetteer services module for placename lookup using geopy.

This module provides interfaces to various gazetteer services for
converting geographic coordinates to place names.
"""

import logging
import os
from typing import Optional, Tuple, Dict, Any, List
from geopy.geocoders import GeoNames, Nominatim, Photon
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from dotenv import load_dotenv

logger = logging.getLogger("geoextent")

# Load environment variables from .env file
load_dotenv()


class GazetteerService:
    """Base class for gazetteer services."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.geocoder = None

    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """
        Reverse geocode coordinates to placename.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Place name string or None if not found
        """
        raise NotImplementedError("Subclasses must implement reverse_geocode")

    def geocode(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Forward-geocode a place name to one or more candidate hits.

        Subclasses should return a list of dicts with keys:
        ``name``, ``lat``, ``lon``, ``id`` (gazetteer-prefixed identifier),
        and ``url`` (canonical URL for the hit). Empty list if no match.
        """
        raise NotImplementedError("Subclasses must implement geocode")

    def find_shared_components(self, names: List[str]) -> Optional[str]:
        """
        Find shared components among placenames and return them as a placename.

        Args:
            names: List of placename strings

        Returns:
            Placename composed of shared components or fallback name
        """
        if not names:
            return None

        # Filter out None values
        valid_names = [name for name in names if name is not None]
        if not valid_names:
            return None

        # If only one name, return it
        if len(valid_names) == 1:
            return valid_names[0]

        import re
        from collections import Counter

        # Split each name into components (words/phrases separated by common delimiters)
        all_components = []

        for name in names:
            # Split by common separators in addresses: comma, semicolon, slash, etc.
            components = re.split(r"[,;/\|]", name)
            # Further split by multiple spaces and clean up
            components = [comp.strip() for comp in components if comp.strip()]
            # Remove duplicates within the same name to avoid inflating frequency
            unique_components = list(set(components))
            all_components.extend(unique_components)

        # Count frequency of each component across all names
        component_freq = Counter(all_components)

        # Find components that appear in multiple names (shared components)
        shared_components = [
            comp
            for comp, freq in component_freq.items()
            if freq > 1 and len(comp.strip()) > 0
        ]

        if not shared_components:
            # No shared components, fall back to shortest name (most concise)
            return min(names, key=len)

        # Return shared components as a comma-separated placename
        # Retain original ordering from gazetteer service
        return ", ".join(shared_components)


class GeoNamesService(GazetteerService):
    """GeoNames gazetteer service."""

    def __init__(self):
        super().__init__("geonames")
        username = os.getenv("GEONAMES_USERNAME")
        if not username:
            raise ValueError(
                "GEONAMES_USERNAME environment variable required for GeoNames service. "
                "Please set it in your .env file or environment."
            )
        self.geocoder = GeoNames(username=username)

    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """Reverse geocode using GeoNames service."""
        try:
            location = self.geocoder.reverse((lat, lon), timeout=10)
            if location:
                return location.address
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(
                "GeoNames reverse-geocoding via api.geonames.org failed for "
                "(%s, %s): %s",
                lat,
                lon,
                e,
            )
        except Exception as e:
            logger.error(
                "Unexpected error in GeoNames reverse-geocoding via "
                "api.geonames.org for (%s, %s): %s",
                lat,
                lon,
                e,
            )
        return None

    def geocode(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            results = self.geocoder.geocode(query, exactly_one=False, timeout=10)
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(
                "GeoNames forward geocoding via api.geonames.org failed " "for %r: %s",
                query,
                e,
            )
            return []
        except Exception as e:
            logger.error(
                "Unexpected error in GeoNames forward geocoding via "
                "api.geonames.org for %r: %s",
                query,
                e,
            )
            return []
        if not results:
            return []
        hits = []
        for loc in results[:limit]:
            raw = getattr(loc, "raw", {}) or {}
            geoname_id = raw.get("geonameId")
            ident = (
                f"geonames:{geoname_id}" if geoname_id else f"geonames:{loc.address}"
            )
            url = f"https://www.geonames.org/{geoname_id}" if geoname_id else None
            hits.append(
                {
                    "name": loc.address,
                    "lat": float(loc.latitude),
                    "lon": float(loc.longitude),
                    "id": ident,
                    "url": url,
                    # GeoNames does not supply boundary geometry; downstream
                    # code falls back to the point.
                    "boundary": None,
                }
            )
        return hits


class NominatimService(GazetteerService):
    """Nominatim gazetteer service."""

    def __init__(self):
        super().__init__("nominatim")
        # Use a proper user agent for Nominatim
        user_agent = os.getenv("NOMINATIM_USER_AGENT", "geoextent/1.0")
        self.geocoder = Nominatim(user_agent=user_agent)

    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """Reverse geocode using Nominatim service."""
        try:
            location = self.geocoder.reverse((lat, lon), timeout=10)
            if location:
                return location.address
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(
                "Nominatim reverse-geocoding via nominatim.openstreetmap.org "
                "failed for (%s, %s): %s",
                lat,
                lon,
                e,
            )
        except Exception as e:
            logger.error(
                "Unexpected error in Nominatim reverse-geocoding via "
                "nominatim.openstreetmap.org for (%s, %s): %s",
                lat,
                lon,
                e,
            )
        return None

    def geocode(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        # Request the boundary geometry as GeoJSON for hits that have one
        # (administrative areas, parks, lakes, etc.). Nominatim returns a
        # Point or Polygon/MultiPolygon under the ``geojson`` key on each
        # raw record; geopy passes through via ``geometry="geojson"``.
        try:
            results = self.geocoder.geocode(
                query,
                exactly_one=False,
                timeout=10,
                limit=limit,
                geometry="geojson",
            )
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(
                "Nominatim forward geocoding via nominatim.openstreetmap.org "
                "failed for %r: %s",
                query,
                e,
            )
            return []
        except Exception as e:
            logger.error(
                "Unexpected error in Nominatim forward geocoding via "
                "nominatim.openstreetmap.org for %r: %s",
                query,
                e,
            )
            return []
        if not results:
            return []
        hits = []
        for loc in results[:limit]:
            raw = getattr(loc, "raw", {}) or {}
            osm_type = raw.get("osm_type")
            osm_id = raw.get("osm_id")
            if osm_type and osm_id:
                ident = f"osm:{osm_type}:{osm_id}"
                url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
            else:
                ident = f"nominatim:{raw.get('place_id', loc.address)}"
                url = None
            geojson_geom = raw.get("geojson")
            # Nominatim returns Point even for areal features unless we ask
            # for the area geometry; only carry the geometry forward when
            # it is genuinely areal (Polygon / MultiPolygon / LineString),
            # not a redundant centroid Point that adds noise.
            boundary = None
            if isinstance(geojson_geom, dict) and geojson_geom.get("type") in (
                "Polygon",
                "MultiPolygon",
                "LineString",
                "MultiLineString",
            ):
                boundary = geojson_geom
            hits.append(
                {
                    "name": loc.address,
                    "lat": float(loc.latitude),
                    "lon": float(loc.longitude),
                    "id": ident,
                    "url": url,
                    "boundary": boundary,
                }
            )
        return hits


class PhotonService(GazetteerService):
    """Photon gazetteer service."""

    def __init__(self):
        super().__init__("photon")
        # Use custom endpoint if specified, otherwise use default
        domain = os.getenv("PHOTON_DOMAIN", "photon.komoot.io")
        self.geocoder = Photon(domain=domain)

    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """Reverse geocode using Photon service."""
        try:
            location = self.geocoder.reverse((lat, lon), timeout=10)
            if location:
                return location.address
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(
                "Photon reverse-geocoding via %s failed for (%s, %s): %s",
                self.geocoder.domain,
                lat,
                lon,
                e,
            )
        except Exception as e:
            logger.error(
                "Unexpected error in Photon reverse-geocoding via %s for "
                "(%s, %s): %s",
                self.geocoder.domain,
                lat,
                lon,
                e,
            )
        return None

    def geocode(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            results = self.geocoder.geocode(
                query, exactly_one=False, timeout=10, limit=limit
            )
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(
                "Photon forward geocoding via %s failed for %r: %s",
                self.geocoder.domain,
                query,
                e,
            )
            return []
        except Exception as e:
            logger.error(
                "Unexpected error in Photon forward geocoding via %s for " "%r: %s",
                self.geocoder.domain,
                query,
                e,
            )
            return []
        if not results:
            return []
        hits = []
        for loc in results[:limit]:
            raw = getattr(loc, "raw", {}) or {}
            props = raw.get("properties", {}) if isinstance(raw, dict) else {}
            osm_type = props.get("osm_type")
            osm_id = props.get("osm_id")
            if osm_type and osm_id:
                # Photon returns one-letter osm_type (N/W/R); map to full names
                osm_type_long = {
                    "N": "node",
                    "W": "way",
                    "R": "relation",
                }.get(osm_type, osm_type)
                ident = f"osm:{osm_type_long}:{osm_id}"
                url = f"https://www.openstreetmap.org/{osm_type_long}/{osm_id}"
            else:
                ident = f"photon:{loc.address}"
                url = None
            hits.append(
                {
                    "name": loc.address,
                    "lat": float(loc.latitude),
                    "lon": float(loc.longitude),
                    "id": ident,
                    "url": url,
                    # Photon returns geometry only as a point; downstream
                    # code falls back to lat/lon.
                    "boundary": None,
                }
            )
        return hits


class PlacenameExtractor:
    """Main class for extracting placenames from geometries."""

    SUPPORTED_SERVICES = {
        "geonames": GeoNamesService,
        "nominatim": NominatimService,
        "photon": PhotonService,
    }

    def __init__(self, service_name: str = "geonames"):
        """
        Initialize placename extractor.

        Args:
            service_name: Name of gazetteer service to use
        """
        if service_name not in self.SUPPORTED_SERVICES:
            raise ValueError(
                f"Unsupported gazetteer service: {service_name}. "
                f"Supported services: {list(self.SUPPORTED_SERVICES.keys())}"
            )

        try:
            service_class = self.SUPPORTED_SERVICES[service_name]
            self.service = service_class()
            logger.info(f"Initialized {service_name} gazetteer service")
        except Exception as e:
            logger.error(f"Failed to initialize {service_name} service: {e}")
            raise

    def extract_placename_from_bbox(self, bbox: List[float]) -> Optional[str]:
        """
        Extract placename from bounding box coordinates.

        Args:
            bbox: Bounding box as [min_lon, min_lat, max_lon, max_lat]

        Returns:
            Most relevant placename or None
        """
        if not bbox or len(bbox) != 4:
            logger.warning("Invalid bounding box format for placename extraction")
            return None

        min_lon, min_lat, max_lon, max_lat = bbox

        # Generate sample points from the bounding box
        sample_points = [
            (min_lat, min_lon),  # Southwest corner
            (max_lat, max_lon),  # Northeast corner
            ((min_lat + max_lat) / 2, (min_lon + max_lon) / 2),  # Center point
            (min_lat, max_lon),  # Southeast corner
            (max_lat, min_lon),  # Northwest corner
        ]

        return self._extract_from_points(sample_points)

    def extract_placename_from_convex_hull(
        self, coordinates: List[List[float]]
    ) -> Optional[str]:
        """
        Extract placename from convex hull coordinates.

        Args:
            coordinates: List of [lon, lat] coordinate pairs

        Returns:
            Most relevant placename or None
        """
        if not coordinates:
            logger.warning("Empty coordinates for placename extraction")
            return None

        # For closed polygons, remove the duplicate last point (same as first)
        coords_to_use = coordinates
        if len(coordinates) > 1 and coordinates[0] == coordinates[-1]:
            coords_to_use = coordinates[:-1]
            logger.debug(
                f"Removed duplicate closing point from polygon ({len(coordinates)} -> {len(coords_to_use)} points)"
            )

        # Convert [lon, lat] to (lat, lon) for geocoding
        sample_points = [(coord[1], coord[0]) for coord in coords_to_use]

        # Add center point
        if len(coords_to_use) > 2:
            center_lon = sum(coord[0] for coord in coords_to_use) / len(coords_to_use)
            center_lat = sum(coord[1] for coord in coords_to_use) / len(coords_to_use)
            sample_points.append((center_lat, center_lon))

        return self._extract_from_points(sample_points)

    def _extract_from_points(self, points: List[Tuple[float, float]]) -> Optional[str]:
        """
        Extract placename from a list of coordinate points.

        Args:
            points: List of (lat, lon) tuples

        Returns:
            Most detailed placename found
        """
        from tqdm import tqdm

        placenames = []

        # Limit points to avoid excessive API calls
        max_points = min(len(points), 5)  # Process up to 5 points

        # Show progress bar for gazetteer queries when processing multiple points
        with tqdm(
            total=max_points,
            desc=f"Querying {self.service.service_name}",
            unit="point",
            leave=False,
        ) as pbar:

            for i, (lat, lon) in enumerate(points[:max_points]):
                # Validate coordinates
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    logger.warning(f"Invalid coordinates: ({lat}, {lon})")
                    pbar.update(1)
                    continue

                placename = self.service.reverse_geocode(lat, lon)
                if placename:
                    placenames.append(placename)
                    logger.debug(f"Found placename for ({lat}, {lon}): {placename}")
                    pbar.set_postfix_str(f"Found: {len(placenames)} names")

                pbar.update(1)

                # Stop early if we have enough good results
                if len(placenames) >= 3:
                    break

        return self.service.find_shared_components(placenames)


def get_placename_for_geometry(
    bbox: Optional[List[float]] = None,
    convex_hull_coords: Optional[List[List[float]]] = None,
    service_name: str = "geonames",
    escape_unicode: bool = False,
) -> Optional[str]:
    """
    Convenience function to extract placename from geometry.

    Args:
        bbox: Bounding box coordinates [min_lon, min_lat, max_lon, max_lat]
        convex_hull_coords: Convex hull coordinates as list of [lon, lat] pairs
        service_name: Gazetteer service to use
        escape_unicode: Whether to escape Unicode characters in the result

    Returns:
        Placename string or None
    """
    if not bbox and not convex_hull_coords:
        logger.warning(
            "No geometry provided for placename extraction via %s "
            "(both bbox and convex_hull_coords are empty)",
            service_name,
        )
        return None

    try:
        extractor = PlacenameExtractor(service_name)

        placename = None
        if convex_hull_coords:
            placename = extractor.extract_placename_from_convex_hull(convex_hull_coords)
        elif bbox:
            placename = extractor.extract_placename_from_bbox(bbox)

        # Apply Unicode escaping if requested
        if placename and escape_unicode:
            placename = placename.encode("unicode_escape").decode("ascii")

        return placename

    except Exception as e:
        logger.error(
            "Error extracting placename via %s reverse-geocoding: %s",
            service_name,
            e,
        )
        return None


_SERVICE_CLASSES = {
    "geonames": GeoNamesService,
    "nominatim": NominatimService,
    "photon": PhotonService,
}

# Track which (service, name) pairs we have already warned about so a long
# directory with the same ambiguous mention in many files doesn't flood the
# log. Keyed by (service, name.lower()). Bounded by the natural number of
# unique mentions per run.
_AMBIGUITY_WARNED = set()


def _reset_ambiguity_warnings():
    """Clear the warned-about set; intended for tests."""
    _AMBIGUITY_WARNED.clear()


def get_gazetteer_service(service_name: str) -> GazetteerService:
    """Instantiate a gazetteer service by name."""
    if service_name not in _SERVICE_CLASSES:
        raise ValueError(
            f"Unsupported gazetteer service: {service_name}. "
            f"Supported: {list(_SERVICE_CLASSES.keys())}"
        )
    return _SERVICE_CLASSES[service_name]()


def forward_geocode_names(
    names: List[str],
    service_name: str = "geonames",
    ambiguity: str = "drop",
    cache: Optional[Dict[Tuple[str, str], List[Dict[str, Any]]]] = None,
    limit: int = 5,
) -> List[Tuple[str, Optional[Dict[str, Any]], List[Dict[str, Any]]]]:
    """Forward-geocode a list of place names.

    Args:
        names: place name strings to resolve.
        service_name: gazetteer service identifier.
        ambiguity: ``"drop"`` to skip mentions with more than one hit,
            ``"top"`` to keep the highest-ranked hit when multiple are returned.
        cache: optional dict for in-memory caching of (service, query) -> hits.
        limit: max number of hits to request per query.

    Returns:
        List of ``(name, chosen_hit, all_hits)`` tuples, in input order.
        ``chosen_hit`` is None when no hit was found or when an ambiguous
        result was dropped.
    """
    if ambiguity not in ("drop", "top"):
        raise ValueError(f"Invalid ambiguity mode: {ambiguity!r} (use 'drop' or 'top')")

    service = get_gazetteer_service(service_name)
    if cache is None:
        cache = {}

    out: List[Tuple[str, Optional[Dict[str, Any]], List[Dict[str, Any]]]] = []
    for raw_name in names:
        name = (raw_name or "").strip()
        if not name:
            continue
        key = (service_name, name.lower())
        if key in cache:
            hits = cache[key]
        else:
            hits = service.geocode(name, limit=limit)
            cache[key] = hits

        if not hits:
            out.append((name, None, hits))
            continue
        if ambiguity == "drop" and len(hits) > 1:
            warn_key = (service_name, name.lower())
            if warn_key not in _AMBIGUITY_WARNED:
                _AMBIGUITY_WARNED.add(warn_key)
                # Candidate names from administrative gazetteers contain
                # commas (e.g. "Paris, Île-de-France, France"); join with
                # "; " so the boundary between candidates stays readable.
                logger.warning(
                    "Dropped ambiguous place name %r — %s returned %d candidates "
                    "(e.g. %s). To keep the highest-ranked match instead, use "
                    "--ner-ambiguity top (CLI) or ner_ambiguity='top' (API).",
                    name,
                    service_name,
                    len(hits),
                    "; ".join(h["name"][:60] for h in hits[:3]),
                )
            else:
                logger.debug(
                    "Dropping ambiguous mention %r (%d hits, already warned)",
                    name,
                    len(hits),
                )
            out.append((name, None, hits))
            continue
        out.append((name, hits[0], hits))
    return out
