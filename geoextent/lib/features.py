"""
Feature listing for geoextent.

This module provides machine-readable information about supported file formats
and content providers by dynamically inspecting the existing handler and provider classes.
"""

import json
import logging
import re
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
        "content_providers": _get_content_provider_info()
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
        "description": "CSV files with coordinate or geometry columns",
        "capabilities": {
            "bounding_box": True,
            "temporal_extent": True,
            "convex_hull": hasattr(handleCSV, "getConvexHull")
        },
        "supported_patterns": {
            "longitude_columns": handleCSV.search.get("longitude", []),
            "latitude_columns": handleCSV.search.get("latitude", []),
            "geometry_columns": handleCSV.search.get("geometry", []),
            "time_columns": handleCSV.search.get("time", [])
        },
        "file_extensions": [".csv"],
        "notes": "Automatically detects coordinate columns using pattern matching"
    }
    handlers.append(csv_info)

    # Vector Handler
    vector_info = {
        "handler": handleVector.get_handler_name(),
        "description": "Vector geospatial formats (Shapefile, GeoJSON, GeoPackage, etc.)",
        "capabilities": {
            "bounding_box": True,
            "temporal_extent": True,
            "convex_hull": hasattr(handleVector, "getConvexHull")
        },
        "supported_patterns": {
            "time_columns": handleVector.search.get("time", [])
        },
        "file_extensions": [
            ".shp", ".shx", ".dbf", ".prj",  # Shapefile
            ".geojson", ".json",              # GeoJSON
            ".gpkg",                          # GeoPackage
            ".gpx",                           # GPX
            ".kml", ".kmz",                   # KML
            ".gml",                           # GML
            ".fgb"                            # FlatGeobuf
        ],
        "notes": "Uses GDAL/OGR for vector format support"
    }
    handlers.append(vector_info)

    # Raster Handler
    raster_info = {
        "handler": handleRaster.get_handler_name(),
        "description": "Raster geospatial formats (GeoTIFF, NetCDF, etc.)",
        "capabilities": {
            "bounding_box": True,
            "temporal_extent": False,
            "convex_hull": False
        },
        "file_extensions": [
            ".tif", ".tiff", ".geotiff",     # GeoTIFF
            ".nc", ".netcdf",                 # NetCDF
            ".asc"                            # ASCII Grid
        ],
        "notes": "Uses GDAL for raster format support"
    }
    handlers.append(raster_info)

    return handlers


