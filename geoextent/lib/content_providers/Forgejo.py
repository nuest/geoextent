"""
Forgejo/Gitea content provider for geoextent.

Extracts geospatial extent from Forgejo and Gitea repositories by:
1. Listing files via the Git Trees API (paginated, per_page=1000)
2. Filtering for geospatial file extensions
3. Downloading files via the raw file API endpoint

Supported identifiers:
- https://codeberg.org/{owner}/{repo}
- https://codeberg.org/{owner}/{repo}/tree/{ref}
- https://codeberg.org/{owner}/{repo}/tree/{ref}/{path}
- Self-hosted Forgejo/Gitea instances (detected by known hosts or API probe)

API usage: 1 call for repo info + N calls for paginated tree listing.
Unauthenticated limit varies per instance; Codeberg allows ~60 req/hour.
With token (FORGEJO_TOKEN): higher limits per instance configuration.
"""

import logging
import os
import re
from urllib.parse import urlparse

from geoextent.lib.content_providers.GitHostProvider import GitHostProvider
from geoextent.lib.content_providers.GitLab import _KNOWN_GITLAB_HOSTS

logger = logging.getLogger("geoextent")

_KNOWN_FORGEJO_HOSTS = {
    "codeberg.org",
    "datahub.hcdc.hereon.de",  # Helmholtz DataHub (behind AAI)
    "hub.datalad.org",  # DataLad Hub (Forgejo-aneksajo)
}


class Forgejo(GitHostProvider):
    """Forgejo/Gitea content provider.

    Supports Codeberg.org and self-hosted Forgejo/Gitea instances.
    Detects instances via known hostnames, "forgejo" or "gitea" in hostname,
    or API probe fallback (GET /api/v1/version).
    """

    def __init__(self):
        super().__init__()
        self.name = "Forgejo"
        self._host = None
        self._api_base = None
        self._api_headers = {"Accept": "application/json"}
        token = os.environ.get("FORGEJO_TOKEN")
        if token:
            self._api_headers["Authorization"] = f"token {token}"
            self.log.debug("Using FORGEJO_TOKEN for authenticated API access")

    @classmethod
    def provider_info(cls):
        return {
            "name": "Forgejo",
            "description": (
                "Forgejo and Gitea are community-driven git hosting platforms. "
                "This provider downloads geospatial files from public Forgejo/Gitea "
                "repositories (including Codeberg.org) and extracts their spatial "
                "and temporal extent."
            ),
            "website": "https://codeberg.org/",
            "supported_identifiers": [
                "https://codeberg.org/{owner}/{repo}",
                "https://codeberg.org/{owner}/{repo}/tree/{ref}",
                "https://{forgejo-host}/{owner}/{repo}",
            ],
            "examples": [
                "https://codeberg.org/steko/ancient-ceramic-kilns",
                "https://codeberg.org/mokazemi/iran-geojson",
            ],
        }

    def _is_forgejo_host(self, hostname):
        """Check if hostname is a known or likely Forgejo/Gitea instance."""
        if hostname in _KNOWN_FORGEJO_HOSTS:
            return True
        hn = hostname.lower()
        if "forgejo" in hn or "gitea" in hn:
            return True
        return False

    def _probe_forgejo_api(self, host):
        """Probe if host is a Forgejo/Gitea instance via API.

        Sends GET /api/v1/version which returns {"version": "..."} on
        Forgejo and Gitea instances.
        """
        try:
            resp = self.session.get(
                f"https://{host}/api/v1/version",
                timeout=10,
                headers=self._api_headers,
            )
            if resp.status_code != 200:
                return False
            data = resp.json()
            return "version" in data
        except Exception:
            return False

    def validate_provider(self, reference):
        """Match Forgejo/Gitea repository URLs.

        Uses a three-stage approach:
        1. Known Forgejo/Gitea hostnames (fast, no network)
        2. Hostname contains "forgejo" or "gitea" (fast, no network)
        3. API probe fallback: GET /api/v1/version (network, slow)
        """
        try:
            parsed = urlparse(reference)
        except Exception:
            return False

        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Exclude hosts handled by other providers
        if hostname == "github.com":
            return False
        if hostname in _KNOWN_GITLAB_HOSTS:
            return False

        # Check if it's a known or likely Forgejo/Gitea host
        is_forgejo = self._is_forgejo_host(hostname)

        # If not a known host, try API probe
        if not is_forgejo:
            is_forgejo = self._probe_forgejo_api(hostname)

        if not is_forgejo:
            return False

        # Must have at least 2 path segments (owner/repo)
        path = parsed.path.strip("/")
        # Strip .git suffix and /tree/ resource paths for validation
        clean_path = re.sub(r"\.git$", "", path)
        clean_path = re.sub(r"/tree/.*$", "", clean_path)

        segments = [s for s in clean_path.split("/") if s]
        if len(segments) < 2:
            return False

        self.reference = reference
        self._host = hostname
        self._api_base = f"{parsed.scheme}://{hostname}/api/v1"
        return True

    def _parse_reference(self, url):
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # Remove .git suffix
        path = re.sub(r"\.git$", "", path)

        ref = None
        subpath = None

        # Check for /tree/{ref} or /tree/{ref}/{path}
        tree_match = re.search(r"/tree/([^/]+)(?:/(.+))?$", path)
        if tree_match:
            ref = tree_match.group(1)
            subpath = tree_match.group(2)
            # Owner/repo is everything before /tree/
            project_path = path[: path.index("/tree/")]
        else:
            project_path = path

        segments = [s for s in project_path.split("/") if s]

        if len(segments) >= 2:
            owner = segments[0]
            repo = segments[1]
        else:
            owner = segments[0] if segments else ""
            repo = ""

        return {
            "owner": owner,
            "repo": repo,
            "ref": ref,
            "path": subpath,
        }

    def _get_default_branch(self, owner, repo):
        resp = self._request(
            f"{self._api_base}/repos/{owner}/{repo}",
            headers=self._api_headers,
        )
        return resp.json()["default_branch"]

    def _list_files(self, owner, repo, ref, path=None):
        all_files = []
        page = 1
        per_page = 1000

        while True:
            url = (
                f"{self._api_base}/repos/{owner}/{repo}/git/trees/{ref}"
                f"?recursive=true&per_page={per_page}&page={page}"
            )

            resp = self._request(url, headers=self._api_headers)
            data = resp.json()

            tree = data.get("tree", [])
            if not tree:
                break

            for item in tree:
                if item["type"] == "blob":
                    all_files.append(
                        {
                            "path": item["path"],
                            "size": item.get("size", 0),
                            "type": "blob",
                        }
                    )

            # Gitea returns truncated=true if not all entries fit
            if not data.get("truncated", False):
                break
            page += 1

        # Filter by path prefix if specified
        if path:
            prefix = path.rstrip("/") + "/"
            all_files = [
                f
                for f in all_files
                if f["path"].startswith(prefix) or f["path"] == path
            ]

        return all_files

    def _get_raw_url(self, owner, repo, ref, path):
        return f"{self._api_base}/repos/{owner}/{repo}/raw/{path}?ref={ref}"
