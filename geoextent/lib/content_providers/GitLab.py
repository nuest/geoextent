"""
GitLab content provider for geoextent.

Extracts geospatial extent from GitLab repositories by:
1. Listing files via the Repository Tree API (paginated, per_page=100)
2. Filtering for geospatial file extensions
3. Downloading files via the raw file content API

Supported identifiers:
- https://gitlab.com/{namespace}/{project}
- https://gitlab.com/{namespace}/{project}/-/tree/{ref}
- https://gitlab.com/{namespace}/{project}/-/tree/{ref}/{path}
- Self-hosted GitLab instances (detected by known hosts or API probe)

API usage: 1 call for project info + N calls for paginated tree listing.
Unauthenticated limit on gitlab.com: ~400 requests/10 min.
With token (GITLAB_TOKEN): higher limits per instance configuration.
"""

import logging
import os
import re
from urllib.parse import quote_plus, urlparse

from geoextent.lib.content_providers.GitHostProvider import GitHostProvider

logger = logging.getLogger("geoextent")

# Known GitLab instances (hostnames)
_KNOWN_GITLAB_HOSTS = {
    "gitlab.com",
    # German universities and research institutions
    "git.rwth-aachen.de",
    "zivgitlab.uni-muenster.de",
    "git.gfz-potsdam.de",
    "codebase.helmholtz.cloud",
    # Government platforms
    "gitlab.opencode.de",
    "gitlab-forge.din.developpement-durable.gouv.fr",
    # European universities
    "gitlab.ethz.ch",
    "git.wur.nl",
    "git.wageningenur.nl",
    "code.vt.edu",
    # European research/intergovernmental
    "gitlab.eumetsat.int",
    "gitlab.orfeo-toolbox.org",
    "gitlab.inria.fr",
    "gitlab.in2p3.fr",
    "gitlab.huma-num.fr",
    "forge.inrae.fr",
    "baltig.infn.it",
    "gitlab.cern.ch",
    # Community instances
    "framagit.org",
    "salsa.debian.org",
}