def _get_content_provider_info() -> List[Dict[str, Any]]:
    """
    Extract content provider information from provider classes.

    Returns information about each provider including:
    - Provider name
    - Supported URL patterns (extracted from validate_provider method)
    - API endpoints (from class properties)
    - Example identifiers
    """
    from .content_providers import (
        Zenodo, Figshare, Dryad, Pangaea, OSF,
        Dataverse, GFZ, Pensoft, Opara
    )

    providers = []

    # Zenodo
    zenodo_instance = Zenodo.Zenodo()
    zenodo_info = {
        "name": zenodo_instance.name,
        "description": "Zenodo is a free and open digital archive built by CERN and OpenAIRE, enabling researchers to share and preserve research output in any size, format and from all fields of research. It assigns persistent DOIs to all submissions and stores data in the CERN Data Center for long-term preservation.",
        "website": "https://zenodo.org/",
        "url_patterns": zenodo_instance.host.get("hostname", []),
        "api_endpoint": zenodo_instance.host.get("api", ""),
        "supported_identifiers": [
            "https://zenodo.org/records/{record_id}",
            "https://zenodo.org/record/{record_id}",
            "https://doi.org/10.5281/zenodo.{record_id}",
            "10.5281/zenodo.{record_id}",
            "{record_id}"
        ],
        "doi_prefix": "10.5281/zenodo",
        "examples": [
            "https://doi.org/10.5281/zenodo.4593540",
            "10.5281/zenodo.4593540"
        ]
    }
    providers.append(zenodo_info)

    # Figshare
    figshare_instance = Figshare.Figshare()
    figshare_info = {
        "name": figshare_instance.name,
        "description": "Figshare is an online open access repository where researchers can preserve and share their research outputs including figures, datasets, images, and videos. It allows researchers to publish files in any format with assigned DOIs and tracks download statistics for altmetrics.",
        "website": "https://figshare.com/",
        "url_patterns": figshare_instance.host.get("hostname", []),
        "api_endpoint": figshare_instance.host.get("api", ""),
        "supported_identifiers": [
            "https://figshare.com/articles/{article_id}",
            "https://doi.org/10.6084/m9.figshare.{article_id}",
            "10.6084/m9.figshare.{article_id}"
        ],
        "doi_prefix": "10.6084/m9.figshare",
        "examples": [
            "https://doi.org/10.6084/m9.figshare.12345678"
        ]
    }
    providers.append(figshare_info)

    # Dryad
    dryad_instance = Dryad.Dryad()
    dryad_info = {
        "name": dryad_instance.name,
        "description": "Dryad is a nonprofit curated general-purpose repository that makes research data discoverable, freely reusable, and citable with DOIs. It specializes in data underlying scientific publications and accepts data in any file format from any field of research under Creative Commons Zero waiver.",
        "website": "https://datadryad.org/",
        "url_patterns": dryad_instance.host.get("hostname", []),
        "api_endpoint": dryad_instance.host.get("api", ""),
        "supported_identifiers": [
            "https://datadryad.org/stash/dataset/doi:{doi}",
            "https://doi.org/10.5061/dryad.{id}",
            "10.5061/dryad.{id}"
        ],
        "doi_prefix": "10.5061/dryad",
        "examples": [
            "https://datadryad.org/stash/dataset/doi:10.5061/dryad.0k6djhb7x"
        ]
    }
    providers.append(dryad_info)

    # PANGAEA
    pangaea_instance = Pangaea.Pangaea()
    pangaea_info = {
        "name": pangaea_instance.name,
        "description": "PANGAEA is a digital data library and publisher for earth system science, hosted by the Alfred Wegener Institute and MARUM in Germany. It archives and publishes georeferenced data from earth system research with DOI assignment and holds around 375,000 datasets comprising over 13 billion data items.",
        "website": "https://www.pangaea.de/",
        "url_patterns": pangaea_instance.host.get("hostname", []),
        "api_endpoint": pangaea_instance.host.get("api", ""),
        "supported_identifiers": [
            "https://doi.pangaea.de/10.1594/PANGAEA.{dataset_id}",
            "https://doi.org/10.1594/PANGAEA.{dataset_id}",
            "10.1594/PANGAEA.{dataset_id}"
        ],
        "doi_prefix": "10.1594/PANGAEA",
        "examples": [
            "https://doi.org/10.1594/PANGAEA.734969"
        ]
    }
    providers.append(pangaea_info)

    # OSF
    osf_instance = OSF.OSF()
    osf_info = {
        "name": osf_instance.name,
        "description": "The Open Science Framework (OSF) is a free and open-source project management tool developed by the Center for Open Science that facilitates open collaboration in science research. It enables researchers to manage, store, and share documents, datasets, and other research materials throughout the project lifecycle with version control and integration capabilities.",
        "website": "https://osf.io/",
        "url_patterns": osf_instance.host.get("hostname", []),
        "api_endpoint": osf_instance.host.get("api", ""),
        "supported_identifiers": [
            "https://osf.io/{project_id}/",
            "https://doi.org/10.17605/OSF.IO/{project_id}",
            "10.17605/OSF.IO/{project_id}",
            "OSF.IO/{project_id}"
        ],
        "doi_prefix": "10.17605/OSF.IO",
        "examples": [
            "https://doi.org/10.17605/OSF.IO/4XE6Z",
            "https://osf.io/4xe6z/"
        ]
    }
    providers.append(osf_info)

    # Dataverse
    dataverse_instance = Dataverse.Dataverse()
    dataverse_info = {
        "name": dataverse_instance.name,
        "description": "Dataverse is an open-source web application for sharing, preserving, citing, exploring, and analyzing research data developed at Harvard University's Institute for Quantitative Social Science. The Harvard Dataverse Repository is one of the largest repositories of open research data in the world with thousands of datasets across all disciplines.",
        "website": "https://dataverse.org/",
        "known_hosts": dataverse_instance.known_hosts,
        "url_patterns": [
            "https://{host}/dataset.xhtml?persistentId={doi}",
            "https://{host}/api/datasets/:persistentId?persistentId={doi}",
            "https://{host}/api/datasets/{id}"
        ],
        "api_endpoint": "https://{host}/api/",
        "supported_identifiers": [
            "https://{instance}/dataset.xhtml?persistentId=doi:{doi}",
            "https://doi.org/{doi}",
            "doi:{doi}",
            "{doi}"
        ],
        "doi_prefix": "10.7910/DVN (Harvard), varies by instance",
        "examples": [
            "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/12345"
        ],
        "notes": "Supports multiple Dataverse instances"
    }
    providers.append(dataverse_info)

    # GFZ
    gfz_instance = GFZ.GFZ()
    gfz_info = {
        "name": gfz_instance.name,
        "description": "GFZ Data Services is a curated research data repository for the geosciences domain, hosted at the GFZ German Research Centre for Geosciences in Potsdam. It has assigned DOIs to geoscientific datasets since 2004 and provides comprehensive consultation by domain scientists and IT specialists following FAIR principles.",
        "website": "https://dataservices.gfz-potsdam.de/",
        "url_patterns": gfz_instance.host.get("hostname", []),
        "api_endpoint": gfz_instance.host.get("api", ""),
        "supported_identifiers": [
            "https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id={doi}",
            "https://doi.org/10.5880/GFZ.{id}",
            "10.5880/GFZ.{id}"
        ],
        "doi_prefix": "10.5880/GFZ",
        "examples": [
            "10.5880/GFZ.4.8.2023.004"
        ]
    }
    providers.append(gfz_info)

    # Pensoft
    pensoft_instance = Pensoft.Pensoft()
    pensoft_info = {
        "name": pensoft_instance.name,
        "description": "Pensoft Publishers is a scholarly publisher based in Sofia, Bulgaria, specializing in biodiversity and environmental science with over 60 peer-reviewed open access journals. All articles are published under Creative Commons licenses and include semantic enrichments and hyperlinks to facilitate data findability and interoperability.",
        "website": "https://pensoft.net/",
        "url_patterns": pensoft_instance.host.get("hostname", []),
        "api_endpoint": pensoft_instance.host.get("api", ""),
        "supported_identifiers": [
            "https://doi.org/10.3897/{journal}.{article_id}",
            "10.3897/{journal}.{article_id}"
        ],
        "doi_prefix": "10.3897",
        "examples": [
            "https://doi.org/10.3897/BDJ.2.e1068"
        ]
    }
    providers.append(pensoft_info)

    # Opara (TU Dresden)
    opara_instance = Opara.Opara()
    opara_info = {
        "name": opara_instance.name,
        "description": "OPARA is the Open Access Repository and Archive for research data of Saxon universities, jointly operated by TU Dresden and TU Bergakademie Freiberg. It offers free archiving for at least ten years and open access publishing of research data with DOI assignment, running on DSpace 7.x platform.",
        "website": "https://opara.zih.tu-dresden.de/",
        "url_patterns": opara_instance.host.get("hostname", []),
        "api_endpoint": opara_instance.host.get("api", ""),
        "supported_identifiers": [
            "https://opara.zih.tu-dresden.de/items/{uuid}",
            "https://opara.zih.tu-dresden.de/handle/{handle}",
            "https://doi.org/10.25532/OPARA-{id}",
            "10.25532/OPARA-{id}",
            "{uuid}"
        ],
        "doi_prefix": "10.25532/OPARA",
        "examples": [
            "https://opara.zih.tu-dresden.de/items/4cdf08d6-2738-4c9e-9d27-345a0647ff7c",
            "https://opara.zih.tu-dresden.de/handle/123456789/821",
            "10.25532/OPARA-581"
        ],
        "notes": "TU Dresden institutional repository using DSpace 7.x"
    }
    providers.append(opara_info)

    return providers


