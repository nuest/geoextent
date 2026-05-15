"""Janeway journal landing-page provider.

Detects Janeway by any of:

* ``<link rel="alternate" type="application/geo+json">`` — the
  ``janeway_geometadata`` plugin's canonical GeoJSON export link, only
  emitted when the plugin is installed.
* ``/static/geometadata/`` paths and ``/article/id/{N}/`` URL pattern — the
  Janeway default URL scheme together with the plugin's static assets.
* ``<meta name="generator" content="Janeway …">`` — some Janeway themes
  advertise the platform explicitly.

When the plugin is not installed but the URL still looks Janeway-shaped
(``/article/id/{N}/``), this provider declines so cleaner providers can take
a turn.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from ._base import JournalProvider


class Janeway(JournalProvider):
    """Content provider for Janeway journal article landing pages."""

    name = "Janeway"

    @classmethod
    def provider_info(cls):
        return {
            "name": "Janeway",
            "description": (
                "Janeway journal article landing pages (https://janeway.systems/). "
                "Detects Janeway via the geo+json alternate link emitted by the "
                "janeway_geometadata plugin "
                "(https://github.com/GeoinformationSystems/janeway_geometadata/), "
                "or via the platform's static asset paths combined with the "
                "/article/id/{N}/ URL pattern. Extracts JSON-LD spatialCoverage, "
                "DC.SpatialCoverage (GeoJSON/WKT), DC.box, ISO 19139, "
                "DC.temporal, and follows the alternate geo+json link to the "
                "plugin's canonical export."
            ),
            "website": "https://janeway.systems/",
            "supported_identifiers": [
                "https://{journal-host}/{journal-code}/article/id/{N}/",
                "https://doi.org/{any-DOI-resolving-to-Janeway}",
            ],
            "examples": [
                "http://localhost:8000/dqj/article/id/53/",
            ],
        }

    def _is_my_platform(self, html: str, url: str) -> bool:
        soup = BeautifulSoup(html, "html.parser")

        generator = soup.find("meta", attrs={"name": "generator"})
        if generator and "janeway" in (generator.get("content") or "").lower():
            return True

        for link in soup.find_all("link"):
            rel = link.get("rel") or []
            ltype = (link.get("type") or "").lower()
            if "alternate" in rel and "geo+json" in ltype:
                return True

        if "/static/geometadata/" in html and "/article/id/" in url:
            return True
        return False
