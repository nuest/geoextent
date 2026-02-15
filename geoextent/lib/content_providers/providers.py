from requests import Session, HTTPError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from geoextent.lib import helpfunctions as hf
import logging
import math

logger = logging.getLogger("geoextent")
import time
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock


def find_provider(reference, content_providers):
    """Two-phase provider selection: fast DOI prefix match, then full validation.

    Phase 1 checks each provider's ``doi_prefixes`` class attribute against the
    reference string.  This is a pure string comparison — no network calls —
    so it is instant even when the target service is unreachable.

    Phase 2 falls back to calling ``validate_provider()`` on every provider,
    which may trigger DOI resolution via doi.org.  Exceptions (e.g. from an
    unreachable host) are caught and logged so that the next provider is tried.

    Returns:
        A provider instance whose ``validate_provider()`` returned True, or None.
    """
    # Phase 1 — fast offline DOI prefix matching
    for provider_class in content_providers:
        prefixes = getattr(provider_class, "doi_prefixes", ())
        if prefixes and any(p in reference for p in prefixes):
            provider = provider_class()
            try:
                if provider.validate_provider(reference):
                    logger.debug(
                        "Provider %s matched %s via DOI prefix (fast path)",
                        provider_class.__name__,
                        reference,
                    )
                    return provider
            except Exception:
                logger.debug(
                    "Provider %s DOI prefix matched but validate_provider "
                    "raised an exception, continuing",
                    provider_class.__name__,
                )
            # Prefix matched this provider; no other provider should share it.
            break

    # Phase 2 — full validation (may involve network calls)
    for provider_class in content_providers:
        provider = provider_class()
        try:
            if provider.validate_provider(reference):
                logger.debug(
                    "Provider %s matched %s (full validation)",
                    provider_class.__name__,
                    reference,
                )
                return provider
            else:
                logger.debug(
                    "Provider %s did not match %s",
                    provider_class.__name__,
                    reference,
                )
        except Exception:
            logger.debug(
                "Provider %s raised an exception during validation, skipping",
                provider_class.__name__,
            )
            continue

    return None


class ContentProvider:
    @property
    def supports_metadata_extraction(self):
        """Whether this provider can extract spatial/temporal extent from repository metadata alone."""
        return False

    def __init__(self):
        self.log = logging.getLogger("geoextent")


