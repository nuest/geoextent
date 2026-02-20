"""
Software Heritage content provider for geoextent.

Extracts geospatial extent from software artifacts archived by Software Heritage
(https://www.softwareheritage.org/), a non-profit archive of all publicly available
source code, assigning persistent identifiers (SWHIDs) to every software artifact.

Supported identifiers:
- Bare SWHIDs: swh:1:(cnt|dir|rev|rel|snp|ori):<40hex>[;qualifiers]
- Browse URLs: https://archive.softwareheritage.org/browse/origin/directory/?origin_url=...
- Browse URLs: https://archive.softwareheritage.org/browse/directory/<sha>/
- Browse URLs: https://archive.softwareheritage.org/browse/revision/<sha>/
- SWHID URLs: https://archive.softwareheritage.org/swh:1:...

API rate limits: 120 req/hr anonymous, 1200 req/hr with SWH_TOKEN env var.
"""

import logging
import os
import re
from urllib.parse import parse_qs, urlparse, unquote

from geoextent.lib.content_providers.providers import DoiProvider
from geoextent.lib import helpfunctions as hf

logger = logging.getLogger("geoextent")

SWH_API = "https://archive.softwareheritage.org/api/1"

_SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".svn",
    ".hg",
    ".tox",
    ".eggs",
    ".mypy_cache",
    ".pytest_cache",
    "venv",
    ".venv",
}

# --- Identifier patterns ---

# Bare SWHID: swh:1:<type>:<40hex>[;qualifier=value;...]
_SWHID_RE = re.compile(
    r"^swh:1:(cnt|dir|rev|rel|snp|ori):([0-9a-f]{40})" r"((?:;[a-z_]+=\S+)*)$",
    re.IGNORECASE,
)

# Browse origin URL:
# https://archive.softwareheritage.org/browse/origin/directory/?origin_url=<url>[&path=<path>]
_BROWSE_ORIGIN_RE = re.compile(
    r"^https?://archive\.softwareheritage\.org/browse/origin/directory/\?",
    re.IGNORECASE,
)

# Browse directory URL:
# https://archive.softwareheritage.org/browse/directory/<sha1_git>/
_BROWSE_DIR_RE = re.compile(
    r"^https?://archive\.softwareheritage\.org/browse/directory/([0-9a-f]{40})/?$",
    re.IGNORECASE,
)

# Browse revision URL:
# https://archive.softwareheritage.org/browse/revision/<sha1_git>/
_BROWSE_REV_RE = re.compile(
    r"^https?://archive\.softwareheritage\.org/browse/revision/([0-9a-f]{40})/?$",
    re.IGNORECASE,
)

# SWHID in URL form:
# https://archive.softwareheritage.org/swh:1:...
_SWHID_URL_RE = re.compile(
    r"^https?://archive\.softwareheritage\.org/(swh:1:\S+)$",
    re.IGNORECASE,
)


