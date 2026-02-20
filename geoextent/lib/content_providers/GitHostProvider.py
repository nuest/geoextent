"""
Base class for git hosting platform content providers.

Provides a shared download orchestration for git platforms (GitHub, GitLab, etc.):
1. Parse URL → owner/repo/ref/path
2. Resolve ref if not specified (→ default branch, 1 API call)
3. List files in repo/path (1 API call)
4. Filter geospatial files using inherited _filter_geospatial_files()
5. Construct download URLs
6. Download files preserving directory structure

Subclasses implement four abstract methods:
- _parse_reference(url) → dict
- _get_default_branch(owner, repo) → str
- _list_files(owner, repo, ref, path) → list[dict]
- _get_raw_url(owner, repo, ref, path) → str
"""

import logging
import os
from abc import abstractmethod

from geoextent.lib import helpfunctions as hf
from geoextent.lib.content_providers.providers import DoiProvider

logger = logging.getLogger("geoextent")


class GitHostProvider(DoiProvider):
    """Abstract base class for git hosting platform content providers."""

    # Git hosts are not DOI-based
    doi_prefixes = ()

    @property
    def supports_metadata_extraction(self):
        """Git hosts have no structured spatial metadata."""
        return False

    @abstractmethod
    def _parse_reference(self, url):
        """Parse a repository URL into components.

        Returns:
            dict with keys: owner, repo, ref (may be None), path (may be None)
        """

    @abstractmethod
    def _get_default_branch(self, owner, repo):
        """Fetch the default branch name from the API.

        Returns:
            str: branch name (e.g. "main", "master")
        """

    @abstractmethod
    def _list_files(self, owner, repo, ref, path=None):
        """List files in repository (or subdirectory).

        Returns:
            list of dict, each with keys: path, size, type
            Only blobs (files) should be returned.
        """

    @abstractmethod
    def _get_raw_url(self, owner, repo, ref, path):
        """Construct a raw file download URL (no API call).

        Returns:
            str: URL to download the file content
        """

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
        """Download geospatial files from a git repository.

        Orchestrates: parse URL → resolve ref → list files → filter → download.
        Preserves directory structure so co-located files (e.g. shapefile
        components) remain together.
        """
        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        if not download_data:
            self.log.warning(
                "%s provider does not have geospatial metadata. "
                "Using download_data=False may result in limited or no spatial "
                "extent information. Consider using download_data=True.",
                self.name,
            )
            return

        # 1. Parse URL
        parsed = self._parse_reference(self.reference)
        owner = parsed["owner"]
        repo = parsed["repo"]
        ref = parsed.get("ref")
        subpath = parsed.get("path")

        # 2. Resolve ref if not specified
        if not ref:
            ref = self._get_default_branch(owner, repo)
            self.log.debug("Resolved default branch: %s", ref)

        # 3. List files
        self.log.debug("Listing files in %s/%s@%s path=%s", owner, repo, ref, subpath)
        all_files = self._list_files(owner, repo, ref, subpath)
        self.log.info("Found %d files in %s/%s", len(all_files), owner, repo)

        if not all_files:
            self.log.warning("No files found in %s/%s", owner, repo)
            return

        # 4. Filter geospatial files
        # Build file list in the format expected by _filter_geospatial_files
        file_list = [{"name": f["path"], "size": f.get("size", 0)} for f in all_files]

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

        # 5. Apply size filtering if specified
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

        # 6. Download files preserving directory structure
        # Strip common subpath prefix so files are relative to the target dir
        strip_prefix = (subpath + "/") if subpath else ""

        self.log.info(
            "Starting download of %d files from %s/%s (%d bytes total)",
            len(file_list),
            owner,
            repo,
            total_size,
        )

        downloaded_count = 0
        for file_info in file_list:
            file_path = file_info["name"]
            url = self._get_raw_url(owner, repo, ref, file_path)

            # Build local path preserving directory structure
            relative_path = file_path
            if strip_prefix and relative_path.startswith(strip_prefix):
                relative_path = relative_path[len(strip_prefix) :]

            local_path = os.path.join(folder, relative_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            try:
                self._download_file_optimized(url, local_path)
                downloaded_count += 1
            except Exception as e:
                self.log.warning("Failed to download %s: %s", file_path, e)

        self.log.info(
            "Downloaded %d/%d files from %s/%s",
            downloaded_count,
            len(file_list),
            owner,
            repo,
        )