class GitLab(GitHostProvider):
    """GitLab content provider.

    Supports gitlab.com and self-hosted GitLab instances.
    Detects instances via known hostnames, "gitlab" in hostname,
    or API probe fallback.
    """

    def __init__(self):
        super().__init__()
        self.name = "GitLab"
        self._host = None
        self._api_base = None
        self._api_headers = {"Accept": "application/json"}
        # Use GITLAB_TOKEN env var if available for higher rate limits
        token = os.environ.get("GITLAB_TOKEN")
        if token:
            self._api_headers["PRIVATE-TOKEN"] = token
            self.log.debug("Using GITLAB_TOKEN for authenticated API access")

    @classmethod
    def provider_info(cls):
        return {
            "name": "GitLab",
            "description": (
                "GitLab is a platform for hosting and collaborating on code "
                "and data. This provider downloads geospatial files from "
                "public GitLab repositories on gitlab.com and self-hosted "
                "instances, and extracts their spatial and temporal extent."
            ),
            "website": "https://gitlab.com/",
            "supported_identifiers": [
                "https://gitlab.com/{namespace}/{project}",
                "https://gitlab.com/{namespace}/{project}/-/tree/{ref}",
                "https://{gitlab-host}/{namespace}/{project}",
            ],
            "examples": [
                "https://gitlab.com/eaws/eaws-regions/-/tree/master/public/outline",
                "https://gitlab.com/bazylizon/seismicity",
                "https://git.rwth-aachen.de/nfdi4earth/crosstopics/knowledgehub-maps",
            ],
        }

    def _is_gitlab_host(self, hostname):
        """Check if hostname is a known or likely GitLab instance."""
        if hostname in _KNOWN_GITLAB_HOSTS:
            return True
        if "gitlab" in hostname.lower():
            return True
        return False

    def _probe_gitlab_api(self, host):
        """Probe if host is a GitLab instance via API.

        Sends a lightweight request to the projects endpoint.
        If it returns a JSON array, the host is a GitLab instance.
        """
        try:
            resp = self.session.get(
                f"https://{host}/api/v4/projects?per_page=1",
                timeout=10,
                headers=self._api_headers,
            )
            if resp.status_code != 200:
                return False
            data = resp.json()
            return isinstance(data, list)
        except Exception:
            return False

    def validate_provider(self, reference):
        """Match GitLab repository URLs.

        Uses a three-stage approach:
        1. Known GitLab hostnames (fast, no network)
        2. Hostname contains "gitlab" (fast, no network)
        3. API probe fallback (network, slow)
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

        # Must not be github.com (handled by GitHub provider)
        if hostname == "github.com":
            return False

        # Check if it's a known or likely GitLab host
        is_gitlab = self._is_gitlab_host(hostname)

        # If not a known host, try API probe
        if not is_gitlab:
            is_gitlab = self._probe_gitlab_api(hostname)

        if not is_gitlab:
            return False

        # Must have at least 2 path segments (namespace/project)
        path = parsed.path.strip("/")
        # Strip .git suffix and /-/ resource paths for validation
        clean_path = re.sub(r"\.git$", "", path)
        clean_path = re.sub(r"/-/.*$", "", clean_path)

        segments = [s for s in clean_path.split("/") if s]
        if len(segments) < 2:
            return False

        self.reference = reference
        self._host = hostname
        self._api_base = f"{parsed.scheme}://{hostname}/api/v4"
        return True

    def _parse_reference(self, url):
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # Remove .git suffix
        path = re.sub(r"\.git$", "", path)

        ref = None
        subpath = None

        # Check for /-/tree/ or /-/blob/ separator
        resource_match = re.search(r"/-/(?:tree|blob)/([^/]+)(?:/(.+))?$", path)
        if resource_match:
            ref = resource_match.group(1)
            subpath = resource_match.group(2)
            # Project path is everything before /-/
            project_path = path[: path.index("/-/")]
        else:
            project_path = path

        # Split into namespace segments
        segments = [s for s in project_path.split("/") if s]

        # For GitLab: namespace can be nested (group/subgroup/.../project)
        # owner = everything except last segment, repo = last segment
        if len(segments) >= 2:
            owner = "/".join(segments[:-1])
            repo = segments[-1]
        else:
            owner = segments[0] if segments else ""
            repo = ""

        return {
            "owner": owner,
            "repo": repo,
            "ref": ref,
            "path": subpath,
        }

    def _get_project_id(self, owner, repo):
        """Get URL-encoded project path for API calls."""
        project_path = f"{owner}/{repo}"
        return quote_plus(project_path)

    def _get_default_branch(self, owner, repo):
        project_id = self._get_project_id(owner, repo)
        resp = self._request(
            f"{self._api_base}/projects/{project_id}",
            headers=self._api_headers,
        )
        return resp.json()["default_branch"]

    def _list_files(self, owner, repo, ref, path=None):
        project_id = self._get_project_id(owner, repo)
        all_files = []
        page = 1
        per_page = 100

        while True:
            url = (
                f"{self._api_base}/projects/{project_id}/repository/tree"
                f"?ref={ref}&recursive=true&per_page={per_page}&page={page}"
            )
            if path:
                url += f"&path={quote_plus(path)}"

            resp = self._request(url, headers=self._api_headers)
            items = resp.json()

            if not items:
                break

            for item in items:
                if item["type"] == "blob":
                    all_files.append(
                        {
                            "path": item["path"],
                            "size": 0,  # GitLab tree API does not return sizes
                            "type": "blob",
                        }
                    )

            # Check for next page
            if len(items) < per_page:
                break
            page += 1

        return all_files

    def _get_raw_url(self, owner, repo, ref, path):
        # Use API endpoint for reliable raw file access across all instances
        project_id = self._get_project_id(owner, repo)
        encoded_path = quote_plus(path)
        return (
            f"{self._api_base}/projects/{project_id}"
            f"/repository/files/{encoded_path}/raw?ref={ref}"
        )