class SoftwareHeritage(DoiProvider):
    """Software Heritage content provider."""

    doi_prefixes = ()

    @property
    def supports_metadata_extraction(self):
        return False

    def __init__(self):
        super().__init__()
        self.name = "Software Heritage"
        self._swhid_type = None
        self._swhid_hash = None
        self._origin_url = None
        self._subpath = None
        self._qualifiers = {}
        # Use SWH_TOKEN env var for authenticated access (1200 req/hr)
        token = os.environ.get("SWH_TOKEN")
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
            self.log.debug("Using SWH_TOKEN for authenticated API access")

    @classmethod
    def provider_info(cls):
        return {
            "name": "Software Heritage",
            "description": (
                "Software Heritage is a non-profit archive (Inria + UNESCO) of all "
                "publicly available source code, assigning persistent identifiers "
                "(SWHIDs) to every software artifact. This provider downloads "
                "geospatial files from archived repositories and extracts their "
                "spatial and temporal extent."
            ),
            "website": "https://www.softwareheritage.org/",
            "supported_identifiers": [
                "swh:1:dir:<40-hex>",
                "swh:1:ori:<40-hex>",
                "swh:1:rev:<40-hex>",
                "swh:1:cnt:<40-hex>",
                "https://archive.softwareheritage.org/browse/origin/directory/?origin_url=<url>",
                "https://archive.softwareheritage.org/browse/directory/<sha1_git>/",
            ],
            "examples": [
                "swh:1:dir:b9d02ab606442f4e63ab1f3317318e03176bdfe0",
                "https://archive.softwareheritage.org/browse/origin/directory/"
                "?origin_url=https://github.com/AWMC/geodata"
                "&path=Cultural-Data/political_shading/hasmonean",
            ],
        }

    def validate_provider(self, reference):
        """Match SWH identifier patterns."""
        self.reference = reference

        # 1. Bare SWHID
        m = _SWHID_RE.match(reference)
        if m:
            self._swhid_type = m.group(1).lower()
            self._swhid_hash = m.group(2).lower()
            quals = m.group(3)
            if quals:
                self._qualifiers = _parse_qualifiers(quals)
                if "origin" in self._qualifiers:
                    self._origin_url = self._qualifiers["origin"]
                if "path" in self._qualifiers:
                    self._subpath = self._qualifiers["path"].strip("/")
            return True

        # 2. SWHID in URL form
        m = _SWHID_URL_RE.match(reference)
        if m:
            swhid_str = m.group(1)
            inner = _SWHID_RE.match(swhid_str)
            if inner:
                self._swhid_type = inner.group(1).lower()
                self._swhid_hash = inner.group(2).lower()
                quals = inner.group(3)
                if quals:
                    self._qualifiers = _parse_qualifiers(quals)
                    if "origin" in self._qualifiers:
                        self._origin_url = self._qualifiers["origin"]
                    if "path" in self._qualifiers:
                        self._subpath = self._qualifiers["path"].strip("/")
                return True

        # 3. Browse origin URL
        if _BROWSE_ORIGIN_RE.match(reference):
            parsed = urlparse(reference)
            qs = parse_qs(parsed.query)
            origin_url = qs.get("origin_url", [None])[0]
            if origin_url:
                self._origin_url = origin_url
                path = qs.get("path", [None])[0]
                if path:
                    self._subpath = path.strip("/")
                return True

        # 4. Browse directory URL
        m = _BROWSE_DIR_RE.match(reference)
        if m:
            self._swhid_type = "dir"
            self._swhid_hash = m.group(1).lower()
            return True

        # 5. Browse revision URL
        m = _BROWSE_REV_RE.match(reference)
        if m:
            self._swhid_type = "rev"
            self._swhid_hash = m.group(1).lower()
            return True

        return False

    def _resolve_to_directory(self):
        """Resolve the identifier to a directory hash.

        Returns:
            (dir_sha, subpath_or_None) tuple.
            For swh:1:cnt: returns (None, None) — handled separately in download().
        """
        swhid_type = self._swhid_type
        swhid_hash = self._swhid_hash
        origin_url = self._origin_url

        # cnt: single content object — no directory
        if swhid_type == "cnt":
            return None, None

        # ori: origin by hash — look up the origin URL first
        if swhid_type == "ori":
            resp = self._request(
                f"{SWH_API}/origin/sha1:{swhid_hash}/get/", throttle=True
            )
            origin_url = resp.json()["url"]
            self._origin_url = origin_url
            # Fall through to origin URL resolution below

        # Origin URL → visit → snapshot → revision → directory
        if origin_url:
            resp = self._request(
                f"{SWH_API}/origin/{_quote_origin(origin_url)}/visit/latest/"
                f"?require_snapshot=true",
                throttle=True,
            )
            snapshot_sha = resp.json()["snapshot"]
            return self._resolve_snapshot(snapshot_sha)

        # snp: snapshot
        if swhid_type == "snp":
            return self._resolve_snapshot(swhid_hash)

        # rel: release → target (may chain through revisions)
        if swhid_type == "rel":
            return self._resolve_release(swhid_hash)

        # rev: revision → directory
        if swhid_type == "rev":
            return self._resolve_revision(swhid_hash)

        # dir: already a directory
        if swhid_type == "dir":
            return swhid_hash, self._subpath

        raise ValueError(f"Unsupported SWHID type: {swhid_type}")

    def _resolve_snapshot(self, snapshot_sha):
        """Resolve snapshot → HEAD branch → revision → directory."""
        resp = self._request(f"{SWH_API}/snapshot/{snapshot_sha}/", throttle=True)
        data = resp.json()
        rev_sha = self._resolve_head_from_snapshot(data)
        return self._resolve_revision(rev_sha)

    def _resolve_head_from_snapshot(self, snapshot_data):
        """Find the HEAD revision from snapshot branches.

        Follows the HEAD alias, then tries main/master, then any revision branch.
        """
        branches = snapshot_data.get("branches", {})

        # Try HEAD alias first
        head = branches.get("HEAD")
        if head and head.get("target_type") == "alias":
            alias_target = head["target"]
            branch = branches.get(alias_target)
            if branch and branch.get("target_type") == "revision":
                return branch["target"]

        # Try common branch names
        for name in ("refs/heads/main", "refs/heads/master"):
            branch = branches.get(name)
            if branch and branch.get("target_type") == "revision":
                return branch["target"]

        # Fall back to any revision branch
        for name, branch in branches.items():
            if branch and branch.get("target_type") == "revision":
                return branch["target"]

        raise ValueError("No revision branch found in snapshot")

    def _resolve_release(self, release_sha):
        """Resolve release → revision → directory (may chain)."""
        resp = self._request(f"{SWH_API}/release/{release_sha}/", throttle=True)
        data = resp.json()
        target_type = data["target_type"]
        target = data["target"]

        if target_type == "revision":
            return self._resolve_revision(target)
        elif target_type == "directory":
            return target, self._subpath
        elif target_type == "release":
            return self._resolve_release(target)
        else:
            raise ValueError(f"Unsupported release target type: {target_type}")

    def _resolve_revision(self, revision_sha):
        """Resolve revision → directory."""
        resp = self._request(f"{SWH_API}/revision/{revision_sha}/", throttle=True)
        dir_sha = resp.json()["directory"]
        return dir_sha, self._subpath

    def _resolve_subpath(self, root_dir_sha, subpath):
        """Resolve a path within a directory tree.

        GET /api/1/directory/{sha}/{path}/ returns either:
        - A single dict (the path resolves to a directory entry) — follow the target
        - A list of dicts (the path resolves to directory contents)

        Returns:
            list of SWH directory entry dicts (the contents of the target directory)
        """
        resp = self._request(
            f"{SWH_API}/directory/{root_dir_sha}/{subpath}/", throttle=True
        )
        data = resp.json()

        if isinstance(data, dict):
            # Single entry: the subpath is a directory. Follow its target hash
            # to list the actual contents.
            if data.get("type") == "dir":
                target_sha = data["target"]
                self.log.debug(
                    "Subpath '%s' resolved to directory %s, listing contents",
                    subpath,
                    target_sha,
                )
                resp2 = self._request(
                    f"{SWH_API}/directory/{target_sha}/", throttle=True
                )
                return resp2.json()
            elif data.get("type") == "file":
                # Single file at the subpath
                return [data]
            else:
                raise ValueError(
                    f"Unexpected entry type from subpath API: {data.get('type')}"
                )
        elif isinstance(data, list):
            self.log.debug("Subpath '%s' resolved to %d entries", subpath, len(data))
            return data
        else:
            raise ValueError(
                f"Unexpected response type from directory subpath API: {type(data)}"
            )

    def _collect_entries(self, entries):
        """Convert SWH directory entries to the flat file list format.

        Args:
            entries: List of SWH directory entry dicts from the directory API.

        Returns:
            list of dicts with keys: path, size, sha1_git
        """
        all_files = []
        for entry in entries:
            if entry["type"] == "file":
                all_files.append(
                    {
                        "path": entry["name"],
                        "size": entry.get("length", 0),
                        "sha1_git": entry["target"],
                    }
                )
            elif entry["type"] == "dir":
                if entry["name"] not in _SKIP_DIRS:
                    sub_files = self._list_files_recursive(
                        entry["target"], entry["name"]
                    )
                    all_files.extend(sub_files)
        return all_files

    def _list_files_recursive(self, dir_sha, prefix=""):
        """Recursively list files in a directory.

        Returns:
            list of dicts with keys: path, size, sha1_git
        """
        resp = self._request(f"{SWH_API}/directory/{dir_sha}/", throttle=True)
        entries = resp.json()
        files = []

        for entry in entries:
            name = entry["name"]
            entry_path = f"{prefix}{name}" if not prefix else f"{prefix}/{name}"

            if entry["type"] == "file":
                files.append(
                    {
                        "path": entry_path,
                        "size": entry.get("length", 0),
                        "sha1_git": entry["target"],
                    }
                )
            elif entry["type"] == "dir":
                if name in _SKIP_DIRS:
                    self.log.debug("Skipping directory: %s", entry_path)
                    continue
                files.extend(self._list_files_recursive(entry["target"], entry_path))

        return files

    def _download_content_raw(self, url, filepath):
        """Download a content file with rate-limit awareness.

        Unlike _download_file_optimized, this method uses _request (which
        handles 429 throttling) to get the raw content, then writes it to disk.
        """
        resp = self._request(url, throttle=True)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(resp.content)
        self.log.debug("Downloaded %d bytes to %s", len(resp.content), filepath)

    def _download_single_content(self, folder, sha, filename):
        """Download a single content object by sha1_git."""
        if not filename:
            # Try to get filename from content metadata
            resp = self._request(f"{SWH_API}/content/sha1_git:{sha}/", throttle=True)
            data = resp.json()
            filename = data.get("data_url", sha).rsplit("/", 1)[-1]
            if not filename or filename == "raw/":
                filename = sha

        url = f"{SWH_API}/content/sha1_git:{sha}/raw/"
        filepath = os.path.join(folder, filename)
        self._download_content_raw(url, filepath)
        return 1

    def download(
        self,
        folder,
        throttle=False,
        download_data=True,
        show_progress=True,
        max_size_bytes=None,
        max_download_method="ordered",
        max_download_method_seed=None,
        download_skip_nogeo=False,
        download_skip_nogeo_exts=None,
        max_download_workers=4,
        **kwargs,
    ):
        """Download geospatial files from Software Heritage.

        Orchestrates: resolve identifier → list files → filter → download.
        """
        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        if not download_data:
            self.log.warning(
                "Software Heritage provider does not have geospatial metadata. "
                "Using download_data=False may result in limited or no spatial "
                "extent information. Consider using download_data=True.",
            )
            return

        # Special case: swh:1:cnt: — download single content object
        if self._swhid_type == "cnt":
            filename = self._qualifiers.get("path", "").rsplit("/", 1)[-1] or None
            self._download_single_content(folder, self._swhid_hash, filename)
            return

        # 1. Resolve to directory
        dir_sha, subpath = self._resolve_to_directory()

        # 2. List files (optionally from subpath)
        if subpath:
            self.log.debug("Resolving subpath '%s' in directory %s", subpath, dir_sha)
            entries = self._resolve_subpath(dir_sha, subpath)
            all_files = self._collect_entries(entries)
        else:
            all_files = self._list_files_recursive(dir_sha, "")

        self.log.info("Found %d files in Software Heritage archive", len(all_files))

        if not all_files:
            self.log.warning("No files found in Software Heritage archive")
            return

        # 3. Filter geospatial files
        file_list = [
            {"name": f["path"], "size": f.get("size", 0), "sha1_git": f["sha1_git"]}
            for f in all_files
        ]

        if download_skip_nogeo:
            file_list = self._filter_geospatial_files(
                file_list,
                skip_non_geospatial=True,
                additional_extensions=download_skip_nogeo_exts,
            )
        else:
            file_list = self._filter_geospatial_files(
                file_list,
                skip_non_geospatial=False,
                additional_extensions=download_skip_nogeo_exts,
            )

        # 4. Apply size filtering if specified
        if max_size_bytes is not None:
            selected_files, total_size, skipped_files = hf.filter_files_by_size(
                file_list,
                max_size_bytes,
                max_download_method,
                max_download_method_seed,
            )
            if not selected_files:
                self.log.warning("No files can be downloaded within the size limit")
                return
            file_list = selected_files
        else:
            total_size = sum(f.get("size", 0) for f in file_list)

        if not file_list:
            self.log.warning("No files selected for download after filtering")
            return

        # 5. Download files (sequential — SWH rate limits make parallel counterproductive)
        self.log.info(
            "Starting download of %d files from Software Heritage (%d bytes total)",
            len(file_list),
            total_size,
        )

        downloaded_count = 0
        for file_info in file_list:
            sha = file_info["sha1_git"]
            file_path = file_info["name"]
            url = f"{SWH_API}/content/sha1_git:{sha}/raw/"

            local_path = os.path.join(folder, file_path)

            try:
                self._download_content_raw(url, local_path)
                downloaded_count += 1
            except Exception as e:
                self.log.warning("Failed to download %s: %s", file_path, e)

        self.log.info(
            "Downloaded %d/%d files from Software Heritage",
            downloaded_count,
            len(file_list),
        )


def _parse_qualifiers(qualifier_string):
    """Parse SWHID qualifier string like ';origin=https://...;path=/foo'."""
    qualifiers = {}
    for part in qualifier_string.split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            qualifiers[key] = unquote(value)
    return qualifiers


def _quote_origin(origin_url):
    """URL-encode an origin URL for the SWH API path."""
    from urllib.parse import quote

    return quote(origin_url, safe="")
