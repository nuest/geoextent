import re
import os
import logging
from urllib.parse import urlparse
from .providers import DoiProvider
from .. import helpfunctions as hf

logger = logging.getLogger("geoextent")


class RADAR(DoiProvider):
    """Content provider for RADAR (Research Data Repository) by FIZ Karlsruhe.

    RADAR is a cross-disciplinary repository for archiving and publishing
    German research data. It assigns DOIs via DataCite (prefix 10.35097/)
    and delivers all datasets as .tar archives.

    Supports:
    - DOI prefix: 10.35097/
    - Hostnames: www.radar-service.eu, radar.kit.edu
    - Backend API for file metadata before download
    """

    doi_prefixes = ("10.35097/",)

    @classmethod
    def provider_info(cls):
        return {
            "name": "RADAR",
            "description": "RADAR (Research Data Repository) is a cross-disciplinary research data repository operated by FIZ Karlsruhe. It provides DOI assignment and long-term archiving for German research institutions.",
            "website": "https://www.radar-service.eu/",
            "supported_identifiers": [
                "https://www.radar-service.eu/radar/en/dataset/{doi}",
                "https://doi.org/10.35097/{id}",
                "10.35097/{id}",
            ],
            "doi_prefix": "10.35097",
            "examples": [
                "10.35097/1871",
            ],
        }

    RADAR_BASE = "https://www.radar-service.eu"

    def __init__(self):
        super().__init__()
        self.host = {
            "hostname": [
                "www.radar-service.eu",
                "radar-service.eu",
                "radar.kit.edu",
            ]
        }
        self.doi_pattern = re.compile(r"10\.35097/")
        self.record_id = None
        self.name = "RADAR"

    def validate_provider(self, reference):
        """Validate if the reference is a supported RADAR identifier.

        Args:
            reference (str): DOI, URL, or dataset identifier

        Returns:
            bool: True if valid RADAR reference, False otherwise
        """
        self.reference = reference

        # Check for RADAR DOI prefix
        if self.doi_pattern.search(reference):
            return True

        # Check for RADAR hostnames in URL
        try:
            parsed = urlparse(reference)
            hostname = parsed.hostname or ""
        except Exception:
            hostname = ""

        if any(
            hostname == h or hostname.endswith("." + h) for h in self.host["hostname"]
        ):
            # Extract record ID from URL path
            # Patterns: /radar/en/dataset/{id}, /radar/de/dataset/{id}
            dataset_match = re.search(r"/radar/(?:en|de)/dataset/([^/?#]+)", reference)
            if dataset_match:
                self.record_id = dataset_match.group(1)
                return True

            # Pattern: /radar-backend/archives/{id}
            backend_match = re.search(r"/radar-backend/archives/([^/?#/]+)", reference)
            if backend_match:
                self.record_id = backend_match.group(1)
                return True

            # Accept any URL on RADAR hosts
            return True

        return False

    def _resolve_record_id(self):
        """Resolve the RADAR record ID from the reference if not already set."""
        if self.record_id:
            return self.record_id

        # If we have a DOI, resolve it to get the landing page URL
        url = self.get_url

        # Try to extract record ID from the resolved URL
        dataset_match = re.search(r"/radar/(?:en|de)/dataset/([^/?#]+)", url)
        if dataset_match:
            self.record_id = dataset_match.group(1)
            return self.record_id

        backend_match = re.search(r"/radar-backend/archives/([^/?#/]+)", url)
        if backend_match:
            self.record_id = backend_match.group(1)
            return self.record_id

        # Fallback: try the last path segment from the DOI suffix
        doi_match = re.search(r"10\.35097/([^\s]+)", self.reference)
        if doi_match:
            self.record_id = doi_match.group(1)
            return self.record_id

        raise ValueError(f"Could not resolve RADAR record ID from: {self.reference}")

    def _get_file_metadata(self):
        """Fetch file metadata from the RADAR backend API.

        Returns:
            tuple: (file_list, archive_version) where file_list is a list of
                   dicts with 'name' and 'size' keys, and archive_version is
                   the version string needed for the download URL.
        """
        record_id = self._resolve_record_id()
        api_url = f"{self.RADAR_BASE}/radar-backend/archives/{record_id}"

        logger.debug(f"Fetching RADAR file metadata from: {api_url}")
        response = self._request(api_url, headers={"Accept": "application/json"})
        response.raise_for_status()
        data = response.json()

        # API returns a flat array of file entries
        if isinstance(data, list):
            files = data
        else:
            files = data.get("files", [])

        archive_version = None
        file_list = []

        for f in files:
            file_list.append(
                {
                    "name": f.get("path", f.get("fileName", "")),
                    "size": f.get("size", 0),
                }
            )
            # All files share the same archive_version
            if archive_version is None:
                archive_version = f.get("archive_version") or f.get("archiveVersion")

        logger.debug(
            f"RADAR metadata: {len(file_list)} files, version={archive_version}"
        )
        return file_list, archive_version

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
    ):
        """Download data from RADAR.

        RADAR delivers all datasets as a single .tar archive.

        Args:
            folder (str): Target directory for downloads
            throttle (bool): Whether to throttle requests
            download_data (bool): Whether to download actual data
            show_progress (bool): Whether to show progress bars
            max_size_bytes (int): Maximum download size in bytes
            max_download_method (str): Method for size-limited downloads
            max_download_method_seed (int): Seed for random sampling
            download_skip_nogeo (bool): Skip if no geospatial files found
            download_skip_nogeo_exts (set): Additional geospatial extensions
            max_download_workers (int): Number of parallel download workers

        Returns:
            str: Path to downloaded data directory
        """
        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        logger.info(f"Downloading from RADAR: {self.reference}")

        if not download_data:
            logger.warning(
                "RADAR provider does not support metadata-only extraction. "
                "Using download_data=False will return no spatial extent information."
            )
            return folder

        # Fetch file metadata from backend API
        try:
            file_list, archive_version = self._get_file_metadata()
        except Exception as e:
            logger.error(f"Error fetching RADAR file metadata: {e}")
            raise

        # Check if archive contains geospatial files based on backend file listing
        if download_skip_nogeo and file_list:
            geo_files = [
                f
                for f in file_list
                if self._is_geospatial_file(f["name"], download_skip_nogeo_exts)
            ]
            if not geo_files:
                logger.warning(
                    "RADAR archive contains no geospatial files based on file "
                    "metadata. Skipping download (--download-skip-nogeo is enabled)."
                )
                return folder

        # Check total archive size against limit
        total_size = sum(f.get("size", 0) for f in file_list)
        if (
            max_size_bytes is not None
            and total_size > 0
            and total_size > max_size_bytes
        ):
            if getattr(self, "_download_size_soft_limit", False):
                from ..exceptions import DownloadSizeExceeded

                raise DownloadSizeExceeded(total_size, max_size_bytes, self.name)
            logger.warning(
                f"RADAR archive ({total_size:,} bytes) exceeds size limit "
                f"({max_size_bytes:,} bytes). Skipping download."
            )
            return folder

        # Build download URL
        record_id = self._resolve_record_id()
        if archive_version is not None:
            download_url = (
                f"{self.RADAR_BASE}/radar-backend/archives/{record_id}"
                f"/versions/{archive_version}/content"
            )
        else:
            # Fallback without version
            download_url = (
                f"{self.RADAR_BASE}/radar-backend/archives/{record_id}/content"
            )

        logger.debug(f"RADAR download URL: {download_url}")

        # Create target directory
        folder_name = f"radar_{record_id}"
        download_dir = os.path.join(folder, folder_name)
        os.makedirs(download_dir, exist_ok=True)

        # Download the tar archive
        tar_filename = f"{record_id}.tar"
        tar_path = os.path.join(download_dir, tar_filename)

        try:
            self._download_file_optimized(
                download_url, tar_path, show_progress=show_progress
            )
            logger.info(f"Downloaded RADAR archive to: {tar_path}")
        except Exception as e:
            logger.error(f"Error downloading RADAR archive: {e}")
            raise

        return download_dir
