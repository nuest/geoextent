"""
Geoextent - Extract geospatial extent (bounding boxes and temporal extents) from files and directories.

This package provides functionality for extracting spatial and temporal extents from
geospatial data files and research repositories.
"""

name = "geoextent"

try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"

# Import main functions for easy access
from .lib.extent import fromFile, fromDirectory, fromRemote, from_repository

# Import main modules for advanced usage
from . import lib

__all__ = [
    'fromFile',
    'fromDirectory',
    'fromRemote',
    'from_repository',  # Backward compatibility (deprecated)
    'lib',
    '__version__'
]
