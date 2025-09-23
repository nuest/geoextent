import logging
import os
import re
import tempfile
from requests import HTTPError
from .providers import ContentProvider

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class Mendeley(ContentProvider):
    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("geoextent")
        self.host = {
            "hostname": [
                "https://data.mendeley.com/",
                "http://data.mendeley.com/",
            ],
            "api": "https://data.mendeley.com/api/datasets/",
        }
        self.reference = None
        self.dataset_id = None
        self.version = None
        self.name = "Mendeley"
        self.throttle = False

    def validate_provider(self, reference):
        """Validate if the reference is a Mendeley dataset URL or DOI"""
        self.reference = reference

        # Check for DOI resolver URLs pointing to Mendeley Data
        # Example: https://doi.org/10.17632/ybx6zp2rfp.1
        doi_url_patterns = [
            r"^https?://(?:dx\.)?doi\.org/10\.17632/([a-z0-9]+)\.(\d+)/?(?:[?#].*)?$",
            r"^https?://(?:www\.)?doi\.org/10\.17632/([a-z0-9]+)\.(\d+)/?(?:[?#].*)?$",
        ]

        for pattern in doi_url_patterns:
            doi_url_match = re.search(pattern, reference, re.IGNORECASE)
            if doi_url_match:
                self.dataset_id = doi_url_match.group(1).lower()
                self.version = doi_url_match.group(2)
                return True

        # Check for bare Mendeley DOI pattern: 10.17632/DATASET_ID.VERSION
        bare_doi_pattern = r"^10\.17632/([a-z0-9]+)\.(\d+)$"
        doi_match = re.search(bare_doi_pattern, reference, re.IGNORECASE)
        if doi_match:
            self.dataset_id = doi_match.group(1).lower()
            self.version = doi_match.group(2)
            return True

        # Check for direct Mendeley Data URLs
        # Example: https://data.mendeley.com/datasets/ybx6zp2rfp/1
        mendeley_url_pattern = r"^https?://data\.mendeley\.com/datasets/([a-z0-9]+)/(\d+)/?(?:[?#].*)?$"
        url_match = re.search(mendeley_url_pattern, reference, re.IGNORECASE)
        if url_match:
            self.dataset_id = url_match.group(1).lower()
            self.version = url_match.group(2)
            return True

        # Check for dataset ID with version (e.g., "ybx6zp2rfp.1" or "ybx6zp2rfp/1")
        id_version_patterns = [
            r"^([a-z0-9]+)\.(\d+)$",  # ybx6zp2rfp.1
            r"^([a-z0-9]+)/(\d+)$",   # ybx6zp2rfp/1
        ]

        for pattern in id_version_patterns:
            id_match = re.search(pattern, reference, re.IGNORECASE)
            if id_match:
                self.dataset_id = id_match.group(1).lower()
                self.version = id_match.group(2)
                return True

        # Check for bare dataset ID (assume latest version)
        # Mendeley dataset IDs are typically 10 characters: alphanumeric
        if re.match(r"^[a-z0-9]{10}$", reference, re.IGNORECASE):
            self.dataset_id = reference.lower()
            self.version = None  # Will use latest version
            return True

        return False

    def _get_metadata_via_oai_pmh(self):
        """Get dataset metadata via OAI-PMH (public access)"""
        if not self.dataset_id:
            raise Exception("No dataset ID available for metadata extraction")

        import requests
        from xml.etree import ElementTree as ET

        # Construct OAI-PMH identifier
        # Mendeley OAI-PMH identifiers follow pattern: oai:data.mendeley.com:datasets/DATASET_ID/VERSION
        if self.version:
            oai_identifier = f"oai:data.mendeley.com:datasets/{self.dataset_id}/{self.version}"
        else:
            oai_identifier = f"oai:data.mendeley.com:datasets/{self.dataset_id}"

        oai_url = "https://data.mendeley.com/oai"
        params = {
            "verb": "GetRecord",
            "identifier": oai_identifier,
            "metadataPrefix": "oai_dc"
        }

        self.log.debug(f"Fetching Mendeley metadata from OAI-PMH: {oai_url}")

        try:
            response = requests.get(oai_url, params=params, timeout=30)
            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.content)

            # Find Dublin Core metadata
            dc_elements = {}
            for elem in root.iter():
                if elem.tag.startswith('{http://purl.org/dc/elements/1.1/}'):
                    tag_name = elem.tag.split('}')[1]
                    if tag_name not in dc_elements:
                        dc_elements[tag_name] = []
                    dc_elements[tag_name].append(elem.text)

            return {
                "title": dc_elements.get("title", [None])[0],
                "description": dc_elements.get("description", [None])[0],
                "creator": dc_elements.get("creator", []),
                "date": dc_elements.get("date", [None])[0],
                "identifier": dc_elements.get("identifier", []),
                "subject": dc_elements.get("subject", []),
                "type": dc_elements.get("type", [None])[0],
            }
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch Mendeley OAI-PMH metadata: {e}")
        except ET.ParseError as e:
            raise Exception(f"Failed to parse Mendeley OAI-PMH response: {e}")

    def _get_download_url_from_page(self):
        """Extract download information from the Mendeley dataset landing page"""
        import requests
        import re
        import json

        version = self.version or "1"
        page_url = f"https://data.mendeley.com/datasets/{self.dataset_id}/{version}"

        self.log.debug(f"Fetching Mendeley landing page: {page_url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        try:
            response = requests.get(page_url, headers=headers, timeout=30)
            response.raise_for_status()

            # Extract the initial state JSON which contains API endpoints and dataset info
            page_text = response.text

            # Look for window.INITIAL_STATE JSON data
            # We need to find the opening brace and match to the corresponding closing brace
            initial_state_start = page_text.find('window.INITIAL_STATE = {')
            if initial_state_start != -1:
                # Find the opening brace
                json_start = page_text.find('{', initial_state_start)
                if json_start != -1:
                    # Count braces to find the matching closing brace
                    brace_count = 0
                    json_end = json_start
                    for i, char in enumerate(page_text[json_start:], json_start):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break

                    if brace_count == 0:  # Found matching closing brace
                        try:
                            initial_state_json = page_text[json_start:json_end]
                            initial_state = json.loads(initial_state_json)
                            self.log.debug(f"Extracted INITIAL_STATE from page")

                            # Get API base URLs from the config
                            config_client = initial_state.get('configClient', {})
                            api_base_url = config_client.get('apiBaseUrl', '/api/datasets-v2')

                            # Construct potential download URLs based on Mendeley's API structure
                            base_urls = [
                                f"https://data.mendeley.com{api_base_url}/{self.dataset_id}/{version}/archive",
                                f"https://data.mendeley.com{api_base_url}/{self.dataset_id}/{version}/files/archive",
                                f"https://data.mendeley.com/datasets/{self.dataset_id}/{version}/download",
                                f"https://data.mendeley.com/v1/datasets/{self.dataset_id}/{version}/download",
                            ]

                            self.log.debug(f"Generated download URLs from page analysis: {base_urls}")
                            return base_urls

                        except json.JSONDecodeError as e:
                            self.log.debug(f"Failed to parse INITIAL_STATE JSON: {e}")
                    else:
                        self.log.debug(f"Could not find matching closing brace for INITIAL_STATE JSON")
            else:
                self.log.debug(f"Could not find window.INITIAL_STATE in page")

        except requests.RequestException as e:
            self.log.warning(f"Failed to fetch landing page: {e}")

        # Fallback URLs if page analysis fails
        fallback_urls = [
            f"https://data.mendeley.com/datasets/{self.dataset_id}/{version}/download",
            f"https://data.mendeley.com/v1/datasets/{self.dataset_id}/{version}/download",
        ]

        self.log.debug(f"Using fallback download URLs: {fallback_urls}")
        return fallback_urls

    def _get_direct_download_url(self):
        """Get the direct download URL for the entire dataset"""
        if not self.dataset_id:
            raise Exception("No dataset ID available")

        # First try to get download URL from the landing page
        urls = self._get_download_url_from_page()

        if isinstance(urls, str):
            return urls
        elif isinstance(urls, list):
            return urls[0]  # Return first URL for primary attempt

        # Final fallback
        if self.version:
            return f"https://data.mendeley.com/datasets/{self.dataset_id}/{self.version}/download"
        else:
            return f"https://data.mendeley.com/datasets/{self.dataset_id}/download"

    def _download_dataset_archive(self, target_folder):
        """Download the entire dataset as a zip archive and extract it"""
        import requests
        import os
        import zipfile
        import tempfile

        # Get download URLs using the updated method
        download_urls = self._get_download_url_from_page()

        # Set headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        # Try each download URL until one works
        last_error = None
        response = None
        successful_url = None

        for i, download_url in enumerate(download_urls):
            self.log.debug(f"Trying download URL {i+1}/{len(download_urls)}: {download_url}")

            try:
                # First try HEAD request to check if it's a direct file download
                head_response = requests.head(download_url, headers=headers, timeout=30, allow_redirects=True)
                head_content_type = head_response.headers.get('content-type', '').lower()

                # If HEAD request indicates a file download, proceed with GET
                if ('application/' in head_content_type or 'binary' in head_content_type or
                    'zip' in head_content_type or 'octet-stream' in head_content_type or
                    'content-disposition' in head_response.headers):

                    self.log.debug(f"URL {download_url} appears to be a direct file download (content-type: {head_content_type})")
                    response = requests.get(download_url, headers=headers, timeout=60, stream=True, allow_redirects=True)
                    response.raise_for_status()
                    successful_url = download_url
                    break

                # If it's HTML, it might be a download page
                elif 'text/html' in head_content_type:
                    self.log.debug(f"URL {download_url} returned HTML, checking if it's a functional download page")

                    # Try the GET request anyway - some services return HTML headers but actual file content
                    response = requests.get(download_url, headers=headers, timeout=60, stream=True, allow_redirects=True)

                    # Check the actual response content-type
                    actual_content_type = response.headers.get('content-type', '').lower()

                    if ('application/' in actual_content_type or 'binary' in actual_content_type or
                        'zip' in actual_content_type or 'octet-stream' in actual_content_type or
                        'content-disposition' in response.headers):

                        self.log.debug(f"URL {download_url} actually returned file content despite HTML headers")
                        response.raise_for_status()
                        successful_url = download_url
                        break

                    # If it's still HTML, check if it's a very small response (likely an error)
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) < 1000:
                        self.log.debug(f"URL {download_url} returned small HTML response, likely an error page")
                        continue

                    # If it's a larger HTML response, it might contain the download mechanism
                    # This could be a download page that requires JavaScript or form submission
                    self.log.debug(f"URL {download_url} returned HTML download page")
                    continue

                else:
                    # Unknown content type, try GET request
                    self.log.debug(f"URL {download_url} returned unknown content-type: {head_content_type}, trying GET request")
                    response = requests.get(download_url, headers=headers, timeout=60, stream=True, allow_redirects=True)
                    response.raise_for_status()

                    # Check if we got a file
                    actual_content_type = response.headers.get('content-type', '').lower()
                    if not 'text/html' in actual_content_type:
                        successful_url = download_url
                        break
                    else:
                        continue

            except requests.RequestException as e:
                self.log.debug(f"Failed to download from {download_url}: {e}")
                last_error = e
                continue
        else:
            # If we've tried all URLs without success
            raise Exception(f"Dataset appears to require authentication or is not publicly downloadable. Last error: {last_error}")

        self.log.debug(f"Successfully started download from: {successful_url}")

        try:
            # Create a temporary file for the download
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
                temp_path = temp_file.name

                # Download the file in chunks
                total_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                        total_size += len(chunk)

            self.log.debug(f"Downloaded {total_size} bytes to: {temp_path}")

            # Check if we actually got a zip file
            if total_size < 100:  # Suspiciously small file
                with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content_preview = f.read(500)
                    self.log.debug(f"Small file content preview: {content_preview}")
                    if content_preview.strip().startswith('<'):
                        raise Exception("Downloaded HTML content instead of dataset archive - dataset may not be publicly accessible")

            # Extract the archive
            downloaded_files = []
            try:
                with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                    # Extract all files to target folder
                    zip_ref.extractall(target_folder)

                    # Get list of extracted files
                    for file_info in zip_ref.infolist():
                        if not file_info.is_dir():
                            extracted_path = os.path.join(target_folder, file_info.filename)
                            downloaded_files.append(extracted_path)
                            self.log.debug(f"Extracted file: {file_info.filename}")

            except zipfile.BadZipFile:
                self.log.error(f"Downloaded file is not a valid zip archive")
                # Try to see what we actually downloaded
                with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content_preview = f.read(500)
                    self.log.debug(f"Downloaded content preview: {content_preview}")
                raise Exception("Downloaded file is not a valid zip archive - dataset may not be publicly accessible")
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass  # File may already be deleted

            return downloaded_files

        except Exception as e:
            self.log.error(f"Error downloading Mendeley dataset: {e}")
            raise


    def download(self, target_folder, throttle=False, download_data=True):
        """
        Extract geospatial metadata from Mendeley dataset.

        Parameters:
        - target_folder: Directory to store files
        - throttle: Rate limiting for API calls
        - download_data: If True, downloads actual data files for local extraction.
                        If False, attempts metadata-only extraction via OAI-PMH.
        """
        self.throttle = throttle

        if not download_data:
            self.log.warning(
                "Mendeley provider has limited metadata-only extraction capabilities. "
                "Using download_data=False may result in incomplete spatial extent information. "
                "Consider using download_data=True to download actual data files for better geospatial extraction."
            )
            # For metadata-only mode, use OAI-PMH
            try:
                metadata = self._get_metadata_via_oai_pmh()
                self.log.info(f"Mendeley metadata extracted for dataset {self.dataset_id}")
                return
            except Exception as e:
                self.log.error(f"Failed to extract Mendeley metadata: {e}")
                raise

        try:
            # Download the entire dataset as an archive
            downloaded_files = self._download_dataset_archive(target_folder)

            if downloaded_files:
                self.log.info(f"Mendeley data downloaded for dataset {self.dataset_id}: {len(downloaded_files)} files")
            else:
                self.log.warning(f"No files downloaded from Mendeley dataset {self.dataset_id}")

        except Exception as e:
            self.log.error(f"Error processing Mendeley dataset: {e}")
            raise