class DoiProvider(ContentProvider):
    # Known DOI prefixes for this provider.  Used for fast offline matching
    # during provider selection — avoids slow DOI resolution via doi.org when
    # the target service is unreachable.  Override in subclasses.
    doi_prefixes = ()

    def __init__(self):
        super().__init__()  # Initialize parent class (includes logging)
        self.session = self._create_optimized_session()
        # Default chunk size for downloads (1MB)
        self.download_chunk_size = 1024 * 1024
        # Initialize parallel download manager (will be configured per provider)
        self.parallel_manager = None

    def _create_optimized_session(self):
        """Create an optimized session with connection pooling and retry strategy"""
        session = Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=0.5,
            raise_on_status=False,
        )

        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=10,  # Number of connection pools
            pool_maxsize=20,  # Maximum number of connections in pool
            max_retries=retry_strategy,
        )

        # Mount adapter for both HTTP and HTTPS
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _download_file_optimized(
        self, url, filepath, chunk_size=None, show_progress=False
    ):
        """
        Optimized file download with proper buffering and streaming.

        Args:
            url: URL to download from
            filepath: Local file path to save to
            chunk_size: Size of chunks to download (default: 1MB)
            show_progress: Whether to show download progress
        """
        if chunk_size is None:
            chunk_size = self.download_chunk_size

        self.log.debug(f"Downloading {url} to {filepath} with {chunk_size} byte chunks")

        try:
            # Use streaming to avoid loading entire file into memory
            with self.session.get(url, stream=True) as response:
                response.raise_for_status()

                # Get file size if available
                total_size = int(response.headers.get("content-length", 0))

                with open(filepath, "wb") as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:  # Filter out keep-alive chunks
                            f.write(chunk)
                            downloaded += len(chunk)

                            if show_progress and total_size > 0:
                                progress = (downloaded / total_size) * 100
                                self.log.debug(f"Download progress: {progress:.1f}%")

                self.log.debug(f"Download completed: {downloaded} bytes")
                return downloaded

        except Exception as e:
            self.log.error(f"Failed to download {url}: {e}")
            # Clean up partial file
            if os.path.exists(filepath):
                os.remove(filepath)
            raise

    def _is_geospatial_file(self, filename, additional_extensions=None):
        """
        Check if a file is likely to contain geospatial data based on its extension.

        Based on officially documented supported formats in README.md and CLI help,
        plus commonly encountered geospatial extensions.

        Args:
            filename: Name of the file to check
            additional_extensions: Set of additional file extensions to consider geospatial

        Returns:
            bool: True if file extension suggests geospatial content
        """
        # Single comprehensive list of geospatial file extensions
        geospatial_extensions = {
            # Core officially supported formats (documented in README.md and CLI)
            ".geojson",  # GeoJSON
            ".csv",  # Tabular data (potential coordinates)
            ".shp",
            ".shx",
            ".dbf",
            ".prj",  # Shapefile components
            ".tif",
            ".tiff",
            ".geotiff",  # GeoTIFF
            ".gpkg",  # GeoPackage
            ".gpx",  # GPS Exchange Format
            ".gml",  # Geography Markup Language
            ".kml",
            ".kmz",  # Keyhole Markup Language
            ".fgb",  # FlatGeobuf
            # Additional commonly encountered geospatial extensions
            ".json",  # JSON files that might be GeoJSON
            ".nc",
            ".netcdf",  # NetCDF (often used for atmospheric/ocean data)
            ".asc",  # ASCII Grid (raster format)
            ".zip",
            ".tar",
            ".gz",
            ".rar",  # Archives that might contain geospatial data
            ".sqlite",
            ".db",  # Spatial databases (might be GeoPackage or SpatiaLite)
        }

        # Add any additional extensions provided by user
        if additional_extensions:
            geospatial_extensions = geospatial_extensions.union(
                {
                    ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                    for ext in additional_extensions
                }
            )

        file_ext = Path(filename).suffix.lower()
        return file_ext in geospatial_extensions

    def _filter_geospatial_files(
        self,
        files,
        skip_non_geospatial=False,
        max_size_mb=None,
        additional_extensions=None,
    ):
        """
        Filter files based on geospatial relevance and size constraints.

        Args:
            files: List of file dictionaries with 'name' and optionally 'size' keys
            skip_non_geospatial: If True, skip files that don't appear to be geospatial
            max_size_mb: Maximum total size in MB for all files combined
            additional_extensions: Set of additional file extensions to consider geospatial

        Returns:
            list: Filtered list of files
        """
        filtered_files = []
        total_size_bytes = 0
        max_size_bytes = max_size_mb * 1024 * 1024 if max_size_mb else None

        # First, separate geospatial and non-geospatial files
        geo_files = []
        non_geo_files = []

        for file_info in files:
            filename = file_info.get("name", "")
            if self._is_geospatial_file(filename, additional_extensions):
                geo_files.append(file_info)
            else:
                non_geo_files.append(file_info)

        # Sort by size (smaller files first for better sampling)
        def get_file_size(f):
            return f.get("size", 0)

        geo_files.sort(key=get_file_size)
        non_geo_files.sort(key=get_file_size)

        # Add geospatial files first (priority)
        for file_info in geo_files:
            file_size = file_info.get("size", 0)

            if (
                max_size_bytes is None
                or (total_size_bytes + file_size) <= max_size_bytes
            ):
                filtered_files.append(file_info)
                total_size_bytes += file_size
            else:
                self.log.warning(f"Skipping {file_info.get('name')} due to size limit")
                break

        # Add non-geospatial files if not skipping them and we have remaining space
        if not skip_non_geospatial:
            for file_info in non_geo_files:
                file_size = file_info.get("size", 0)

                if (
                    max_size_bytes is None
                    or (total_size_bytes + file_size) <= max_size_bytes
                ):
                    filtered_files.append(file_info)
                    total_size_bytes += file_size
                else:
                    self.log.warning(
                        f"Skipping {file_info.get('name')} due to size limit"
                    )
                    break

        if skip_non_geospatial and len(non_geo_files) > 0:
            self.log.info(
                f"Skipped {len(non_geo_files)} non-geospatial files due to --download-skip-nogeo option"
            )

        self.log.info(
            f"Selected {len(filtered_files)} files totaling {total_size_bytes / (1024*1024):.1f} MB"
        )
        return filtered_files

    def _setup_parallel_manager(self, max_workers=4):
        """Set up the parallel download manager with provider-specific settings."""

        class ProviderParallelManager(ParallelDownloadManager):
            def __init__(self, provider, max_workers, chunk_size):
                super().__init__(max_workers, chunk_size)
                self.provider = provider

            def _download_single_file(self, task):
                """Use the provider's optimized download method."""
                url, filepath, expected_size = task
                return self.provider._download_file_optimized(
                    url, filepath, self.chunk_size
                )

        self.parallel_manager = ProviderParallelManager(
            self, max_workers, self.download_chunk_size
        )

    def _should_use_parallel_downloads(self, file_list, max_workers):
        """
        Determine if parallel downloads would be beneficial.

        Criteria:
        - Parallel downloads enabled (max_workers > 1)
        - Multiple files (>= 2)
        - Total size > 10MB OR average file size > 1MB
        - Not too many files (to avoid overwhelming servers)
        """
        if max_workers <= 1:
            return False

        if len(file_list) < 2:
            return False

        if len(file_list) > 20:
            return False  # Too many files might overwhelm server

        total_size = sum(f.get("size", 0) for f in file_list)
        avg_size = total_size / len(file_list) if file_list else 0

        # Use parallel if total > 10MB or average file > 1MB
        return total_size > 10 * 1024 * 1024 or avg_size > 1024 * 1024

    def _download_files_batch(
        self, file_list, target_folder, show_progress=True, max_workers=4
    ):
        """
        Download multiple files with automatic parallel/sequential selection.

        Args:
            file_list: List of file dictionaries with 'url', 'name', 'size'
            target_folder: Target directory
            show_progress: Whether to show progress bars
            max_workers: Maximum number of parallel workers

        Returns:
            Download statistics and results
        """
        if not file_list:
            return []

        # Set up parallel manager
        self._setup_parallel_manager(max_workers)

        # Prepare download tasks
        download_tasks = []
        for file_info in file_list:
            # Different providers have different URL structures
            url = (
                file_info.get("url")
                or file_info.get("download_url")
                or file_info.get("link")
            )
            name = file_info.get("name") or file_info.get("filename")
            size = file_info.get("size", 0)

            if url and name:
                # Sanitize filename to avoid directory traversal issues
                safe_name = name.replace("/", "_").replace("\\", "_")
                filepath = os.path.join(target_folder, safe_name)
                download_tasks.append((url, filepath, size))

        if not download_tasks:
            self.log.warning("No valid download tasks found")
            return []

        # Decide parallel vs sequential
        use_parallel = self._should_use_parallel_downloads(file_list, max_workers)

        if use_parallel:
            self.log.info(
                f"Using parallel downloads with {max_workers} workers for {len(download_tasks)} files"
            )
        else:
            self.log.info(f"Using sequential downloads for {len(download_tasks)} files")

        # Progress tracking
        if show_progress:
            from tqdm import tqdm

            total_bytes = sum(task[2] for task in download_tasks)
            progress_bar = tqdm(
                total=total_bytes,
                desc="Downloading files",
                unit="B",
                unit_scale=True,
            )

            completed_count = 0

            def progress_callback(task, result):
                nonlocal completed_count
                if result["success"]:
                    progress_bar.update(result["bytes_downloaded"])
                completed_count += 1
                progress_bar.set_postfix(
                    {
                        "files": f"{completed_count}/{len(download_tasks)}",
                    }
                )

            results = self.parallel_manager.download_files_parallel(
                download_tasks, progress_callback
            )
            progress_bar.close()
        else:
            results = self.parallel_manager.download_files_parallel(download_tasks)

        # Log results
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful

        self.log.info(f"Downloaded {successful} files successfully, {failed} failed")

        if failed > 0:
            failed_files = [r["task"][1] for r in results if not r["success"]]
            self.log.warning(
                f"Failed downloads: {[os.path.basename(f) for f in failed_files]}"
            )

        return results

    def _request(self, url, throttle=False, **kwargs):
        while True:
            try:
                response = self.session.get(url, **kwargs)
                response.raise_for_status()
                break  # break while loop
            except HTTPError as e:
                # http error
                # dryad     dict_keys(['undefined', '404', '502', '503'])
                # figshare  dict_keys(['404', '422'])
                # zenodo    dict_keys(['410', '502', '404', '504'])
                # https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status

                if e.response.status_code == 429:
                    self._throttle(e.response)
                else:
                    logger.debug("HTTP %s for %s", e.response.status_code, url)
                    raise

        if throttle:
            self._throttle(response)

        return response

    def _throttle(self, response):
        values = [
            (response.headers.get("x-ratelimit-remaining")),  # Zenodo
            (response.headers.get("x-ratelimit-reset")),  # Zenodo
            (response.headers.get("ratelimit-remaining")),  # Dryad
            (response.headers.get("ratelimit-reset")),  # Dryad
        ]
        http_error = response.status_code

        wait_seconds = 1

        match values:
            case [None, None, None, None]:
                if http_error == 429:
                    wait_seconds = 60
                else:
                    wait_seconds = 1

            case [_, _, None, None]:
                remaining = int(values[0])
                reset = int(values[1])

                if remaining < 2 or http_error == 429:
                    wait_seconds = math.ceil(reset - time.time())

            case [None, None, _, _]:
                remaining = int(values[2])
                reset = int(values[3])

                if remaining < 2 or http_error == 429:
                    wait_seconds = math.ceil(reset - time.time())

            case _:
                if http_error == 429:
                    wait_seconds = 60
                else:
                    wait_seconds = 1

        print(f"INFO: Sleep {wait_seconds:.0f} s...")
        time.sleep(wait_seconds)

        return

    def _type_of_reference(self):
        if hf.doi_regexp.match(self.reference):
            return "DOI"
        elif hf.https_regexp.match(self.reference):
            return "Link"

    @property
    def get_url(self):

        if self._type_of_reference() == "DOI":
            doi = hf.doi_regexp.match(self.reference).group(2)

            try:
                resp = self._request("https://doi.org/{}".format(doi))
                resp.raise_for_status()
            except HTTPError:
                return doi
            except Exception:
                # Network errors (ConnectionError, Timeout, etc.) during DOI
                # resolution — return the raw DOI so callers can still attempt
                # offline matching (prefix, hostname) without crashing.
                logger.debug("DOI resolution failed for %s, returning raw DOI", doi)
                return doi

            return resp.url

        else:
            return self.reference


