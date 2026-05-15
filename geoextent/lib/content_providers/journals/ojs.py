"""OJS (Open Journal Systems) journal landing-page provider.

Detects OJS by the ``<meta name="generator" content="Open Journal Systems …">``
tag that every OJS theme emits. The geospatial metadata itself is extracted
by :class:`JournalProvider` from whatever the ``ojsGeo`` plugin
(https://github.com/nuest/ojsGeo) inlined into the head — typically a
``DC.SpatialCoverage`` FeatureCollection plus ``ICBM`` / ``geo.position``
centroids.

A page that advertises OJS but ships without the geo plugin is still
matched; ``download_record`` then surfaces no spatial extent (only the
publication date, if any).
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from ._base import JournalProvider


class OJS(JournalProvider):
    """Content provider for OJS journal article landing pages."""

    name = "OJS"

    @classmethod
    def provider_info(cls):
        return {
            "name": "OJS",
            "description": (
                "Open Journal Systems (OJS) journal article landing pages. "
                "Detects the OJS generator meta tag and extracts geospatial "
                "metadata embedded by the ojsGeo plugin (Dublin Core "
                "SpatialCoverage GeoJSON / WKT, ICBM, geo.position). Works "
                "across any OJS-hosted journal that has the plugin installed; "
                "pages without it are still recognised as OJS but return no "
                "spatial extent."
            ),
            "website": "https://pkp.sfu.ca/ojs/",
            "supported_identifiers": [
                "https://{journal-host}/article/view/{id}",
                "https://doi.org/{any-DOI-resolving-to-OJS}",
            ],
            "examples": [
                "https://service.tib.eu/komet/ojs330/index.php/gmdj/article/view/39",
                "http://localhost:8330/index.php/gmdj/article/view/44",
            ],
        }

    def _is_my_platform(self, html: str, url: str) -> bool:
        # Parse the head only and look up <meta name="generator"> properly,
        # so attribute order in the source HTML doesn't matter.
        soup = BeautifulSoup(html, "html.parser")
        generator = soup.find("meta", attrs={"name": "generator"})
        if not generator:
            return False
        content = generator.get("content") or ""
        return "open journal systems" in content.lower()
