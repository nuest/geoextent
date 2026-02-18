"""
Feature listing for geoextent.

This module provides machine-readable information about supported file formats
and content providers by dynamically inspecting the existing handler and provider classes.
"""

import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger("geoextent")


def get_supported_features() -> Dict[str, Any]:
    """
    Get a comprehensive list of all supported features in geoextent.

    Returns information about:
    - File formats/handlers with their capabilities
    - Content providers with their URL patterns and supported identifiers

    All information is extracted dynamically from existing class properties
    and patterns, not hardcoded.

    Returns:
        dict: A structured dictionary containing all supported features
    """

    features = {
        "version": _get_geoextent_version(),
        "file_formats": _get_file_format_info(),
        "content_providers": _get_content_provider_info(),
    }

    return features


def get_supported_features_json(indent: int = 2) -> str:
    """
    Get supported features as a JSON string.

    Args:
        indent: Number of spaces for JSON indentation (default: 2)

    Returns:
        str: JSON string containing all supported features
    """
    features = get_supported_features()
    return json.dumps(features, indent=indent)


def _get_geoextent_version() -> str:
    """Get the geoextent version."""
    try:
        from .. import __version__

        return __version__
    except (ImportError, AttributeError):
        return "unknown"


def _get_file_format_info() -> List[Dict[str, Any]]:
    """
    Extract file format information from handler modules.

    Returns information about each handler including:
    - Handler name
    - Capabilities (bbox, temporal extent, convex hull)
    - Example file extensions (derived from GDAL driver support)
    """
    from . import handleCSV, handleRaster, handleVector

    handlers = []

    # CSV Handler
    csv_info = {
        "handler": handleCSV.get_handler_name(),
        "display_name": handleCSV.get_handler_display_name(),
        "description": "CSV files with coordinate or geometry columns",
        "capabilities": {
            "bounding_box": True,
            "temporal_extent": True,
            "convex_hull": hasattr(handleCSV, "getConvexHull"),
        },
        "supported_patterns": {
            "longitude_columns": handleCSV.search.get("longitude", []),
            "latitude_columns": handleCSV.search.get("latitude", []),
            "geometry_columns": handleCSV.search.get("geometry", []),
            "time_columns": handleCSV.search.get("time", []),
        },
        "file_extensions": [".csv", ".txt"],
        "notes": "Automatically detects coordinate columns using pattern matching. Uses GDAL CSV driver with open options for column detection.",
    }
    handlers.append(csv_info)

    # Vector Handler
    vector_info = {
        "handler": handleVector.get_handler_name(),
        "display_name": handleVector.get_handler_display_name(),
        "description": "Vector geospatial formats (Shapefile, GeoJSON, GeoPackage, Esri File Geodatabase, etc.)",
        "capabilities": {
            "bounding_box": True,
            "temporal_extent": True,
            "convex_hull": hasattr(handleVector, "getConvexHull"),
        },
        "supported_patterns": {"time_columns": handleVector.search.get("time", [])},
        "file_extensions": [
            ".shp",
            ".shx",
            ".dbf",
            ".prj",  # Shapefile
            ".geojson",
            ".json",  # GeoJSON
            ".gpkg",  # GeoPackage
            ".gdb",  # Esri File Geodatabase
            ".gpx",  # GPX
            ".kml",
            ".kmz",  # KML
            ".gml",  # GML
            ".fgb",  # FlatGeobuf
        ],
        "notes": "Uses GDAL/OGR for vector format support. Esri File Geodatabase (.gdb) via OpenFileGDB driver.",
    }
    handlers.append(vector_info)

    # Raster Handler
    raster_info = {
        "handler": handleRaster.get_handler_name(),
        "display_name": handleRaster.get_handler_display_name(),
        "description": "Raster geospatial formats (GeoTIFF, NetCDF, world files, etc.)",
        "capabilities": {
            "bounding_box": True,
            "temporal_extent": True,
            "convex_hull": False,
        },
        "file_extensions": [
            ".tif",
            ".tiff",
            ".geotiff",  # GeoTIFF
            ".nc",
            ".netcdf",  # NetCDF
            ".asc",  # ASCII Grid
            ".wld",
            ".jgw",
            ".pgw",
            ".pngw",
            ".tfw",
            ".tifw",
            ".bpw",
            ".gfw",  # World files
        ],
        "notes": "Uses GDAL for raster format support. Temporal extraction from NetCDF CF time dimensions, ACDD time_coverage attributes, GeoTIFF TIFFTAG_DATETIME, and band-level ACQUISITIONDATETIME. World file support for images without embedded georeferencing.",
    }
    handlers.append(raster_info)

    return handlers


