"""Umbrella package for journal landing-page content providers.

All concrete providers in this package share the meta-tag + JSON-LD parsing
machinery in :class:`JournalProvider`. Subclasses override
``_is_my_platform`` to fingerprint their host platform (OJS, Janeway, …);
DOI-prefix-shortcut publishers (Pensoft) additionally override
``validate_provider`` for a fast path that skips the platform sniff.

Public re-exports — :class:`OJS`, :class:`Janeway`, :class:`Pensoft` — match
the convention used elsewhere under ``content_providers/`` so callers can do
``from geoextent.lib.content_providers.journals import OJS``.
"""

from ._base import JournalProvider
from .ojs import OJS
from .janeway import Janeway
from .pensoft import Pensoft

__all__ = ["JournalProvider", "OJS", "Janeway", "Pensoft"]
