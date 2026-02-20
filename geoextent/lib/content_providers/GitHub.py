"""
GitHub content provider for geoextent.

Extracts geospatial extent from GitHub repositories by:
1. Listing files via the Git Trees API (1 API call, handles ~100k files)
2. Filtering for geospatial file extensions
3. Downloading files via raw.githubusercontent.com (no API rate limit)

Supported identifiers:
- https://github.com/{owner}/{repo}
- https://github.com/{owner}/{repo}/tree/{ref}
- https://github.com/{owner}/{repo}/tree/{ref}/{path}

API usage: 2 calls per repo (get default branch + list tree).
Unauthenticated limit: 60/hour. With token (GITHUB_TOKEN): 5000/hour.
"""

import logging
import os
import re

from geoextent.lib.content_providers.GitHostProvider import GitHostProvider

logger = logging.getLogger("geoextent")

_GITHUB_URL_RE = re.compile(
    r"https?://github\.com/"
    r"([^/]+)/"  # owner
    r"([^/]+?)"  # repo (non-greedy to handle .git suffix)
    r"(?:\.git)?"  # optional .git suffix
    r"(?:/tree/"
    r"([^/]+)"  # ref (branch/tag/commit)
    r"(?:/(.+))?"  # optional path within repo
    r")?"
    r"/?$",
    re.IGNORECASE,
)

_GITHUB_API = "https://api.github.com"
_GITHUB_RAW = "https://raw.githubusercontent.com"


class GitHub(GitHostProvider):
    """GitHub content provider."""

    def __init__(self):
        super().__init__()
        self.name = "GitHub"
        self._api_headers = {"Accept": "application/vnd.github.v3+json"}
        # Use GITHUB_TOKEN env var if available for higher rate limits
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            self._api_headers["Authorization"] = f"token {token}"
            self.log.debug("Using GITHUB_TOKEN for authenticated API access")

    @classmethod
    def provider_info(cls):
        return {
            "name": "GitHub",
            "description": (
                "GitHub is a platform for hosting and collaborating on code and data. "
                "This provider downloads geospatial files from public GitHub repositories "
                "and extracts their spatial and temporal extent."
            ),
            "website": "https://github.com/",
            "supported_identifiers": [
                "https://github.com/{owner}/{repo}",
                "https://github.com/{owner}/{repo}/tree/{ref}",
                "https://github.com/{owner}/{repo}/tree/{ref}/{path}",
            ],
            "examples": [
                "https://github.com/fraxen/tectonicplates",
                "https://github.com/Nowosad/spDataLarge/tree/master/inst/raster",
            ],
        }

    def validate_provider(self, reference):
        """Match github.com repository URLs."""
        match = _GITHUB_URL_RE.match(reference)
        if match:
            self.reference = reference
            self.name = "GitHub"
            return True
        return False

    def _parse_reference(self, url):
        m = _GITHUB_URL_RE.match(url)
        return {
            "owner": m.group(1),
            "repo": m.group(2),
            "ref": m.group(3),
            "path": m.group(4),
        }

    def _get_default_branch(self, owner, repo):
        resp = self._request(
            f"{_GITHUB_API}/repos/{owner}/{repo}",
            headers=self._api_headers,
        )
        return resp.json()["default_branch"]

    def _list_files(self, owner, repo, ref, path=None):
        resp = self._request(
            f"{_GITHUB_API}/repos/{owner}/{repo}/git/trees/{ref}?recursive=1",
            headers=self._api_headers,
        )
        data = resp.json()

        files = [
            {"path": item["path"], "size": item.get("size", 0), "type": item["type"]}
            for item in data.get("tree", [])
            if item["type"] == "blob"
        ]

        # Filter by path prefix if specified
        if path:
            prefix = path.rstrip("/") + "/"
            files = [
                f for f in files if f["path"].startswith(prefix) or f["path"] == path
            ]

        if data.get("truncated"):
            self.log.warning(
                "GitHub tree API returned truncated results for %s/%s; "
                "some files may be missed",
                owner,
                repo,
            )

        return files

    def _get_raw_url(self, owner, repo, ref, path):
        return f"{_GITHUB_RAW}/{owner}/{repo}/{ref}/{path}"
