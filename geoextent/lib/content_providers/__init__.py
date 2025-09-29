# Content providers for geoextent
# This package contains modules for extracting data from various research repositories

# Import all providers
from . import providers
from . import Zenodo
from . import Figshare
from . import Dryad
from . import OSF
from . import Dataverse
from . import GFZ

# Conditionally import Pangaea only if pangaeapy is available
try:
    import pangaeapy
    from . import Pangaea
    HAS_PANGAEA = True
except ImportError:
    Pangaea = None
    HAS_PANGAEA = False

__all__ = [
    'providers',
    'Zenodo',
    'Figshare',
    'Dryad',
    'OSF',
    'Dataverse',
    'GFZ'
]

if HAS_PANGAEA:
    __all__.append('Pangaea')