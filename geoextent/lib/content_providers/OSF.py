import logging
import os
import re
import tempfile
from requests import HTTPError
from .providers import ContentProvider


class OSF(ContentProvider):
    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("geoextent")
        self.host = {
            "hostname": [
                "https://osf.io/",
                "http://osf.io/",
            ],
            "api": "https://api.osf.io/v2/nodes/",
        }
        self.reference = None
        self.project_id = None
        self.name = "OSF"
        self.throttle = False

    def validate_provider(self, reference):
        """Validate if the reference is an OSF project URL or DOI"""
        self.reference = reference

        # Check for DOI resolver URLs (https://doi.org/, http://dx.doi.org/, etc.)
        doi_url_patterns = [
            r"^https?://(?:dx\.)?doi\.org/10\.17605/OSF\.IO/([A-Z0-9]{5})/?(?:[?#].*)?$",
            r"^https?://(?:www\.)?doi\.org/10\.17605/OSF\.IO/([A-Z0-9]{5})/?(?:[?#].*)?$",
        ]

        for pattern in doi_url_patterns:
            doi_url_match = re.search(pattern, reference, re.IGNORECASE)
            if doi_url_match:
                self.project_id = doi_url_match.group(1).lower()
                return True

        # Check for bare OSF DOI pattern: 10.17605/OSF.IO/PROJECT_ID (various capitalizations)
        bare_doi_patterns = [
            r"^10\.17605/OSF\.IO/([A-Z0-9]{5})$",  # Standard case
            r"^10\.17605/osf\.io/([A-Z0-9]{5})$",  # Lowercase osf.io
            r"^10\.17605/Osf\.Io/([A-Z0-9]{5})$",  # Mixed case
        ]

        for pattern in bare_doi_patterns:
            doi_match = re.search(pattern, reference, re.IGNORECASE)
            if doi_match:
                self.project_id = doi_match.group(1).lower()
                return True

        # Check for plain OSF identifiers without protocol: OSF.IO/PROJECT_ID (various capitalizations)
        plain_osf_patterns = [
            r"^OSF\.IO/([A-Z0-9]{5})$",  # Standard case: OSF.IO/9JG2U
            r"^osf\.io/([A-Z0-9]{5})$",  # Lowercase: osf.io/9jg2u
            r"^Osf\.Io/([A-Z0-9]{5})$",  # Mixed case: Osf.Io/9JG2U
        ]

        for pattern in plain_osf_patterns:
            plain_match = re.search(pattern, reference, re.IGNORECASE)
            if plain_match:
                self.project_id = plain_match.group(1).lower()
                return True

        # Check for direct OSF URLs
        osf_url_pattern = re.compile(
            r"https?://osf\.io/([A-Z0-9]{5})/?(?:[?#].*)?$", re.IGNORECASE
        )
        url_match = osf_url_pattern.search(reference)
        if url_match:
            self.project_id = url_match.group(1).lower()
            return True

        # Check for direct project ID (5 character alphanumeric)
        if re.match(r"^[A-Z0-9]{5}$", reference, re.IGNORECASE):
            self.project_id = reference.lower()
            return True

        return False

    def _get_metadata_via_api(self):
        """Get project metadata via OSF API v2"""
        if not self.project_id:
            raise Exception("No project ID available for API metadata extraction")

        import requests

        api_url = f"{self.host['api']}{self.project_id}/"
        self.log.debug(f"Fetching OSF metadata from {api_url}")

        try:
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            data = response.json()

            return {
                "title": data.get("data", {}).get("attributes", {}).get("title"),
                "description": data.get("data", {})
                .get("attributes", {})
                .get("description"),
                "public": data.get("data", {}).get("attributes", {}).get("public"),
                "date_created": data.get("data", {})
                .get("attributes", {})
                .get("date_created"),
                "date_modified": data.get("data", {})
                .get("attributes", {})
                .get("date_modified"),
            }
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch OSF API metadata: {e}")

    def _get_files_via_osfclient(self, target_folder, show_progress=True):
        """Download files using osfclient library"""
        try:
            from osfclient import OSF as OSFClient
            from tqdm import tqdm
        except ImportError:
            raise Exception(
                "osfclient library is required for OSF support. Install with: pip install osfclient"
            )

        try:
            # Initialize OSF client (no authentication needed for public projects)
            osf = OSFClient()

            # Get the project
            project = osf.project(self.project_id)

            # Get the main storage
            storage = project.storage("osfstorage")

            # First count the files to set up progress bar
            files_list = list(storage.files)
            total_files = len([f for f in files_list if hasattr(f, "name")])

            if total_files == 0:
                self.log.warning(f"No files found in OSF project {self.project_id}")
                return []

            # Log download summary before starting
            self.log.info(
                f"Starting download of {total_files} files from OSF project {self.project_id}"
            )

            # Download all files with progress bar
            downloaded_files = []
            if show_progress:
                pbar = tqdm(
                    total=total_files,
                    desc=f"Downloading OSF files from {self.project_id}",
                    unit="file",
                )

            try:
                for file_obj in files_list:
                    if hasattr(file_obj, "name"):
                        local_path = os.path.join(target_folder, file_obj.name)

                        # Create directories if needed
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)

                        # Download file with progress update
                        if show_progress:
                            pbar.set_postfix_str(f"Downloading {file_obj.name}")
                        with open(local_path, "wb") as fp:
                            file_obj.write_to(fp)

                        downloaded_files.append(local_path)
                        self.log.debug(f"Downloaded OSF file: {file_obj.name}")
                        if show_progress:
                            pbar.update(1)
            finally:
                if show_progress:
                    pbar.close()

            self.log.info(
                f"Downloaded {len(downloaded_files)} files from OSF project {self.project_id}"
            )
            return downloaded_files

        except Exception as e:
            self.log.error(f"Error using osfclient: {e}")
            raise Exception(f"Failed to download OSF files via osfclient: {e}")

    def _get_files_via_api(self, target_folder, show_progress=True):
        """Fallback method to get file list via OSF API"""
        if not self.project_id:
            raise Exception("No project ID available")

        import requests
        from tqdm import tqdm

        files_url = f"{self.host['api']}{self.project_id}/files/"
        self.log.debug(f"Fetching file list from {files_url}")

        try:
            response = requests.get(files_url, timeout=30)
            response.raise_for_status()
            data = response.json()

            # First pass: collect all downloadable files with progress tracking
            downloadable_files = []
            storage_providers = data.get("data", [])

            if show_progress:
                metadata_pbar = tqdm(
                    total=len(storage_providers),
                    desc=f"Processing OSF metadata for {self.project_id}",
                    unit="provider",
                    leave=False,
                )

            try:
                for storage_provider in storage_providers:
                    if (
                        storage_provider.get("attributes", {}).get("name")
                        == "osfstorage"
                    ):
                        # Get files from osfstorage
                        storage_url = (
                            storage_provider.get("relationships", {})
                            .get("files", {})
                            .get("links", {})
                            .get("related", {})
                            .get("href")
                        )
                        if storage_url:
                            if show_progress:
                                metadata_pbar.set_postfix_str("Fetching file list")
                            files_response = requests.get(storage_url, timeout=30)
                            files_response.raise_for_status()
                            files_data = files_response.json()

                            file_count = 0
                            for file_info in files_data.get("data", []):
                                if (
                                    file_info.get("attributes", {}).get("kind")
                                    == "file"
                                ):
                                    file_name = file_info.get("attributes", {}).get(
                                        "name"
                                    )
                                    download_url = file_info.get("links", {}).get(
                                        "download"
                                    )
                                    file_size = file_info.get("attributes", {}).get(
                                        "size", 0
                                    )

                                    if file_name and download_url:
                                        downloadable_files.append(
                                            {
                                                "name": file_name,
                                                "url": download_url,
                                                "size": file_size,
                                            }
                                        )
                                        file_count += 1

                            if show_progress:
                                metadata_pbar.set_postfix_str(
                                    f"Found {file_count} files"
                                )
                    if show_progress:
                        metadata_pbar.update(1)

            finally:
                if show_progress:
                    metadata_pbar.close()

            if not downloadable_files:
                self.log.warning(
                    f"No downloadable files found in OSF project {self.project_id}"
                )
                return []

            # Second pass: download files with progress tracking
            downloaded_files = []
            total_size = sum(f["size"] for f in downloadable_files)

            # Log download summary before starting
            self.log.info(
                f"Starting download of {len(downloadable_files)} files from OSF project {self.project_id} ({total_size:,} bytes total)"
            )

            if show_progress:
                pbar = tqdm(
                    total=total_size,
                    desc=f"Downloading OSF files from {self.project_id}",
                    unit="B",
                    unit_scale=True,
                )

            try:
                for file_info in downloadable_files:
                    file_name = file_info["name"]
                    download_url = file_info["url"]
                    local_path = os.path.join(target_folder, file_name)

                    if show_progress:
                        pbar.set_postfix_str(f"Downloading {file_name}")

                    # Download file
                    file_response = requests.get(download_url, timeout=30, stream=True)
                    file_response.raise_for_status()

                    with open(local_path, "wb") as f:
                        for chunk in file_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                if show_progress:
                                    pbar.update(len(chunk))

                    downloaded_files.append(local_path)
                    self.log.debug(f"Downloaded OSF file via API: {file_name}")

            finally:
                if show_progress:
                    pbar.close()

            self.log.info(
                f"Downloaded {len(downloaded_files)} files from OSF project {self.project_id}"
            )
            return downloaded_files

        except requests.RequestException as e:
            raise Exception(f"Failed to download files via OSF API: {e}")

    def download(
        self, target_folder, throttle=False, download_data=True, show_progress=True
    ):
        """
        Extract geospatial metadata from OSF project.

        Parameters:
        - target_folder: Directory to store files
        - throttle: Rate limiting for API calls (not used for OSF)
        - download_data: If True, downloads actual data files for local extraction.
                        If False, attempts metadata-only extraction (limited for OSF).
        """
        self.throttle = throttle

        if not download_data:
            self.log.warning(
                "OSF provider has limited metadata-only extraction capabilities. "
                "Using download_data=False may result in incomplete spatial extent information. "
                "Consider using download_data=True to download actual data files for better geospatial extraction."
            )
            # For metadata-only mode, we can only get basic project info
            try:
                metadata = self._get_metadata_via_api()
                self.log.info(f"OSF metadata extracted for project {self.project_id}")
                return
            except Exception as e:
                self.log.error(f"Failed to extract OSF metadata: {e}")
                raise

        try:
            # First try osfclient for file download
            try:
                downloaded_files = self._get_files_via_osfclient(
                    target_folder, show_progress
                )
                self.log.info(
                    f"OSF data downloaded via osfclient for project {self.project_id}"
                )
            except Exception as osfclient_error:
                self.log.warning(
                    f"osfclient failed: {osfclient_error}, trying API fallback"
                )
                downloaded_files = self._get_files_via_api(target_folder, show_progress)
                self.log.info(
                    f"OSF data downloaded via API for project {self.project_id}"
                )

            if not downloaded_files:
                self.log.warning(
                    f"No files downloaded from OSF project {self.project_id}"
                )

        except Exception as e:
            self.log.error(f"Error processing OSF project: {e}")
            raise