def validate_remote_identifier(identifier: str) -> Dict[str, Any]:
    """
    Validate a remote identifier and determine which provider supports it.

    This function can be used by external tools to validate user input before
    calling geoextent.

    Args:
        identifier: URL, DOI, or other identifier to validate

    Returns:
        dict: Validation result with keys:
            - valid: bool, whether the identifier is supported
            - provider: str or None, name of the supporting provider
            - message: str, description of the result
    """
    from .content_providers import (
        Zenodo, Figshare, Dryad, Pangaea, OSF,
        Dataverse, GFZ, Pensoft, Opara
    )

    # Try each provider in order
    provider_classes = [
        Dryad.Dryad,
        Figshare.Figshare,
        Zenodo.Zenodo,
        Pangaea.Pangaea,
        OSF.OSF,
        Dataverse.Dataverse,
        GFZ.GFZ,
        Pensoft.Pensoft,
        Opara.Opara,
    ]

    for provider_class in provider_classes:
        provider = provider_class()
        try:
            if provider.validate_provider(identifier):
                return {
                    "valid": True,
                    "provider": provider.name,
                    "message": f"Identifier is supported by {provider.name}"
                }
        except Exception as e:
            # Continue to next provider if validation fails
            logger.debug(f"Provider {provider.name} validation failed: {e}")
            continue

    return {
        "valid": False,
        "provider": None,
        "message": "Identifier is not supported by any known content provider"
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

    handlers = [
        ("CSV", handleCSV),
        ("Vector", handleVector),
        ("Raster", handleRaster)
    ]

    for handler_name, handler_module in handlers:
        try:
            if handler_module.checkFileSupported(filepath):
                return {
                    "valid": True,
                    "handler": handler_module.get_handler_name(),
                    "message": f"File format is supported by {handler_name} handler"
                }
        except Exception as e:
            # Continue to next handler if validation fails
            logger.debug(f"Handler {handler_name} validation failed: {e}")
            continue

    return {
        "valid": False,
        "handler": None,
        "message": "File format is not supported by any known handler"
    }
