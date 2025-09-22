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
        osf_url_pattern = re.compile(r"https?://osf\.io/([A-Z0-9]{5})/?(?:[?#].*)?$", re.IGNORECASE)
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
                "description": data.get("data", {}).get("attributes", {}).get("description"),
                "public": data.get("data", {}).get("attributes", {}).get("public"),
                "date_created": data.get("data", {}).get("attributes", {}).get("date_created"),
                "date_modified": data.get("data", {}).get("attributes", {}).get("date_modified"),
            }
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch OSF API metadata: {e}")

    def _get_files_via_osfclient(self, target_folder):
        """Download files using osfclient library"""
        try:
            from osfclient import OSF as OSFClient
        except ImportError:
            raise Exception("osfclient library is required for OSF support. Install with: pip install osfclient")

        try:
            # Initialize OSF client (no authentication needed for public projects)
            osf = OSFClient()

            # Get the project
            project = osf.project(self.project_id)

            # Get the main storage
            storage = project.storage('osfstorage')

            # Download all files
            downloaded_files = []
            for file_obj in storage.files:
                if hasattr(file_obj, 'name'):
                    local_path = os.path.join(target_folder, file_obj.name)

                    # Create directories if needed
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)

                    # Download file
                    with open(local_path, 'wb') as fp:
                        file_obj.write_to(fp)

                    downloaded_files.append(local_path)
                    self.log.debug(f"Downloaded OSF file: {file_obj.name}")

            return downloaded_files

        except Exception as e:
            self.log.error(f"Error using osfclient: {e}")
            raise Exception(f"Failed to download OSF files via osfclient: {e}")

    def _get_files_via_api(self, target_folder):
        """Fallback method to get file list via OSF API"""
        if not self.project_id:
            raise Exception("No project ID available")

        import requests

        files_url = f"{self.host['api']}{self.project_id}/files/"
        self.log.debug(f"Fetching file list from {files_url}")

        try:
            response = requests.get(files_url, timeout=30)
            response.raise_for_status()
            data = response.json()

            downloaded_files = []
            for storage_provider in data.get("data", []):
                if storage_provider.get("attributes", {}).get("name") == "osfstorage":
                    # Get files from osfstorage
                    storage_url = storage_provider.get("relationships", {}).get("files", {}).get("links", {}).get("related", {}).get("href")
                    if storage_url:
                        files_response = requests.get(storage_url, timeout=30)
                        files_response.raise_for_status()
                        files_data = files_response.json()

                        for file_info in files_data.get("data", []):
                            if file_info.get("attributes", {}).get("kind") == "file":
                                file_name = file_info.get("attributes", {}).get("name")
                                download_url = file_info.get("links", {}).get("download")

                                if file_name and download_url:
                                    local_path = os.path.join(target_folder, file_name)

                                    # Download file
                                    file_response = requests.get(download_url, timeout=30, stream=True)
                                    file_response.raise_for_status()

                                    with open(local_path, 'wb') as f:
                                        for chunk in file_response.iter_content(chunk_size=8192):
                                            f.write(chunk)

                                    downloaded_files.append(local_path)
                                    self.log.debug(f"Downloaded OSF file via API: {file_name}")

            return downloaded_files

        except requests.RequestException as e:
            raise Exception(f"Failed to download files via OSF API: {e}")

    def download(self, target_folder, throttle=False, download_data=True):
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
                downloaded_files = self._get_files_via_osfclient(target_folder)
                self.log.info(f"OSF data downloaded via osfclient for project {self.project_id}")
            except Exception as osfclient_error:
                self.log.warning(f"osfclient failed: {osfclient_error}, trying API fallback")
                downloaded_files = self._get_files_via_api(target_folder)
                self.log.info(f"OSF data downloaded via API for project {self.project_id}")

            if not downloaded_files:
                self.log.warning(f"No files downloaded from OSF project {self.project_id}")

        except Exception as e:
            self.log.error(f"Error processing OSF project: {e}")
            raise