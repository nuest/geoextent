import logging
import os
import re
import tempfile
from requests import HTTPError
from .providers import DoiProvider
from .. import helpfunctions as hf


class OSF(DoiProvider):
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
        from osfclient import OSF as OSFClient
        from tqdm import tqdm

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

    def _get_file_metadata_via_api(self):
        """Get file metadata from OSF API without downloading"""
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

            # Recursively collect all files with metadata
            def collect_files_recursive(url, path_prefix=""):
                files = []
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()

                for item in data.get("data", []):
                    attributes = item.get("attributes", {})
                    kind = attributes.get("kind")
                    name = attributes.get("name", "")

                    if kind == "file":
                        file_size = attributes.get("size", 0)
                        download_url = item.get("links", {}).get("download")
                        full_path = (
                            os.path.join(path_prefix, name) if path_prefix else name
                        )

                        if download_url:
                            files.append(
                                {
                                    "name": full_path,
                                    "url": download_url,
                                    "size": file_size,
                                }
                            )
                    elif (
                        kind == "folder"
                        and "relationships" in item
                        and "files" in item["relationships"]
                    ):
                        # Recursively explore folders
                        folder_url = item["relationships"]["files"]["links"]["related"][
                            "href"
                        ]
                        folder_path = (
                            os.path.join(path_prefix, name) if path_prefix else name
                        )
                        files.extend(collect_files_recursive(folder_url, folder_path))

                return files

            # Start collection from osfstorage
            all_files = []
            storage_providers = data.get("data", [])

            for storage_provider in storage_providers:
                if storage_provider.get("attributes", {}).get("name") == "osfstorage":
                    storage_url = (
                        storage_provider.get("relationships", {})
                        .get("files", {})
                        .get("links", {})
                        .get("related", {})
                        .get("href")
                    )
                    if storage_url:
                        all_files.extend(collect_files_recursive(storage_url))

            self.log.debug(
                f"Found {len(all_files)} files in OSF project {self.project_id}"
            )
            return all_files

        except requests.RequestException as e:
            raise Exception(f"Failed to get file metadata via OSF API: {e}")

    def _get_files_via_api(self, target_folder, show_progress=True, file_list=None):
        """Download files via OSF API with optional pre-filtered file list"""
        if file_list is None:
            # Get all files if no pre-filtered list provided
            file_list = self._get_file_metadata_via_api()

        if not file_list:
            self.log.warning(
                f"No downloadable files found in OSF project {self.project_id}"
            )
            return []

        # Download files with progress tracking
        downloaded_files = []
        total_size = sum(f["size"] for f in file_list)

        # Log download summary before starting
        self.log.info(
            f"Starting download of {len(file_list)} files from OSF project {self.project_id} ({total_size:,} bytes total)"
        )

        # Use the batch download method from parent class
        if hasattr(self, "_download_files_batch"):
            results = self._download_files_batch(
                file_list, target_folder, show_progress=show_progress, max_workers=4
            )
            downloaded_files = [
                os.path.join(target_folder, f["name"]) for f in file_list
            ]
        else:
            # Fallback to sequential download
            from tqdm import tqdm

            if show_progress:
                pbar = tqdm(
                    total=total_size,
                    desc=f"Downloading OSF files from {self.project_id}",
                    unit="B",
                    unit_scale=True,
                )

            try:
                for file_info in file_list:
                    file_name = file_info["name"]
                    download_url = file_info["url"]
                    local_path = os.path.join(target_folder, file_name)

                    # Create directories if needed
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)

                    if show_progress:
                        pbar.set_postfix_str(
                            f"Downloading {os.path.basename(file_name)}"
                        )

                    # Download file
                    import requests

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

    def download(
        self,
        target_folder,
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
        """
        Extract geospatial metadata from OSF project.

        Parameters:
        - target_folder: Directory to store files
        - throttle: Rate limiting for API calls (not used for OSF)
        - download_data: If True, downloads actual data files for local extraction.
                        If False, attempts metadata-only extraction (limited for OSF).
        """
        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        self.throttle = throttle

        # OSF now supports selective file filtering!

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
            # Get file metadata first via API (more reliable than osfclient for metadata)
            self.log.debug(
                f"Retrieving file metadata for OSF project {self.project_id}"
            )

            try:
                all_files = self._get_file_metadata_via_api()
            except Exception as metadata_error:
                self.log.warning(f"Failed to get metadata via API: {metadata_error}")
                # Fallback to osfclient without filtering
                try:
                    if download_skip_nogeo:
                        self.log.warning(
                            "Cannot apply geospatial filtering without file metadata. "
                            "Downloading all files via osfclient."
                        )
                    downloaded_files = self._get_files_via_osfclient(
                        target_folder, show_progress
                    )
                    self.log.info(
                        f"OSF data downloaded via osfclient for project {self.project_id}"
                    )
                    return
                except Exception as osfclient_error:
                    raise Exception(
                        f"Both API metadata and osfclient failed: {metadata_error}, {osfclient_error}"
                    )

            if not all_files:
                self.log.warning(f"No files found in OSF project {self.project_id}")
                return

            # Apply filtering if requested
            file_info = all_files
            total_size = sum(f.get("size", 0) for f in file_info)

            # Apply geospatial filtering if requested
            if download_skip_nogeo:
                filtered_files = self._filter_geospatial_files(
                    file_info,
                    skip_non_geospatial=download_skip_nogeo,
                    max_size_mb=None,  # Don't apply size limit here
                    additional_extensions=download_skip_nogeo_exts,
                )
            else:
                filtered_files = file_info

            # Apply size filtering if specified
            if max_size_bytes is not None:
                selected_files, filtered_total_size, skipped_files = (
                    hf.filter_files_by_size(
                        filtered_files,
                        max_size_bytes,
                        max_download_method,
                        max_download_method_seed,
                    )
                )
                if not selected_files:
                    self.log.warning("No files can be downloaded within the size limit")
                    return
                file_info = selected_files
                total_size = filtered_total_size
            else:
                file_info = filtered_files
                total_size = sum(f.get("size", 0) for f in file_info)

            if not file_info:
                self.log.warning(f"No files selected for download after filtering")
                return

            # Download the filtered files
            try:
                # Try API download first (more control over individual files)
                downloaded_files = self._get_files_via_api(
                    target_folder, show_progress, file_info
                )
                self.log.info(
                    f"OSF data downloaded via API for project {self.project_id}"
                )
            except Exception as api_error:
                self.log.warning(f"API download failed: {api_error}, trying osfclient")
                # Fallback to osfclient (but we lose filtering)
                if file_info != all_files:
                    self.log.warning(
                        "File filtering will be lost when using osfclient fallback. "
                        "All files in the project will be downloaded."
                    )
                downloaded_files = self._get_files_via_osfclient(
                    target_folder, show_progress
                )
                self.log.info(
                    f"OSF data downloaded via osfclient for project {self.project_id}"
                )

            if not downloaded_files:
                self.log.warning(
                    f"No files downloaded from OSF project {self.project_id}"
                )

        except Exception as e:
            self.log.error(f"Error processing OSF project: {e}")
            raise
