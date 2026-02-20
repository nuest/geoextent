"""
Generic CKAN content provider for geoextent.

Handles any CKAN instance by recognising dataset URLs matching the pattern
``https://{host}/dataset/{id_or_name}`` and verifying via the CKAN API.

Known CKAN instances are matched instantly; unknown instances are verified
by probing the ``/api/3/action/status_show`` endpoint.

This provider is a catch-all that should be ordered AFTER all specific
CKAN-based providers (e.g., Senckenberg) in the provider list.

See: https://docs.ckan.org/en/latest/api/
"""

import logging
import re
from urllib.parse import urlparse

from .CKANProvider import CKANProvider

logger = logging.getLogger("geoextent")

# CKAN instances handled by dedicated providers — exclude from generic matching
_EXCLUDED_HOSTS = {
    "dataportal.senckenberg.de",
}

# Known CKAN instances (no API probe needed)
_KNOWN_CKAN_HOSTS = [
    "geokur-dmp.geo.tu-dresden.de",
    "ckan.publishing.service.gov.uk",
    "ckan.govdata.de",
    "open.canada.ca",
    "data.gov.au",
    "catalog.data.gov",
    "data.gov.ie",
    "data.gov.sg",
]

# URL pattern: https://{host}[/subpath]/dataset/{id_or_name}
_DATASET_URL_RE = re.compile(
    r"https?://([^/]+)(?:/[^/]+)*/dataset/([^/?#]+)",
    re.IGNORECASE,
)


class CKAN(CKANProvider):
    """Generic content provider for any CKAN instance.

    Matches dataset URLs of the form ``https://{host}/dataset/{id}`` and
    verifies the host is a CKAN instance via the standard API.
    """

    doi_prefixes = ()  # No DOI fast path for generic CKAN

    @classmethod
    def provider_info(cls):
        return {
            "name": "CKAN",
            "description": (
                "Generic provider for CKAN (Comprehensive Knowledge Archive Network) "
                "instances. CKAN is an open-source data management system used by "
                "government agencies, research organisations, and other institutions "
                "worldwide to publish and share open data."
            ),
            "website": "https://ckan.org/",
            "supported_identifiers": [
                "https://{ckan-host}/dataset/{dataset_id_or_name}",
            ],
            "known_hosts": list(_KNOWN_CKAN_HOSTS),
            "examples": [
                "https://geokur-dmp.geo.tu-dresden.de/dataset/cropland-extent",
                "https://ckan.publishing.service.gov.uk/dataset/bishkek-spatial-data",
                "https://ckan.govdata.de/dataset/a-spatially-distributed-sampling-of-rhine-surface-water-for-non-target-screening",
            ],
            "notes": (
                "Catch-all provider for CKAN instances. Specific CKAN instances "
                "(e.g., Senckenberg) have dedicated providers that take priority. "
                "Unknown hosts are verified by probing the CKAN status_show API."
            ),
        }

    def __init__(self):
        super().__init__()
        self.name = "CKAN"
        self._verified_hosts = set()  # Cache verified CKAN hosts within session

    def validate_provider(self, reference):
        """Validate if the reference points to a CKAN dataset.

        Strategy:

        1. Parse URL for ``/dataset/{id}`` pattern
        2. Reject hosts handled by dedicated providers
        3. Fast path: known CKAN hosts
        4. Slow path: probe ``/api/3/action/status_show``

        Returns:
            bool: True if this provider can handle the reference
        """
        self.reference = reference

        # Try to get the resolved URL (handles DOI resolution)
        try:
            url = self.get_url
        except Exception:
            url = reference

        # Match /dataset/{id} URL pattern
        match = _DATASET_URL_RE.match(url)
        if not match:
            return False

        host = match.group(1)
        dataset_id = match.group(2)

        # Reject hosts handled by dedicated providers
        if host.lower() in _EXCLUDED_HOSTS:
            return False

        # Derive API base URL — handle subpath instances (e.g., open.canada.ca/data/)
        parsed = urlparse(url)
        path = parsed.path
        dataset_idx = path.find("/dataset/")
        api_prefix = path[:dataset_idx] if dataset_idx > 0 else ""
        scheme = parsed.scheme or "https"

        self.dataset_id = dataset_id
        self.host = {
            "hostname": [
                f"{scheme}://{host}{api_prefix}/dataset/",
            ],
            "api": f"{scheme}://{host}{api_prefix}/api/3/",
        }
        self.name = f"CKAN ({host})"

        # Fast path: known CKAN host
        if host.lower() in [h.lower() for h in _KNOWN_CKAN_HOSTS]:
            self.log.debug(f"Known CKAN host: {host}")
            return True

        # Fast path: already verified this session
        if host.lower() in self._verified_hosts:
            return True

        # Slow path: probe the CKAN API
        if self._is_ckan_instance(host, f"{scheme}://{host}{api_prefix}"):
            self._verified_hosts.add(host.lower())
            return True

        return False

    def _is_ckan_instance(self, host, base_url):
        """Probe ``/api/3/action/status_show`` to verify this is a CKAN instance.

        Args:
            host: Hostname for logging
            base_url: Base URL including any subpath (e.g., ``https://open.canada.ca/data``)

        Returns:
            bool: True if the host responds with a valid CKAN status response
        """
        try:
            response = self._request(
                f"{base_url}/api/3/action/status_show",
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            # CKAN API returns {"success": true, "result": {"site_title": ..., ...}}
            return data.get("success", False)
        except Exception as e:
            self.log.debug(f"Host {host} is not a CKAN instance: {e}")
            return False
