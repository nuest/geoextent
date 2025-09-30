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
            logger.warning(f"GeoNames geocoding failed for ({lat}, {lon}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error in GeoNames geocoding: {e}")
        return None


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
            logger.warning(f"Nominatim geocoding failed for ({lat}, {lon}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Nominatim geocoding: {e}")
        return None


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
            logger.warning(f"Photon geocoding failed for ({lat}, {lon}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Photon geocoding: {e}")
        return None


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

        # Convert [lon, lat] to (lat, lon) for geocoding
        sample_points = [(coord[1], coord[0]) for coord in coordinates]

        # Add center point
        if len(coordinates) > 2:
            center_lon = sum(coord[0] for coord in coordinates) / len(coordinates)
            center_lat = sum(coord[1] for coord in coordinates) / len(coordinates)
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
        logger.warning("No geometry provided for placename extraction")
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
        logger.error(f"Error extracting placename: {e}")
        return None
