import re
import os
import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .providers import DoiProvider
from .. import helpfunctions as hf

logger = logging.getLogger("geoextent")


class GFZ(DoiProvider):
    """Content provider for GFZ Data Services (dataservices.gfz-potsdam.de)

    Supports GFZ DOIs in the format 10.5880/GFZ.* and direct URLs to GFZ datasets.
    Parses HTML pages to extract download URLs and metadata.
    """

    doi_prefixes = ("10.5880/GFZ",)

    @classmethod
    def provider_info(cls):
        return {
            "name": "GFZ",
            "description": "GFZ Data Services is a curated research data repository for the geosciences domain, hosted at the GFZ German Research Centre for Geosciences in Potsdam. It has assigned DOIs to geoscientific datasets since 2004 and provides comprehensive consultation by domain scientists and IT specialists following FAIR principles.",
            "website": "https://dataservices.gfz-potsdam.de/",
            "supported_identifiers": [
                "https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id={doi}",
                "https://doi.org/10.5880/GFZ.{id}",
                "10.5880/GFZ.{id}",
            ],
            "doi_prefix": "10.5880/GFZ",
            "examples": ["10.5880/GFZ.4.8.2023.004"],
        }

    def __init__(self):
        super().__init__()
        self.host = {
            "hostname": [
                "https://dataservices.gfz-potsdam.de",
                "http://dataservices.gfz-potsdam.de",
                "dataservices.gfz-potsdam.de",
            ]
        }
        self.gfz_doi_pattern = re.compile(r"10\.5880/GFZ\.\d+\.\d+\.\d+\.\d+")
        self.dataset_id = None
        self.doi = None
        self.name = "GFZ"

    def validate_provider(self, reference):
        """Validate if the reference is a supported GFZ Data Services identifier

        Args:
            reference (str): DOI, URL, or dataset identifier

        Returns:
            bool: True if valid GFZ reference, False otherwise
        """
        self.reference = reference

        # Check for GFZ DOI pattern
        doi_match = self.gfz_doi_pattern.search(reference)
        if doi_match:
            # Extract the matched DOI
            self.doi = doi_match.group(0)
            return True

        # Check for GFZ hostname in URL
        if any(host in reference for host in self.host["hostname"]):
            # Extract dataset ID from showshort.php URLs
            showshort_match = re.search(r"showshort\.php\?id=([^&]+)", reference)
            if showshort_match:
                self.dataset_id = showshort_match.group(1)
                return True

        return False

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
        """Download data from GFZ Data Services

        Args:
            folder (str): Target directory for downloads
            throttle (bool): Whether to throttle requests (default: False)
            download_data (bool): Whether to download actual data (default: True)
            show_progress (bool): Whether to show progress bars (default: True)

        Returns:
            str: Path to downloaded data directory
        """
        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        logger.info(f"Downloading from GFZ Data Services: {self.reference}")

        # Warning for download skip nogeo not being supported
        if download_skip_nogeo:
            logger.warning(
                "GFZ provider does not support selective file filtering. "
                "The --download-skip-nogeo option will be ignored. Files will be downloaded based on availability."
            )

        if not download_data:
            logger.warning(
                "GFZ provider requires data download for geospatial extent extraction. "
                "Using download_data=False may result in limited or no spatial extent information."
            )
            return folder

        # Determine the landing page URL
        if self.doi:
            # Use DOI resolution to get the correct landing page URL
            landing_url = self.get_url
        elif self.dataset_id:
            landing_url = f"https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id={self.dataset_id}"
        else:
            landing_url = self.reference

        logger.debug(f"Landing page URL: {landing_url}")

        # Fetch the landing page
        try:
            response = self._request(landing_url, throttle=throttle)
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract DOI if not already available
            if not self.doi:
                doi_element = soup.find("meta", {"name": "citation_doi"})
                if doi_element:
                    self.doi = doi_element.get("content", "")
                    logger.debug(f"Extracted DOI: {self.doi}")

            # Find download URL
            download_url = self._extract_download_url(soup)
            if not download_url:
                raise Exception("Could not find download URL on GFZ landing page")

            logger.debug(f"Download URL: {download_url}")

            # Create target directory
            if self.doi:
                folder_name = self.doi.replace("/", "_").replace(":", "_")
            else:
                folder_name = f"gfz_{self.dataset_id}"

            download_dir = os.path.join(folder, folder_name)
            os.makedirs(download_dir, exist_ok=True)

            # Download the data with size filtering
            self._download_files(
                download_url,
                download_dir,
                show_progress,
                max_size_bytes=max_size_bytes,
                max_download_method=max_download_method,
                max_download_method_seed=max_download_method_seed,
            )

            return download_dir

        except Exception as e:
            logger.error(f"Error downloading GFZ dataset: {e}")
            raise

    def _extract_download_url(self, soup):
        """Extract download URL from GFZ landing page HTML

        Args:
            soup (BeautifulSoup): Parsed HTML of landing page

        Returns:
            str: Download URL or None if not found
        """
        # Look for download links in various patterns
        download_patterns = [
            # Direct download links
            r'https://datapub\.gfz-potsdam\.de/download/[^"\'>\s]+',
            # FTP links
            r'ftp://datapub\.gfz-potsdam\.de/[^"\'>\s]+',
        ]

        page_text = str(soup)
        for pattern in download_patterns:
            matches = re.findall(pattern, page_text)
            if matches:
                # Return the first valid download URL
                for match in matches:
                    if self._is_valid_download_url(match):
                        return match

        # Try to find download links in anchor tags
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if any(
                domain in href
                for domain in ["datapub.gfz-potsdam.de", "dataservices.gfz-potsdam.de"]
            ):
                if "download" in href.lower() or href.endswith((".zip", ".tar", ".gz")):
                    return urljoin("https://dataservices.gfz-potsdam.de", href)

        return None

    def _is_valid_download_url(self, url):
        """Check if URL is a valid download URL

        Args:
            url (str): URL to validate

        Returns:
            bool: True if valid download URL
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc in [
                "datapub.gfz-potsdam.de",
                "dataservices.gfz-potsdam.de",
            ] and (
                parsed.path.endswith((".zip", ".tar", ".gz", "/"))
                or "download" in parsed.path
            )
        except:
            return False

    def _download_files(
        self,
        download_url,
        target_dir,
        show_progress=True,
        max_size_bytes=None,
        max_download_method="ordered",
        max_download_method_seed=None,
        **kwargs,
    ):
        """Download files from the GFZ download URL

        Args:
            download_url (str): URL to download from
            target_dir (str): Target directory
            show_progress (bool): Whether to show progress bar
            **kwargs: Additional arguments
        """
        try:
            # Check if it's a directory listing or direct file
            response = self._request(download_url, throttle=True, stream=True)
            content_type = response.headers.get("content-type", "").lower()

            if "text/html" in content_type:
                # It's a directory listing, parse and download individual files
                self._download_from_directory_listing(
                    download_url,
                    target_dir,
                    show_progress,
                    max_size_bytes=max_size_bytes,
                    max_download_method=max_download_method,
                    max_download_method_seed=max_download_method_seed,
                    **kwargs,
                )
            else:
                # It's a direct file download
                filename = self._get_filename_from_response(response, download_url)
                file_size = int(response.headers.get("content-length", 0))

                # Check size limit for single file download
                if (
                    max_size_bytes is not None
                    and file_size > 0
                    and file_size > max_size_bytes
                ):
                    logger.warning(
                        f"File {filename} ({file_size:,} bytes) exceeds size limit ({max_size_bytes:,} bytes). Skipping download."
                    )
                    return

                file_path = os.path.join(target_dir, filename)
                self._download_single_file(
                    response,
                    file_path,
                    show_progress,
                    max_size_bytes=max_size_bytes,
                    **kwargs,
                )

        except Exception as e:
            logger.error(f"Error downloading files from {download_url}: {e}")
            raise

    def _download_from_directory_listing(
        self,
        listing_url,
        target_dir,
        show_progress=True,
        max_size_bytes=None,
        max_download_method="ordered",
        max_download_method_seed=None,
        **kwargs,
    ):
        """Download files from a directory listing page

        Args:
            listing_url (str): URL of directory listing
            target_dir (str): Target directory
            show_progress (bool): Whether to show progress bar
            **kwargs: Additional arguments
        """
        response = self._request(listing_url, throttle=True)
        soup = BeautifulSoup(response.text, "html.parser")

        # Ensure listing URL ends with / for proper urljoin behavior
        if not listing_url.endswith("/"):
            listing_url = listing_url + "/"

        # Find downloadable files (skip directories) and gather size information
        file_info = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if not href.startswith("?") and not href.endswith("/") and href != "../":
                file_url = urljoin(listing_url, href)

                # Try to get file size by making a HEAD request
                try:
                    head_response = self.session.head(file_url)
                    head_response.raise_for_status()
                    file_size = int(head_response.headers.get("content-length", 0))
                except:
                    file_size = 0  # Unknown size

                file_info.append({"name": href, "url": file_url, "size": file_size})

        if not file_info:
            logger.warning("No downloadable files found in directory listing")
            return

        logger.info(f"Found {len(file_info)} files in directory listing")

        # Apply size filtering if specified
        if max_size_bytes is not None:
            if max_download_method_seed is None:
                max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

            selected_files, total_size, skipped_files = hf.filter_files_by_size(
                file_info,
                max_size_bytes,
                max_download_method,
                max_download_method_seed,
            )

            if not selected_files:
                logger.warning("No files can be downloaded within the size limit")
                return

            logger.info(
                f"Size limit applied: downloading {len(selected_files)} of {len(file_info)} files ({total_size:,} bytes total)"
            )
            file_info = selected_files
        else:
            total_size = sum(f.get("size", 0) for f in file_info)
            logger.info(
                f"Downloading all {len(file_info)} files ({total_size:,} bytes total)"
            )

        # Download selected files
        for file_data in file_info:
            filename = file_data["name"]
            file_url = file_data["url"]
            try:
                logger.debug(f"Downloading file: {filename}")
                file_response = self._request(file_url, throttle=True, stream=True)
                file_path = os.path.join(target_dir, filename)

                self._download_single_file(
                    file_response,
                    file_path,
                    show_progress,
                    max_size_bytes=max_size_bytes,
                    **kwargs,
                )

            except Exception as e:
                logger.warning(f"Failed to download {filename}: {e}")
                continue

    def _download_single_file(
        self, response, file_path, show_progress=True, max_size_bytes=None, **kwargs
    ):
        """Download a single file from response stream

        Args:
            response: HTTP response object
            file_path (str): Path to save file
            show_progress (bool): Whether to show progress bar
            **kwargs: Additional arguments
        """
        total_size = int(response.headers.get("content-length", 0))

        if show_progress and total_size > 0:
            from tqdm import tqdm

            progress_bar = tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=os.path.basename(file_path),
            )
        else:
            progress_bar = None

        downloaded_size = 0
        size_exceeded = False

        try:
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        # If we have a size limit and the original file size was unknown, monitor download size
                        if max_size_bytes is not None and total_size == 0:
                            downloaded_size += len(chunk)
                            if downloaded_size > max_size_bytes:
                                logger.warning(
                                    f"File {os.path.basename(file_path)} exceeds size limit during download ({downloaded_size:,} > {max_size_bytes:,} bytes). Stopping download."
                                )
                                size_exceeded = True
                                break

                        f.write(chunk)
                        if progress_bar:
                            progress_bar.update(len(chunk))

            if progress_bar:
                progress_bar.close()

            # If size was exceeded, remove the partial file
            if size_exceeded:
                if os.path.exists(file_path):
                    os.remove(file_path)
                return

            logger.debug(f"Downloaded: {file_path}")

        except Exception as e:
            if progress_bar:
                progress_bar.close()
            if os.path.exists(file_path):
                os.remove(file_path)
            raise

    def _get_filename_from_response(self, response, url):
        """Extract filename from HTTP response or URL

        Args:
            response: HTTP response object
            url (str): Download URL

        Returns:
            str: Filename
        """
        # Try to get filename from Content-Disposition header
        content_disposition = response.headers.get("content-disposition", "")
        if "filename=" in content_disposition:
            filename = content_disposition.split("filename=")[1].strip("\"'")
            return filename

        # Fallback to URL path
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if filename and filename != "/":
            return filename

        # Final fallback
        return "gfz_dataset.zip"