class ParallelDownloadManager:
    """Manager for parallel file downloads with progress tracking and error handling."""

    def __init__(self, max_workers=4, chunk_size=1024 * 1024):
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.progress_lock = Lock()

    def download_files_parallel(self, download_tasks, progress_callback=None):
        """
        Download multiple files in parallel.

        Args:
            download_tasks: List of (url, filepath, expected_size) tuples
            progress_callback: Function to call with progress updates

        Returns:
            List of download results with success/failure status
        """
        if self.max_workers <= 1:
            # Fall back to sequential downloads
            return self._download_files_sequential(download_tasks, progress_callback)

        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all download tasks
            future_to_task = {
                executor.submit(self._download_single_file, task): task
                for task in download_tasks
            }

            # Collect results as they complete
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(
                        {
                            "task": task,
                            "success": True,
                            "bytes_downloaded": result,
                            "error": None,
                        }
                    )
                except Exception as e:
                    results.append(
                        {
                            "task": task,
                            "success": False,
                            "bytes_downloaded": 0,
                            "error": str(e),
                        }
                    )

                # Update progress
                if progress_callback:
                    with self.progress_lock:
                        progress_callback(task, results[-1])

        return results

    def _download_files_sequential(self, download_tasks, progress_callback=None):
        """Fallback sequential download implementation."""
        results = []

        for task in download_tasks:
            try:
                result = self._download_single_file(task)
                download_result = {
                    "task": task,
                    "success": True,
                    "bytes_downloaded": result,
                    "error": None,
                }
            except Exception as e:
                download_result = {
                    "task": task,
                    "success": False,
                    "bytes_downloaded": 0,
                    "error": str(e),
                }

            results.append(download_result)

            # Update progress
            if progress_callback:
                progress_callback(task, download_result)

        return results

    def _download_single_file(self, task):
        """
        Download a single file with error handling.
        This method should be overridden by providers to use their optimized download method.
        """
        url, filepath, expected_size = task
        # This is a placeholder - providers should override with their own download method
        raise NotImplementedError(
            "Providers should implement their own download method"
        )