def _get_content_provider_info() -> List[Dict[str, Any]]:
    """
    Extract content provider information from provider classes.

    Each provider class defines a ``provider_info()`` classmethod that returns
    its metadata (name, description, website, supported identifiers, examples).
    This function collects those dicts, augments them with runtime ``host``
    data (url_patterns, api_endpoint), and returns the list in the same order
    as ``_get_content_providers()``.
    """
    from .extent import _get_content_providers

    providers = []
    seen = set()  # Avoid duplicates (Zenodo is also an InvenioRDM subclass)

    for provider_class in _get_content_providers():
        info = provider_class.provider_info()
        if info is None:
            continue
        class_name = provider_class.__name__
        if class_name in seen:
            continue
        seen.add(class_name)

        # Augment with runtime host attributes
        instance = provider_class()
        if hasattr(instance, "host") and isinstance(instance.host, dict):
            info.setdefault("url_patterns", instance.host.get("hostname", []))
            info.setdefault("api_endpoint", instance.host.get("api", ""))
        if hasattr(instance, "csw_base_url"):
            info.setdefault("api_endpoint", instance.csw_base_url)
        if hasattr(instance, "known_hosts"):
            info.setdefault("known_hosts", instance.known_hosts)

        providers.append(info)

    return providers


def validate_remote_identifier(identifier: str) -> Dict[str, Any]:
    """
    Validate a remote identifier and determine which provider supports it.

    Delegates to ``find_provider()`` using the canonical provider list from
    ``_get_content_providers()``, eliminating the need for a duplicate
    hardcoded provider list.

    Args:
        identifier: URL, DOI, or other identifier to validate

    Returns:
        dict: Validation result with keys:
            - valid: bool, whether the identifier is supported
            - provider: str or None, name of the supporting provider
            - message: str, description of the result
    """
    from .extent import _get_content_providers
    from .content_providers.providers import find_provider

    providers = _get_content_providers()
    provider = find_provider(identifier, providers)

    if provider is not None:
        return {
            "valid": True,
            "provider": provider.name,
            "message": f"Identifier is supported by {provider.name}",
        }

    return {
        "valid": False,
        "provider": None,
        "message": "Identifier not recognized by any content provider",
    }


def validate_file_format(filepath: str) -> Dict[str, Any]:
    """
    Validate a file format and determine which handler supports it.

    This function can be used by external tools to validate file formats before
    calling geoextent.

    Args:
        filepath: Path to the file to validate

    Returns:
        dict: Validation result with keys:
            - valid: bool, whether the file format is supported
            - handler: str or None, name of the supporting handler
            - message: str, description of the result
    """
    from . import handleCSV, handleRaster, handleVector

    handlers = [("CSV", handleCSV), ("Vector", handleVector), ("Raster", handleRaster)]

    for handler_name, handler_module in handlers:
        try:
            if handler_module.checkFileSupported(filepath):
                return {
                    "valid": True,
                    "handler": handler_module.get_handler_name(),
                    "message": f"File format is supported by {handler_name} handler",
                }
        except Exception as e:
            # Continue to next handler if validation fails
            logger.debug(f"Handler {handler_name} validation failed: {e}")
            continue

    return {
        "valid": False,
        "handler": None,
        "message": "File format is not supported by any known handler",
    }
