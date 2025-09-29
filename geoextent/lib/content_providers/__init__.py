"""
Content providers for geoextent.

This package contains modules for extracting data from various research repositories.
"""

# Import all content providers
from . import providers
from . import Zenodo
from . import Figshare
from . import Dryad
from . import Pangaea
from . import OSF
from . import Dataverse
from . import GFZ
from . import Pensoft

__all__ = [
    'providers',
    'Zenodo',
    'Figshare',
    'Dryad',
    'Pangaea',
    'OSF',
    'Dataverse',
    'GFZ',
    'Pensoft'
]