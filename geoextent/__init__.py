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

from .lib.extent import from_file, from_directory, from_remote
from .lib.export import export_to_file, join_files

# Import main modules for advanced usage
from . import lib

__all__ = [
    "from_file",
    "from_directory",
    "from_remote",
    "export_to_file",
    "join_files",
    "lib",
    "__version__",
]
