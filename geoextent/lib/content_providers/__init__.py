"""
Content providers for geoextent.

This package contains modules for extracting data from various research repositories.
"""

# Import all content providers
from . import providers
from . import Zenodo
from . import InvenioRDM
from . import Figshare
from . import Dryad
from . import Pangaea
from . import OSF
from . import Dataverse
from . import GFZ
from . import Pensoft
from . import Opara
from . import BGR
from . import Senckenberg
from . import MendeleyData
from . import Wikidata
from . import FourTU
from . import RADAR
from . import ArcticDataCenter
from . import DEIMSSDR

__all__ = [
    "providers",
    "Zenodo",
    "InvenioRDM",
    "Figshare",
    "Dryad",
    "Pangaea",
    "OSF",
    "Dataverse",
    "GFZ",
    "Pensoft",
    "Opara",
    "BGR",
    "Senckenberg",
    "MendeleyData",
    "Wikidata",
    "FourTU",
    "RADAR",
    "ArcticDataCenter",
    "DEIMSSDR",
]
